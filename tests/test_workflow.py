import json
import pytest
from fastapi.testclient import TestClient
from backend import main
from backend.domain import checks, validate_field
from backend.extraction import extract
from scripts.seed import make_pdf, sample_values


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", tmp_path / "test.sqlite3")
    monkeypatch.setattr(main, "DATA", tmp_path)
    (tmp_path / "uploads").mkdir()
    with TestClient(main.app) as client:
        with main.connect() as c:
            for uid, role in [
                ("executive", "executive"),
                ("manager", "manager"),
                ("other", "executive"),
            ]:
                salt = "a" * 32
                c.execute(
                    "INSERT INTO users VALUES(?,?,?,?,?,?)",
                    (
                        uid,
                        uid + "@test.demo",
                        uid,
                        role,
                        salt,
                        main.password_hash("test-password", salt),
                    ),
                )
        yield client


def signin(client, uid="executive"):
    r = client.post(
        "/api/login", json={"email": uid + "@test.demo", "password": "test-password"}
    )
    assert r.status_code == 200
    client.headers["X-CSRF-Token"] = r.json()["csrf"]


def create(client):
    return client.post(
        "/api/shipments", json={"supplier": "Demo supplier", "reference": "TEST-001"}
    ).json()["id"]


def upload(client, sid, kind, values=None):
    return client.post(
        f"/api/shipments/{sid}/documents",
        data={"kind": kind},
        files={
            "file": (
                kind + ".pdf",
                make_pdf(kind, values or sample_values()),
                "application/pdf",
            )
        },
    )


def confirm_all(client, sid):
    s = client.get("/api/shipments/" + sid).json()
    for d in s["documents"]:
        for key, f in d["fields"].items():
            r = client.patch(
                f"/api/documents/{d['id']}/fields/{key}",
                json={"value": f["value"], "revision": s["revision"]},
            )
            assert r.status_code == 200, (key, f, r.text)
            s["revision"] += 1
    return client.get("/api/shipments/" + sid).json()


def test_complete_workflow_and_reapproval(client):
    signin(client)
    sid = create(client)
    assert client.get(f"/api/shipments/{sid}/export").status_code == 409
    for kind in ["invoice", "packing_list", "bill_of_lading"]:
        r = upload(client, sid, kind)
        assert r.status_code == 201, r.text
        assert r.json()["engine"] == "pdf-text"
    s = confirm_all(client, sid)
    assert all(c["passed"] for c in s["checks"])
    assert (
        client.post(
            f"/api/shipments/{sid}/approve", json={"revision": s["revision"]}
        ).status_code
        == 403
    )
    signin(client, "manager")
    assert (
        client.post(
            f"/api/shipments/{sid}/approve", json={"revision": s["revision"]}
        ).status_code
        == 200
    )
    exported = client.get(f"/api/shipments/{sid}/export")
    assert exported.status_code == 200 and "invoice_total" in exported.text
    s = client.get("/api/shipments/" + sid).json()
    d = s["documents"][0]
    assert (
        client.patch(
            f"/api/documents/{d['id']}/fields/gross_weight",
            json={"value": "3165", "revision": s["revision"]},
        ).status_code
        == 200
    )
    assert client.get(f"/api/shipments/{sid}/export").status_code == 409
    assert client.get("/api/shipments/" + sid).json()["status"] == "In review"


def test_mismatch_blocks_even_confirmed(client):
    signin(client)
    sid = create(client)
    for kind in ["invoice", "packing_list", "bill_of_lading"]:
        values = sample_values(gross="3165" if kind == "packing_list" else "3120")
        assert upload(client, sid, kind, values).status_code == 201
    s = confirm_all(client, sid)
    assert (
        next(c for c in s["checks"] if c["code"] == "gross_weight")["passed"] is False
    )
    signin(client, "manager")
    assert (
        client.post(
            f"/api/shipments/{sid}/approve", json={"revision": s["revision"]}
        ).status_code
        == 409
    )


def test_ownership_csrf_and_session(client):
    assert client.get("/api/shipments").status_code == 401
    signin(client)
    sid = create(client)
    d = upload(client, sid, "invoice").json()["id"]
    assert client.get(f"/api/documents/{d}/file").status_code == 200
    client.headers["X-CSRF-Token"] = "invalid"
    assert (
        client.post(
            "/api/shipments", json={"supplier": "abc", "reference": "xyz"}
        ).status_code
        == 403
    )
    signin(client, "other")
    assert client.get("/api/shipments/" + sid).status_code == 404
    assert client.get(f"/api/documents/{d}/file").status_code == 404
    assert client.get("/api/shipments").json() == []
    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/me").status_code == 401


