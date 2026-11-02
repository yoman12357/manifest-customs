# Manifest

A customs document review workspace. Upload an invoice, packing list and bill of lading; extract a draft; reconcile the documents; approve and export reviewed data.

Built for Isocode client brief 5. Fictional demonstration only; it does not file customs declarations or calculate duty.

## Start locally

Python 3.12+, Node 22.12+ and Ollama are required. From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
ollama pull qwen2.5vl:3b
python -m scripts.seed
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Use the demo-role buttons on sign-in, then submit. Native PDF text extraction works without Ollama; scanned-image AI requires the running model. If it fails, fields stay blank for manual entry.

Demo executive: `executive@manifest.demo`. Manager: `manager@manifest.demo`. Both use `ManifestDemo!2026`. These are intentionally public fictional demo accounts, never production credentials.

## Verify

```powershell
python -m pytest -q --basetemp=.test-tmp
npm --prefix frontend run build
```

See [deployment.md](deployment.md), [technical design](docs/TDD.md) and [verification](docs/verification.md). Submission packaging is generated with `python -m scripts.package_submission`.

## Reviewer walkthrough

1. Sign in as executive. Open **SHP-24811** and its cross-checks: invoice and bill of lading show 3,120 kg; packing list shows 3,165 kg.
2. Create a new shipment. Upload all three PDFs from `samples/`. All readings start unconfirmed.
3. Review each original and confirm every required field, including line items. The normal samples reconcile.
4. Sign out. Sign in as manager and open the packet. Approve it and download CSV.
5. Edit any field. Approval is revoked and export locks again.
6. Upload `samples/packing_list_scan.png` to a new shipment's packing-list slot to exercise actual local vision inference.

## Structure

- `backend/domain.py`: decimal arithmetic, field validation, cross-document checks.
- `backend/extraction.py`: uploaded-byte extraction and local vision adapter.
- `backend/main.py`: API, cookie sessions, permissions, SQLite transactions, audit and export.
- `frontend/src/`: responsive React interface and design system.
- `scripts/seed.py`: idempotent synthetic records and sample document generator.
- `tests/`: isolated workflow, arithmetic and security tests.
- `Dockerfile`, `compose.yaml`, `render.yaml`: portable deployment.

SQLite and uploaded files need durable storage and one app worker. Do not deploy this backend directly to an ephemeral Vercel function. Render's Singapore blueprint is a demo option, not India-hosting compliance. No live deployment is claimed until verified.

## License considerations

This project uses PyMuPDF under its AGPL/commercial dual license. Review redistribution and network-service obligations before commercial adoption; replace the PDF layer or obtain a commercial license if required. Model licensing must also be reviewed before client rollout.
