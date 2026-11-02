# Verification record — 2 November 2026

## Verified locally

- `python -m pytest -q --basetemp=.test-tmp`: 16 tests passed. Includes full workflow, cross-document mismatch, role and record permissions, CSRF, session invalidation, size/signature checks, stale revision, decimal multi-line totals, AI success/failure adapters, formula injection and rate limit.
- `npm --prefix frontend run build`: successful production build.
- `npm audit --omit=dev`: no reported production dependency vulnerabilities at verification time.
- Actual local Qwen2.5-VL 3B inference on the synthetic packing-list PNG extracted all eight expected fields. Initial model-load run took approximately 50.4 seconds; a later running-API call took approximately 3.7 seconds. These measurements are hardware/cache-specific, not a service-level commitment.
- `python -m scripts.live_smoke`: HTTP uploads, actual extraction, 27 field confirmations, all checks passed, manager approval, 1,351-byte CSV download; scan upload used local vision and remained export-blocked.
- Browser: executive demo login, dashboard, shipment navigation, source preview, mismatch presentation, mobile and desktop layouts, structured line-item editor. Desktop 1440×1000 and phone 390×844. At the phone viewport, the root did not exceed viewport width.
- Public repository push succeeded with history preserved. No upload to the assessment portal was attempted.

## Limits

- Not deployed remotely; Docker is unavailable locally, so container builds and Render blueprint execution are unverified.
- No client data or held-out historical accuracy dataset. One scan is not evidence for the brief's 95% target on 200 shipments.
- Automated vision reads the first page only. Other PDF pages can be viewed and manually entered.
- Heuristic confidence is not calibrated. Every field requires human confirmation regardless of score.
- Render and Railway's currently documented regions do not include India; the Render blueprint is labelled for fictional demo use only.
- No load test, production account provisioning, disaster-recovery exercise or formal compliance certification.

See `docs/evidence/` for synthetic live inference and export records. Re-run `scripts/live_smoke.py` with the app running to reproduce, noting that it creates two additional demo shipments.