def test_inputs_duplicate_and_stale_edits(client):
    signin(client)
    sid = create(client)
    assert (
        client.post(
            f"/api/shipments/{sid}/documents",
            data={"kind": "invoice"},
            files={"file": ("bad.pdf", b"not a pdf", "application/pdf")},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/shipments/{sid}/documents",
            data={"kind": "invoice"},
            files={
                "file": (
                    "big.pdf",
                    b"%PDF" + b"X" * (10 * 1024 * 1024),
                    "application/pdf",
                )
            },
        ).status_code
        == 413
    )
    d = upload(client, sid, "invoice").json()["id"]
    assert upload(client, sid, "invoice").status_code == 409
    assert (
        client.patch(
            f"/api/documents/{d}/fields/packages", json={"value": "NaN", "revision": 1}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/documents/{d}/fields/packages", json={"value": "120", "revision": 0}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/shipments", json={"supplier": "  ", "reference": "valid"}
        ).status_code
        == 422
    )


def test_unreadable_ai_falls_back(monkeypatch):
    import httpx

    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.Client, "post", unavailable)
    from PIL import Image
    import io

    buf = io.BytesIO()
    Image.new("RGB", (500, 500), "white").save(buf, format="PNG")
    r = extract(buf.getvalue(), "image/png", "invoice")
    assert r["engine"] == "manual"
    assert all(not f["confirmed"] and not f["value"] for f in r["fields"].values())
    assert "manual" in r["note"]


def test_vision_reads_actual_provider_output(monkeypatch):
    import httpx

    def model(*args, **kwargs):
        assert kwargs["json"]["images"]
        return httpx.Response(
            200,
            json={"response": '{"supplier":"From actual provider"}'},
            request=httpx.Request("POST", "http://model"),
        )

    monkeypatch.setattr(httpx.Client, "post", model)
    from PIL import Image
    import io

    buf = io.BytesIO()
    Image.new("RGB", (500, 500), "white").save(buf, format="PNG")
    r = extract(buf.getvalue(), "image/png", "invoice")
    assert r["fields"]["supplier"]["value"] == "From actual provider"
    assert not r["fields"]["supplier"]["confirmed"]


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1e1000", "abc"])
def test_invalid_numbers(value):
    with pytest.raises(ValueError):
        validate_field("gross_weight", value)


def test_multiline_and_decimal_arithmetic():
    from backend.domain import FIELDS

    v = sample_values()
    v["line_items"] = json.dumps(
        [
            {"description": "A", "hsn": "1001", "quantity": "3", "unit_price": "0.10"},
            {"description": "B", "hsn": "1002", "quantity": "2", "unit_price": "0.20"},
        ]
    )
    v["invoice_total"] = "0.70"
    v["quantity"] = "5"
    docs = [
        {
            "kind": kind,
            "fields": {key: {"value": v[key], "confirmed": True} for key in keys},
        }
        for kind, keys in FIELDS.items()
    ]
    assert all(c["passed"] for c in checks(docs))
    docs[0]["fields"]["invoice_total"]["value"] = "0.72"
    assert not next(c for c in checks(docs) if c["code"] == "total")["passed"]


def test_csv_injection():
    assert main.safe_csv('=IMPORTXML("x")').startswith("'")
    assert main.safe_csv("  +cmd").startswith("'")


def test_untrusted_origin(client):
    assert (
        client.post(
            "/api/login",
            headers={"Origin": "https://evil.example"},
            json={"email": "a", "password": "b"},
        ).status_code
        == 403
    )


