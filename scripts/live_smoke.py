"""Exercise the running application, including real vision inference. Saves evidence locally."""

import json
import time
from pathlib import Path
import httpx


def main():
    base = "http://127.0.0.1:8000"
    out = Path("artifacts")
    out.mkdir(exist_ok=True)
    with httpx.Client(base_url=base, timeout=150) as c:

        def login(role):
            r = c.post(
                "/api/login",
                json={
                    "email": role + "@manifest.demo",
                    "password": "ManifestDemo!2026",
                },
            )
            r.raise_for_status()
            c.headers["X-CSRF-Token"] = r.json()["csrf"]

        login("executive")
        sid = c.post(
            "/api/shipments",
            json={
                "supplier": "Company B (China)",
                "reference": "Live end-to-end verification",
            },
        ).json()["id"]
        for kind in ["invoice", "packing_list", "bill_of_lading"]:
            r = c.post(
                f"/api/shipments/{sid}/documents",
                data={"kind": kind},
                files={
                    "file": (
                        kind + ".pdf",
                        Path("samples/" + kind + ".pdf").read_bytes(),
                        "application/pdf",
                    )
                },
            )
            r.raise_for_status()
        s = c.get("/api/shipments/" + sid).json()
        for d in s["documents"]:
            preview = c.get(f"/api/documents/{d['id']}/preview/1")
            assert preview.status_code == 200 and preview.content.startswith(b"\x89PNG")
            for key, f in d["fields"].items():
                r = c.patch(
                    f"/api/documents/{d['id']}/fields/{key}",
                    json={"value": f["value"], "revision": s["revision"]},
                )
                r.raise_for_status()
                s["revision"] += 1
        s = c.get("/api/shipments/" + sid).json()
        assert all(x["passed"] for x in s["checks"])
        login("manager")
        r = c.post(f"/api/shipments/{sid}/approve", json={"revision": s["revision"]})
        r.raise_for_status()
        exported = c.get(f"/api/shipments/{sid}/export")
        exported.raise_for_status()
        (out / "verified-export.csv").write_bytes(exported.content)
        s = c.get("/api/shipments/" + sid).json()
        report = {
            "native_packet": sid,
            "confirmed_fields": sum(len(d["fields"]) for d in s["documents"]),
            "all_checks_passed": all(x["passed"] for x in s["checks"]),
            "approval_status": s["status"],
            "export_bytes": len(exported.content),
        }
        login("executive")
        scan_sid = c.post(
            "/api/shipments",
            json={
                "supplier": "Company B (China)",
                "reference": "Real scan extraction verification",
            },
        ).json()["id"]
        start = time.time()
        r = c.post(
            f"/api/shipments/{scan_sid}/documents",
            data={"kind": "packing_list"},
            files={
                "file": (
                    "packing_list_scan.png",
                    Path("samples/packing_list_scan.png").read_bytes(),
                    "image/png",
                )
            },
        )
        r.raise_for_status()
        ai = r.json()
        from scripts.seed import sample_values

        expected = sample_values()
        matches = {key: f["value"] == expected[key] for key, f in ai["fields"].items()}
        assert ai["engine"] == "local-vision", ai["note"]
        assert all(matches.values()), matches
        report["scan"] = {
            "shipment": scan_sid,
            "elapsed_seconds": round(time.time() - start, 2),
            "engine": ai["engine"],
            "fields": ai["fields"],
            "expected_field_matches": matches,
            "export_blocked": c.get(f"/api/shipments/{scan_sid}/export").status_code
            == 409,
        }
        (out / "live-smoke.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
