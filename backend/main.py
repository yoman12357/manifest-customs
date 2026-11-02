import csv
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    Request,
    Response,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .domain import FIELDS, checks, validate_field
from .extraction import extract, read_file

DATA = Path(os.getenv("DATA_DIR", "data")).resolve()
DATA.mkdir(parents=True, exist_ok=True)
(DATA / "uploads").mkdir(exist_ok=True)
DB = DATA / "manifest.sqlite3"


def connect():
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def password_hash(password, salt):
    return hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
    ).hex()


def initialize():
    with connect() as c:
        c.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE, name TEXT, role TEXT, salt TEXT, hash TEXT);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), csrf TEXT, expires REAL);
        CREATE TABLE IF NOT EXISTS shipments(id TEXT PRIMARY KEY, supplier TEXT, reference TEXT, owner TEXT REFERENCES users(id), status TEXT, created REAL, updated REAL, revision INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, shipment TEXT REFERENCES shipments(id), kind TEXT, filename TEXT, mime TEXT, path TEXT, fields TEXT, engine TEXT, note TEXT, UNIQUE(shipment,kind));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, shipment TEXT, actor TEXT, action TEXT, detail TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS login_attempts(ip TEXT, created REAL);
        """)


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(
    title="Manifest API",
    lifespan=lifespan,
    docs_url="/api/docs" if os.getenv("APP_ENV") != "production" else None,
)


@app.middleware("http")
async def security(request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if (
            origin
            and origin != str(request.base_url).rstrip("/")
            and origin != os.getenv("APP_ORIGIN")
        ):
            return Response("Untrusted origin", status_code=403)
    res = await call_next(request)
    res.headers["X-Content-Type-Options"] = "nosniff"
    res.headers["Referrer-Policy"] = "same-origin"
    res.headers["Cache-Control"] = (
        "no-store" if request.url.path.startswith("/api") else "no-cache"
    )
    res.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; frame-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'"
    )
    return res


def user(request: Request):
    token = request.cookies.get("manifest_session", "")
    with connect() as c:
        row = c.execute(
            "SELECT u.*, s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE token=? AND expires>?",
            (hashlib.sha256(token.encode()).hexdigest(), time.time()),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Please sign in to continue")
    if request.method not in {"GET", "HEAD"} and not hmac.compare_digest(
        request.headers.get("x-csrf-token", ""), row["csrf"]
    ):
        raise HTTPException(403, "Session verification failed. Refresh and try again.")
    return dict(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        role=row["role"],
        csrf=row["csrf"],
    )


def shipment(c, sid, u):
    row = c.execute("SELECT * FROM shipments WHERE id=?", (sid,)).fetchone()
    if not row or (u["role"] != "manager" and row["owner"] != u["id"]):
        raise HTTPException(404, "Shipment not found")
    return dict(row)


def documents(c, sid):
    return [
        {**dict(r), "fields": json.loads(r["fields"])}
        for r in c.execute(
            "SELECT * FROM documents WHERE shipment=? ORDER BY kind", (sid,)
        )
    ]


def audit(c, sid, u, action, detail=""):
    c.execute(
        "INSERT INTO audit(shipment,actor,action,detail,created) VALUES(?,?,?,?,?)",
        (sid, u["name"], action, detail, time.time()),
    )


def invalidate(c, sid):
    c.execute(
        "UPDATE shipments SET status='In review', updated=?, revision=revision+1 WHERE id=?",
        (time.time(), sid),
    )


class Login(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


@app.post("/api/login")
def login(body: Login, response: Response, request: Request):
    ip = request.client.host
    with connect() as c:
        c.execute("DELETE FROM login_attempts WHERE created<?", (time.time() - 600,))
        if (
            c.execute(
                "SELECT COUNT(*) FROM login_attempts WHERE ip=?", (ip,)
            ).fetchone()[0]
            >= 15
        ):
            raise HTTPException(429, "Too many attempts. Try again in 10 minutes.")
        c.execute("INSERT INTO login_attempts VALUES(?,?)", (ip, time.time()))
    with connect() as c:
        row = c.execute(
            "SELECT * FROM users WHERE email=?", (body.email.lower().strip(),)
        ).fetchone()
        salt = row["salt"] if row else "0" * 32
        hashed = password_hash(body.password, salt)
        if not row or not hmac.compare_digest(hashed, row["hash"]):
            raise HTTPException(401, "Email or password is incorrect")
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        c.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
        c.execute(
            "INSERT INTO sessions VALUES(?,?,?,?)",
            (
                hashlib.sha256(token.encode()).hexdigest(),
                row["id"],
                csrf,
                time.time() + 28800,
            ),
        )
    response.set_cookie(
        "manifest_session",
        token,
        httponly=True,
        samesite="strict",
        secure=os.getenv("APP_ENV") == "production",
        max_age=28800,
    )
    return dict(
        id=row["id"], name=row["name"], role=row["role"], email=row["email"], csrf=csrf
    )


@app.get("/api/me")
def me(u=Depends(user)):
    return u


@app.post("/api/logout")
def logout(request: Request, response: Response, u=Depends(user)):
    with connect() as c:
        c.execute(
            "DELETE FROM sessions WHERE token=?",
            (
                hashlib.sha256(
                    request.cookies.get("manifest_session", "").encode()
                ).hexdigest(),
            ),
        )
    response.delete_cookie("manifest_session")
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/shipments")
def list_shipments(u=Depends(user)):
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM shipments WHERE owner=? OR ?='manager' ORDER BY updated DESC",
            (u["id"], u["role"]),
        ).fetchall()
        return [
            {
                **dict(r),
                "document_count": len(documents(c, r["id"])),
                "issues": sum(not x["passed"] for x in checks(documents(c, r["id"]))),
            }
            for r in rows
        ]


class NewShipment(BaseModel):
    supplier: str = Field(min_length=2, max_length=120)
    reference: str = Field(min_length=2, max_length=120)


@app.post("/api/shipments", status_code=201)
def create(body: NewShipment, u=Depends(user)):
    if not body.supplier.strip() or not body.reference.strip():
        raise HTTPException(422, "Supplier and reference are required")
    sid = "SHP-" + secrets.token_hex(3).upper()
    with connect() as c:
        c.execute(
            "INSERT INTO shipments(id,supplier,reference,owner,status,created,updated) VALUES(?,?,?,?,?,?,?)",
            (
                sid,
                body.supplier.strip(),
                body.reference.strip(),
                u["id"],
                "Awaiting documents",
                time.time(),
                time.time(),
            ),
        )
        audit(c, sid, u, "Shipment created", body.reference)
    return {"id": sid}


@app.get("/api/shipments/{sid}")
def detail(sid: str, u=Depends(user)):
    with connect() as c:
        s = shipment(c, sid, u)
        docs = documents(c, sid)
        for d in docs:
            d.pop("path", None)
        return {
            **s,
            "documents": docs,
            "checks": checks(docs),
            "audit": [
                dict(a)
                for a in c.execute(
                    "SELECT * FROM audit WHERE shipment=? ORDER BY id DESC LIMIT 100",
                    (sid,),
                )
            ],
        }


@app.post("/api/shipments/{sid}/documents", status_code=201)
def upload(
    sid: str, kind: str = Form(...), file: UploadFile = File(...), u=Depends(user)
):
    if kind not in FIELDS:
        raise HTTPException(422, "Unknown document type")
    with connect() as c:
        shipment(c, sid, u)
        if c.execute(
            "SELECT 1 FROM documents WHERE shipment=? AND kind=?", (sid, kind)
        ).fetchone():
            raise HTTPException(
                409,
                "This slot is occupied. Use the existing document review or create a new shipment.",
            )
    raw = file.file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "Maximum file size is 10 MB")
    mime = (
        "application/pdf"
        if raw.startswith(b"%PDF")
        else "image/png"
        if raw.startswith(b"\x89PNG\r\n\x1a\n")
        else "image/jpeg"
        if raw.startswith(b"\xff\xd8\xff")
        else None
    )
    if not mime:
        raise HTTPException(422, "Upload a valid PDF, PNG or JPEG")
    try:
        read_file(raw, mime)
    except Exception:
        raise HTTPException(
            422,
            "File could not be read. Use an unencrypted PDF of at most 10 pages, or an image under 20 megapixels.",
        )
    result = extract(raw, mime, kind)
    did = secrets.token_hex(12)
    path = DATA / "uploads" / did
    path.write_bytes(raw)
    try:
        with connect() as c:
            shipment(c, sid, u)
            c.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    did,
                    sid,
                    kind,
                    Path(file.filename or "document").name[:180],
                    mime,
                    str(path),
                    json.dumps(result["fields"]),
                    result["engine"],
                    result["note"],
                ),
            )
            invalidate(c, sid)
            audit(c, sid, u, "Document uploaded", kind + ": " + result["engine"])
    except sqlite3.IntegrityError:
        path.unlink(missing_ok=True)
        raise HTTPException(
            409, "Another upload filled this slot. Refresh the shipment."
        )
    return {"id": did, **result}


@app.get("/api/documents/{did}/file")
def original(did: str, u=Depends(user)):
    with connect() as c:
        d = c.execute("SELECT * FROM documents WHERE id=?", (did,)).fetchone()
        if not d:
            raise HTTPException(404, "Document not found")
        shipment(c, d["shipment"], u)
        audit(c, d["shipment"], u, "Original viewed", d["kind"])
    return FileResponse(
        d["path"], media_type=d["mime"], headers={"Content-Disposition": "inline"}
    )


class Edit(BaseModel):
    value: str = Field(min_length=1, max_length=20000)
    revision: int


@app.patch("/api/documents/{did}/fields/{key}")
def edit(did: str, key: str, body: Edit, u=Depends(user)):
    try:
        validate_field(key, body.value)
    except ValueError as e:
        raise HTTPException(422, str(e))
    with connect() as c:
        c.execute("BEGIN IMMEDIATE")
        d = c.execute("SELECT * FROM documents WHERE id=?", (did,)).fetchone()
        if not d:
            raise HTTPException(404, "Document not found")
        s = shipment(c, d["shipment"], u)
        if s["revision"] != body.revision:
            raise HTTPException(409, "Shipment changed. Refresh before editing.")
        if key not in FIELDS[d["kind"]]:
            raise HTTPException(422, "Unknown field")
        fields = json.loads(d["fields"])
        old = fields[key]["value"]
        fields[key].update(value=body.value.strip(), confirmed=True)
        if not fields[key]["value"]:
            raise HTTPException(422, "Field cannot be blank")
        c.execute("UPDATE documents SET fields=? WHERE id=?", (json.dumps(fields), did))
        invalidate(c, s["id"])
        audit(
            c,
            s["id"],
            u,
            "Field confirmed" if old == body.value else "Field corrected",
            json.dumps(
                {
                    "document": d["kind"],
                    "field": key,
                    "before": old,
                    "after": body.value,
                }
            ),
        )
    return {"ok": True}


class Revision(BaseModel):
    revision: int


@app.post("/api/shipments/{sid}/approve")
def approve(sid: str, body: Revision, u=Depends(user)):
    if u["role"] != "manager":
        raise HTTPException(403, "A documentation manager must approve the packet")
    with connect() as c:
        c.execute("BEGIN IMMEDIATE")
        s = shipment(c, sid, u)
        if s["revision"] != body.revision:
            raise HTTPException(409, "Shipment changed. Refresh before approving.")
        if not all(x["passed"] for x in checks(documents(c, sid))):
            raise HTTPException(
                409, "Clear every cross-check and confirm every field before approval"
            )
        c.execute(
            "UPDATE shipments SET status='Approved', updated=?, revision=revision+1 WHERE id=?",
            (time.time(), sid),
        )
        audit(c, sid, u, "Packet approved")
    return {"ok": True}


def safe_csv(v):
    s = str(v)
    return "'" + s if s.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else s


@app.get("/api/shipments/{sid}/export")
def export(sid: str, u=Depends(user)):
    with connect() as c:
        c.execute("BEGIN IMMEDIATE")
        s = shipment(c, sid, u)
        docs = documents(c, sid)
        if s["status"] != "Approved" or not all(x["passed"] for x in checks(docs)):
            raise HTTPException(
                409, "Export blocked until review and manager approval are complete"
            )
        out = io.StringIO(newline="")
        w = csv.writer(out)
        w.writerow(["shipment_id", "document_type", "field", "value"])
        for d in docs:
            for key, f in d["fields"].items():
                w.writerow([sid, d["kind"], key, safe_csv(f["value"])])
        audit(c, sid, u, "CSV exported", "Manifest normalized v1 layout")
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{sid}.csv"'},
    )


@app.get("/api/activity")
def activity(u=Depends(user)):
    with connect() as c:
        return [
            dict(r)
            for r in c.execute(
                "SELECT a.* FROM audit a JOIN shipments s ON s.id=a.shipment WHERE s.owner=? OR ?='manager' ORDER BY a.id DESC LIMIT 100",
                (u["id"], u["role"]),
            )
        ]


DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        return FileResponse(DIST / "index.html")