def test_rate_limit(client):
    for _ in range(15):
        assert (
            client.post(
                "/api/login", json={"email": "none", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/login", json={"email": "none", "password": "wrong"}
        ).status_code
        == 429
    )


def test_preview_and_unconfirmed_approval(client):
    signin(client)
    sid = create(client)
    did = upload(client, sid, "invoice").json()["id"]
    s = client.get("/api/shipments/" + sid).json()
    assert s["documents"][0]["pages"] == 1
    preview = client.get(f"/api/documents/{did}/preview/1")
    assert preview.status_code == 200 and preview.content.startswith(b"\x89PNG")
    assert client.get(f"/api/documents/{did}/preview/2").status_code == 404
    signin(client, "manager")
    assert (
        client.post(
            f"/api/shipments/{sid}/approve", json={"revision": s["revision"]}
        ).status_code
        == 409
    )


def test_replacement_retains_original_and_revokes_approval(client):
    signin(client)
    sid = create(client)
    for kind in ["invoice", "packing_list", "bill_of_lading"]:
        assert upload(client, sid, kind).status_code == 201
    s = confirm_all(client, sid)
    signin(client, "manager")
    assert (
        client.post(
            f"/api/shipments/{sid}/approve", json={"revision": s["revision"]}
        ).status_code
        == 200
    )
    s = client.get("/api/shipments/" + sid).json()
    d = next(d for d in s["documents"] if d["kind"] == "packing_list")
    original = client.get(f"/api/documents/{d['id']}/file").content
    r = client.post(
        f"/api/documents/{d['id']}/replace",
        data={"revision": s["revision"]},
        files={
            "file": (
                "replacement.pdf",
                make_pdf("packing_list", sample_values(gross="3165")),
                "application/pdf",
            )
        },
    )
    assert r.status_code == 200, r.text
    current = client.get("/api/shipments/" + sid).json()
    replaced = next(x for x in current["documents"] if x["id"] == d["id"])
    assert current["status"] == "In review"
    assert not any(f["confirmed"] for f in replaced["fields"].values())
    assert replaced["fields"]["gross_weight"]["value"] == "3165"
    version = replaced["versions"][0]["id"]
    route = f"/api/documents/{d['id']}/versions/{version}/file"
    assert client.get(route).content == original
    assert client.get(f"/api/shipments/{sid}/export").status_code == 409
    signin(client, "other")
    assert client.get(route).status_code == 404
    assert (
        client.post(
            f"/api/documents/{d['id']}/retry", json={"revision": current["revision"]}
        ).status_code
        == 404
    )


def test_retry_preserves_review_on_failure_and_rejects_stale(client, monkeypatch):
    signin(client)
    sid = create(client)
    did = upload(client, sid, "invoice").json()["id"]
    s = client.get("/api/shipments/" + sid).json()
    assert (
        client.post(
            f"/api/documents/{did}/retry", json={"revision": s["revision"] - 1}
        ).status_code
        == 409
    )
    blank = {
        "fields": {
            k: {"value": "", "confirmed": False} for k in s["documents"][0]["fields"]
        },
        "engine": "manual",
        "note": "offline",
    }
    monkeypatch.setattr(main, "extract", lambda *args: blank)
    assert (
        client.post(
            f"/api/documents/{did}/retry", json={"revision": s["revision"]}
        ).status_code
        == 409
    )
    current = client.get("/api/shipments/" + sid).json()
    assert current["revision"] == s["revision"]
    assert current["documents"][0]["fields"] == s["documents"][0]["fields"]


def test_successful_retry_archives_previous_fields(client):
    signin(client)
    sid = create(client)
    did = upload(client, sid, "invoice").json()["id"]
    s = client.get("/api/shipments/" + sid).json()
    assert (
        client.post(
            f"/api/documents/{did}/retry", json={"revision": s["revision"]}
        ).status_code
        == 200
    )
    current = client.get("/api/shipments/" + sid).json()
    assert current["revision"] == s["revision"] + 1
    assert len(current["documents"][0]["versions"]) == 1
    assert any(a["action"] == "Extraction retried" for a in current["audit"])


def test_flattened_multiline_csv(client):
    import csv, io

    signin(client)
    sid = create(client)
    for kind in ["invoice", "packing_list", "bill_of_lading"]:
        upload(client, sid, kind)
    s = client.get("/api/shipments/" + sid).json()
    inv = next(d for d in s["documents"] if d["kind"] == "invoice")
    pack = next(d for d in s["documents"] if d["kind"] == "packing_list")
    items = [
        {"description": "=1+1", "hsn": "1001", "quantity": "3", "unit_price": "0.10"},
        {
            "description": "Second item",
            "hsn": "1002",
            "quantity": "2",
            "unit_price": "0.20",
        },
    ]
    for did, key, value in [
        (inv["id"], "line_items", json.dumps(items)),
        (inv["id"], "invoice_total", "0.70"),
        (pack["id"], "quantity", "5"),
    ]:
        assert (
            client.patch(
                f"/api/documents/{did}/fields/{key}",
                json={"value": value, "revision": s["revision"]},
            ).status_code
            == 200
        )
        s["revision"] += 1
    s = confirm_all(client, sid)
    signin(client, "manager")
    assert (
        client.post(
            f"/api/shipments/{sid}/approve", json={"revision": s["revision"]}
        ).status_code
        == 200
    )
    rows = list(
        csv.DictReader(io.StringIO(client.get(f"/api/shipments/{sid}/export").text))
    )
    assert len(rows) == 2
    assert rows[0]["description"] == "'=1+1"
    assert rows[0]["line_total"] == "0.30" and rows[1]["line_total"] == "0.40"
    assert rows[0]["invoice_total"] == "0.70"


@pytest.mark.parametrize(
    "patch",
    [
        {"description": None},
        {"description": {"nested": "bad"}},
        {"hsn": []},
        {"hsn": "x" * 31},
    ],
)
def test_malformed_model_line_items(patch):
    item = {
        "description": "Item",
        "hsn": "9405",
        "quantity": "1",
        "unit_price": "1.00",
        **patch,
    }
    with pytest.raises(ValueError):
        validate_field("line_items", json.dumps([item]))


def test_oversized_pdf_page_is_bounded():
    import pymupdf
    from backend.extraction import read_file
    from PIL import Image
    import io

    with pymupdf.open() as pdf:
        pdf.new_page(width=10000, height=10000)
        raw = pdf.tobytes()
    _, image, _ = read_file(raw, "application/pdf")
    with Image.open(io.BytesIO(image)) as im:
        assert max(im.size) <= 1800
