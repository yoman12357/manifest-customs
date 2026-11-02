"""Idempotent, fictional demo data and actual sample documents."""

import io
import json
import os
import secrets
import time
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from backend.main import initialize, connect, DATA, password_hash
from backend.domain import FIELDS
from backend.extraction import LABELS, extract


def sample_values(
    supplier="Company B (China)",
    gross="3120",
    quantity="2400",
    price="6.80",
    description="LED panel light 40W",
):
    from decimal import Decimal

    return dict(
        supplier=supplier,
        consignee="Company A Demo Imports",
        packages="120",
        gross_weight=gross,
        net_weight="2800",
        container="DEMO1234567",
        invoice_number="INV-DEMO-081",
        invoice_date="2026-11-01",
        currency="USD",
        incoterm="CIF",
        description=description,
        hsn="9405",
        quantity=quantity,
        unit_price=price,
        invoice_total=str(Decimal(quantity) * Decimal(price)),
        bl_number="BL-DEMO-811",
        line_items=json.dumps(
            [
                dict(
                    description=description,
                    hsn="9405",
                    quantity=quantity,
                    unit_price=price,
                )
            ]
        ),
    )


def make_pdf(kind, values):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(595, 842))
    c.setFillColor(HexColor("#214e40"))
    c.rect(0, 730, 595, 112, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(42, 786, kind.replace("_", " ").upper())
    c.setFont("Helvetica", 10)
    c.drawString(42, 760, "FICTIONAL SAMPLE / NOT FOR CUSTOMS FILING")
    y = 694
    for key in FIELDS[kind]:
        c.setFillColor(HexColor("#364b3d"))
        c.setFont("Helvetica", 10)
        text = f"{LABELS[key]}: {values[key]}"
        if key == "line_items":
            # Keep the machine-readable line complete, with smaller font to avoid cropping.
            c.setFont("Helvetica", 4.8)
        c.drawString(42, y, text)
        c.setStrokeColor(HexColor("#e3e7df"))
        c.line(42, y - 13, 553, y - 13)
        y -= 34
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#89937e"))
    c.drawString(
        42, 50, "Manifest demo document | All entities and references are synthetic."
    )
    c.save()
    return out.getvalue()


def seed():
    initialize()
    sample_dir = Path("samples")
    sample_dir.mkdir(exist_ok=True)
    with connect() as c:
        for uid, name, role in [
            ("executive", "Asha Rao", "executive"),
            ("manager", "Dev Mehta", "manager"),
        ]:
            salt = secrets.token_hex(16)
            c.execute(
                "INSERT OR IGNORE INTO users VALUES(?,?,?,?,?,?)",
                (
                    uid,
                    uid + "@manifest.demo",
                    name,
                    role,
                    salt,
                    password_hash(
                        os.getenv("DEMO_PASSWORD", "ManifestDemo!2026"), salt
                    ),
                ),
            )
        records = [
            (
                "SHP-24811",
                "Company B (China)",
                "LED panel lights · Ocean import",
                "In review",
                False,
                "mismatch",
            ),
            (
                "SHP-24812",
                "Company C (Sweden)",
                "Steel ball valves · Ocean import",
                "Approved",
                True,
                "clean",
            ),
            (
                "SHP-24813",
                "Company B (China)",
                "Lighting components · November",
                "Awaiting documents",
                False,
                "empty",
            ),
            (
                "SHP-24814",
                "Company D (UAE)",
                "Industrial fittings · November",
                "In review",
                False,
                "partial",
            ),
        ]
        for n, (sid, supplier, ref, status, confirmed, mode) in enumerate(records):
            if c.execute("SELECT 1 FROM shipments WHERE id=?", (sid,)).fetchone():
                continue
            created = time.time() - (n + 1) * 86400
            c.execute(
                "INSERT INTO shipments(id,supplier,reference,owner,status,created,updated) VALUES(?,?,?,?,?,?,?)",
                (sid, supplier, ref, "executive", status, created, created + 1000),
            )
            c.execute(
                "INSERT INTO audit(shipment,actor,action,detail,created) VALUES(?,?,?,?,?)",
                (sid, "Asha Rao", "Shipment created", "Synthetic demo seed", created),
            )
            if mode == "empty":
                continue
            for kind in FIELDS:
                if mode == "partial" and kind != "invoice":
                    continue
                v = sample_values(supplier=supplier)
                if sid == "SHP-24812":
                    v.update(
                        gross_weight="1460",
                        net_weight="1300",
                        quantity="180",
                        description="Steel ball valve DN50",
                        currency="EUR",
                        unit_price="42.50",
                        invoice_total="7650.00",
                        line_items=json.dumps(
                            [
                                dict(
                                    description="Steel ball valve DN50",
                                    hsn="8481",
                                    quantity="180",
                                    unit_price="42.50",
                                )
                            ]
                        ),
                    )
                if mode == "mismatch" and kind == "packing_list":
                    v["gross_weight"] = "3165"
                raw = make_pdf(kind, v)
                did = secrets.token_hex(12)
                path = DATA / "uploads" / did
                path.write_bytes(raw)
                result = extract(raw, "application/pdf", kind)
                for f in result["fields"].values():
                    f["confirmed"] = confirmed
                c.execute(
                    "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        did,
                        sid,
                        kind,
                        kind + ".pdf",
                        "application/pdf",
                        str(path),
                        json.dumps(result["fields"]),
                        result["engine"],
                        result["note"],
                    ),
                )
                c.execute(
                    "INSERT INTO audit(shipment,actor,action,detail,created) VALUES(?,?,?,?,?)",
                    (sid, "Asha Rao", "Document uploaded", kind, created + 500),
                )
            if confirmed:
                c.execute(
                    "INSERT INTO audit(shipment,actor,action,detail,created) VALUES(?,?,?,?,?)",
                    (
                        sid,
                        "Dev Mehta",
                        "Packet approved",
                        "Seeded reviewed example",
                        created + 1000,
                    ),
                )
    for kind in FIELDS:
        (sample_dir / (kind + ".pdf")).write_bytes(make_pdf(kind, sample_values()))
    import pymupdf as fitz

    with fitz.open(
        stream=make_pdf("packing_list", sample_values()), filetype="pdf"
    ) as pdf:
        pdf[0].get_pixmap().save(str(sample_dir / "packing_list_scan.png"))
    print("Demo seeded. Samples are in samples/. Existing records preserved.")


if __name__ == "__main__":
    seed()
