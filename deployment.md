# Manifest — deployment and reviewer guide

Repository: https://github.com/yoman12357/manifest-customs

Status: implemented and verified locally. No live deployment is claimed. The live-app link is optional under the assessment brief. Render deployment files are supplied for a fictional-data demo; India production hosting remains a client rollout requirement.

## 1. Run locally (Windows PowerShell)

Prerequisites: Git, Python 3.12 or later, Node.js 22.12 or later, and Ollama. The vision model download needs several GB of disk space; allow at least 8 GB of system RAM. CPU inference works but can take longer on other machines.

```powershell
git clone https://github.com/yoman12357/manifest-customs.git
cd manifest-customs
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
ollama pull qwen2.5vl:3b
python -m scripts.seed
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open http://127.0.0.1:8000. Ensure the Ollama desktop application is running; if it is not installed as a service, run `ollama serve` in another terminal. Native PDF text extraction does not require the model. Scanned photos require it; failures produce manual-entry fields and never an invented success.

On macOS/Linux, use `python3 -m venv .venv` and `source .venv/bin/activate`; the remaining commands are the same after activation. No environment variables are required for the local default.

For frontend development, run `npm --prefix frontend run dev` in a second terminal. Vite proxies API requests to the local Python service.

## 2. Demo logins

| Role | Email | Password |
| --- | --- | --- |
| Documentation executive | executive@manifest.demo | ManifestDemo!2026 |
| Documentation manager | manager@manifest.demo | ManifestDemo!2026 |

These are deliberately public demo credentials for fictional records. They are not personal accounts or production secrets. The seed command is idempotent and does not overwrite existing work. Changing the demo-password environment setting affects only the first seed of an empty database.

## 3. Try the core flow

1. Executive: open SHP-24811 and Cross-checks. The packing-list weight differs from the invoice and bill of lading. Export stays locked.
2. Create a shipment. Upload `samples/invoice.pdf`, `samples/packing_list.pdf`, and `samples/bill_of_lading.pdf` into their named slots.
3. Compare originals with the fields. Confirm all fields, including the line-item group. Correct values inline if needed. All three regular sample documents match.
4. Sign out and sign in as manager. Open the new shipment, inspect its checks, approve, and export CSV.
5. Change a field after approval: the packet returns to review and export locks again.
6. Create another shipment and upload `samples/packing_list_scan.png`. This exercises real vision inference. Uncertain readings require confirmation; missing readings can be entered manually.

## 4. Run verification

```powershell
python -m pytest -q --basetemp=.test-tmp
npm --prefix frontend run build
```

Optional, with the running app and model: `python -m scripts.live_smoke`. It creates two fictional shipments and saves evidence under `artifacts/`. The automated suite uses an isolated temporary database; it never edits the demo workspace.

## 5. Docker / India-hosted deployment

The app is one container with the React build and Python service. SQLite and uploaded documents share a durable data volume. Ollama is a separate private service with a model volume. Use a single application worker and one instance; do not horizontally replicate this SQLite deployment.

```sh
docker compose up -d --build
docker compose exec ollama ollama pull qwen2.5vl:3b
```

For client production, provision the VM and storage in India. Terminate HTTPS with a reverse proxy, configure the production origin and secure-cookie mode, expose only the reverse proxy, and keep Ollama off the public internet. Take encrypted backups of the database and uploads together. Test restore before client data is admitted. Do not remove named volumes when stopping containers.

The Docker build and remote deployment were not executed in this environment because Docker and a hosting account were unavailable. Treat those as deployment instructions, not verified hosting results.

## 6. Render / Railway / Vercel

Render: import this public GitHub repository as a Blueprint using `render.yaml`. It defines a web service with a persistent disk and a private vision service with a model disk. These resources require paid plans: inspect and approve the provider's displayed cost before creating them. Enter the public app origin when prompted. The model pulls at first startup; wait for it to finish, then test a scan. Check app health and persistence across a restart.

The supplied Render blueprint uses Singapore. Render and Railway's documented regions currently do not include India. This is acceptable only as a clearly labelled fictional-data demonstration, not satisfaction of the client's India-hosting constraint. Do not upload real client documents there.

Vercel lists a Mumbai function region, but this application's SQLite, filesystem uploads and local vision service need persistent processes and disks. A full Vercel migration would require an India-region database, private object storage and a separate model service. Merely moving the frontend to Vercel does not solve that requirement.

Region references: https://render.com/docs/regions ; https://docs.railway.com/deployments/regions ; https://vercel.com/docs/regions . Checked 2 November 2026.

## 7. Environment variables (names only; no credentials)

| Name | Purpose |
| --- | --- |
| APP_ENV | Enables production secure cookies and hides interactive API documentation |
| APP_ORIGIN | Exact public origin accepted for browser mutations |
| DATA_DIR | Durable location for SQLite and private uploads |
| OLLAMA_URL | Private Ollama service base URL |
| VISION_MODEL | Installed vision-model identifier |
| AI_TIMEOUT | Maximum inference request duration |
| DEMO_PASSWORD | Initial demo-account password override on an empty database |
| PORT | Hosting provider's assigned HTTP port |
| OLLAMA_HOST | Vision service's private listen address |

No external AI API key is required. Keep real environment files out of Git. A production rollout must replace public demo accounts with managed user provisioning before handling confidential data.

## 8. Submission

Run `python -m scripts.package_submission`. Upload `submission/Manifest_Submission.zip`, which contains exactly `Manifest_TDD.pdf` and `deployment.md`. The implementation, samples and tests remain in the public GitHub repository. Keep it public until review is complete.
