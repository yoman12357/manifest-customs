# Manifest — Technical Design Document

GitHub: https://github.com/yoman12357/manifest-customs

Live application: not deployed. A working local application and portable deployment files are provided. This document describes verified behavior separately from future production work.

Prepared for client brief 5: Customs broker's AI document extraction and cross-check tool for import shipments. Author: Aryan. 2 November 2026.

## 1. Product and scope

Company A's documentation team retypes invoices, packing lists and bills of lading, then discovers inconsistencies late. Manifest turns these three originals into one reviewable shipment packet. Its central promise is not autonomous filing: it is a shorter, traceable path from uploaded documents to verified data.

The delivered core is shipment list, creation, document upload, actual extraction, side-by-side review, cross-document reconciliation, manager approval and CSV export. Executive and manager sign-in are implemented. Fictional examples include the brief's 3,120 kg invoice versus 3,165 kg packing-list discrepancy, a clean approved packet, an empty shipment and a partial packet.

The brief estimates 9,900 entry hours and INR 70.29 lakh of annual entry/error cost. Those are client assumptions, not measured benefits of this prototype. The target of 95% field accuracy on 200 past shipments has not been demonstrated. No real shipment records were available or used.

Success at this stage means a reviewer can complete upload-to-export, see why an inconsistent packet is blocked, and inspect who changed each value. Payments, messaging and external filing systems are outside this slice; no fake integration button suggests otherwise.

## 2. Architecture and choices

Browser (React/Vite) -> same-origin FastAPI service -> SQLite metadata plus private upload files. FastAPI -> private Ollama vision service. Only authenticated document routes serve originals and rendered previews. The application service also serves the built frontend, avoiding a separate cross-origin session configuration.

React suits the interactive review surface: independent fields, role-specific actions, filters, line-item editing and responsive panels. FastAPI provides validated request models and a small readable API. SQLite with WAL and explicit transactions keeps the demonstration easy to run and back up. It is a deliberate one-worker, one-instance choice; PostgreSQL is the next step when concurrency or multiple instances are required.

Documents are stored under random identifiers outside the static directory. Original filenames are display metadata, not storage paths. PDF pages are rendered to images on authenticated routes, avoiding inconsistent embedded-PDF behavior on phones. PyMuPDF supports both native text and page rendering; its AGPL/commercial license needs a commercial rollout decision.

Inference runs in a separate Ollama service. This avoids third-party document transmission and API-key setup. The tested model is Qwen2.5-VL 3B. The model is a draft generator, never the source of arithmetic, permissions or approval decisions. An unavailable model does not fabricate fields.

## 3. Data model and state

Users: identifier, unique email, display name, role, password salt and scrypt hash. Sessions: hashed random token, user reference, CSRF token, expiry. Raw session tokens exist only in HttpOnly cookies.

Shipments: identifier, supplier, reference, owning executive, status, timestamps and integer revision. Executives see their own packets; managers see all packets in this single organization. Documents: shipment, one of three document kinds, filename, detected MIME type, private path, extraction fields, engine and explanatory note. A unique shipment/kind constraint prevents accidental duplicate slots.

Each extraction field keeps current value, original extraction, source text or page reference, heuristic confidence and human-confirmed flag. Invoice line items are a list of description, HSN, quantity and unit price; the interface exposes a normal row editor. Multiple lines contribute to invoice totals and aggregate quantity checks.

Audit events retain shipment, actor, action, detail and timestamp, including before/after values on correction. Login attempts support rate limiting. Relationships use database foreign keys where relevant. Audit is append-only through the API, not cryptographically tamper-proof against a database administrator.

States are Awaiting documents -> In review -> Approved. Every upload or field edit increments the revision and returns the packet to In review, including edits after approval. Approval and edit transactions take a SQLite write lock; stale revisions return a conflict rather than overwriting another reviewer. Export rechecks the actual current data inside its own transaction.

## 4. Main flows and API contract

Sign-in verifies a salted scrypt password and issues an eight-hour session. The frontend retrieves the user and CSRF token at startup. Sign-out removes the server session and cookie. Incorrect credentials and expired sessions have visible recovery states.

An executive creates a packet with supplier and reference, then uploads one invoice, packing list and bill of lading. Accepted formats are PDF, PNG and JPEG. Files are limited to 10 MB; PDFs to ten unencrypted pages; images to twenty megapixels. Content signatures and parsability are checked rather than trusting the filename or declared MIME type. Duplicate slots return a conflict.

Uploads are extracted from their actual bytes. The reviewer sees the original, source evidence and extracted value. Each required field must be explicitly confirmed; changing a value also confirms it and records the correction. Every confirmation triggers fresh checks. Empty and invalid values cannot be confirmed.

A manager approves only after every check passes. Executives cannot approve through either the UI or a direct API call. Approval enables CSV export for authorized reviewers. An edit then revokes approval. The export uses a documented normalized layout because no proprietary filing-software layout was supplied.

Key routes: POST /api/login; GET /api/shipments; POST /api/shipments; GET /api/shipments/{id}; POST /api/shipments/{id}/documents; PATCH /api/documents/{id}/fields/{key}; POST /api/shipments/{id}/approve; GET /api/shipments/{id}/export. Originals and page previews require the same shipment-level access control.

## 5. Extraction and uncertainty

First, native PDF text is inspected for grounded labelled fields. This deterministic shortcut is genuine extraction, not AI. It returns the matched source line and a heuristic score of 0.94. Layouts without these labels fall through to vision for missing fields. The supplied PDFs use this path so the local demo remains useful without an inference server.

For scans and missing fields, the first page is converted to a bounded image and sent to the private vision model with the allowed field names and a request for structured JSON. The instruction treats document contents as untrusted data. Returned keys are whitelisted and their values length-limited; they cannot invoke tools or perform actions. Missing or malformed model output leaves fields blank for manual entry.

Vision values receive a deliberately cautious heuristic score of 0.55. These scores are routing signals, not calibrated probabilities. Every field requires confirmation regardless of score. Vision evidence says page 1; the image remains adjacent to the field. Native extraction exposes exact source lines. The model never silently confirms its own answer.

Timeout, unavailable model or unreadable content results in a visible manual-entry note. There is no automatic retry loop or invented fixture response. Multi-page PDFs can be viewed page by page and entered manually, but automated vision currently reads only the first page. Bilingual and skewed scans are not validated broadly.

A live scanned packing-list test read all eight expected fields correctly with the selected model; an earlier Moondream attempt failed and safely fell back to manual entry. One synthetic scan does not support an accuracy claim on client documents. Next validation should use 200 consented historical shipments, held-out suppliers and field-level exact-match scoring.

## 6. Reconciliation and security

The server requires all three documents and all required confirmations. It compares package count, gross weight, net weight, supplier, consignee and container across documents. Names are trimmed and case-normalized; no fuzzy match silently resolves differences. It checks aggregate invoice versus packing quantity, each document's net weight <= gross weight, and invoice total versus the sum of all quantity-times-price lines.

Arithmetic uses Python Decimal, never binary floating point or model reasoning. Weights and package counts require exact agreement. Invoice amount tolerance is one currency subunit of 0.01, a labelled assumption. Negative, non-finite and excessively large numbers are rejected. Package and item quantities are whole numbers. Export is gated server-side even if a caller bypasses disabled buttons.

Session tokens are random and stored hashed, cookies are HttpOnly/SameSite Strict, and production cookies are Secure. Mutations require a session-bound CSRF token and enforce the configured origin. Parameterized SQL, role checks, upload limits, CSP, no-sniff headers and CSV formula neutralization cover common risks. No real secrets are committed; public demo credentials are intentional fictional reviewer access.

Production gaps are explicit: public demo users are unsuitable for confidential records; provisioning, retention/deletion, malware scanning, encrypted backups, disk encryption and tested recovery are operational rollout work. No claim of legal certification is made. Logs contain document metadata and correction values and therefore need the same access and retention discipline as originals.

## 7. UI and responsive design

The design uses an off-white canvas, deep forest-green navigation/actions, restrained sage panels and amber uncertainty. Typography, whitespace and repeated spacing make a dense operations tool feel calm. Status is expressed through text and icons as well as color. No decorative stock photography competes with the work.

Overview provides real database counts, recent packets, search and status filters. The shipment table connects reference, supplier, received documents and status. The review surface puts the source on the left and editable fields on the right, with a visible confirmation count and export lock. The cross-check view explains each failure with the values that disagree. History supports handover and correction accountability.

On phones the sidebar becomes a menu, summary cards become two columns, document slots stack and source/fields become a single column. Tables scroll within their containers; they do not force the entire page sideways. Reviewed at desktop width 1440 and phone width 390. Loading, no-results, empty uploads, failed requests, invalid input and AI manual fallback each have distinct states.

The login screen offers fictional demo-role fill buttons without bypassing authentication. Executive and manager actions remain different. Add/remove line items uses ordinary labelled controls rather than JSON. The current app has English UI only; the customs brief specifies desktop use, and phone support is added as required by the assessment.

## 8. Verification and limits

The automated pytest suite covers the complete three-document workflow, manager-only approval, confirmation requirements, post-approval edit invalidation, inconsistent weights even after confirmation, ownership restrictions, original-file authorization, CSRF, logout, bad signatures, file-size limits, duplicates, stale revisions, numeric edge cases, multi-line decimal arithmetic, model success/failure adapters, CSV injection, hostile origins and login rate limiting.

A separate live HTTP walkthrough created a real packet, uploaded the three sample PDFs, confirmed 27 fields, passed every check, approved as manager and downloaded a 1,351-byte CSV. A real scan was then uploaded through the running API; it used local-vision and remained blocked from export. Evidence is reproducible through scripts/live_smoke.py. Vision calls were not mocked in that walkthrough.

Browser review covered desktop and phone layouts, sign-in, shipment navigation, cross-check presentation, readable source rendering and line-item editing controls. Screenshots accompany this document. The frontend production build passed. Automated tests are isolated from the demo database. No Docker build, remote deployment, load test or 200-shipment accuracy evaluation is claimed.

## 9. Assumptions, cuts and next steps

A1: This is one organization, with executive-owned packets and organization-wide manager access. Manager approval is an additional conservative export gate. Identity uses seeded passwords rather than an enterprise SSO integration.

A2: The three document kinds each occupy one slot. Replacements/versioned uploads and multiple supplier invoices are deferred. A reviewer can correct any field manually; a fundamentally wrong original currently requires a fresh packet.

A3: Weights are kg, item/package quantities are whole numbers, and one currency applies per invoice. Currency choices are a bounded supported list. Exact cross-document weight equality and a 0.01 invoice tolerance are assumed until the client supplies formal tolerances and currency rules. Up to 100 line items are supported within the field-size limit.

A4: No filing-software import schema was provided. CSV is a normalized four-column layout: shipment_id, document_type, field, value. Invoice line items are serialized in their field. A client-specific flattening/mapping adapter is a next step, not a claimed integration.

A5: All names, account identities, bill/container identifiers, dates and generated documents are fictional. Company aliases and the brief's example discrepancy are reused; other metadata is synthetic. Model scores are uncalibrated heuristics and not accuracy measurements.

A6: Local execution is the verified delivery. The client requires India hosting; the supplied Render Singapore option is a fictional-data demo exception, explicitly not client-production compliance. Local vision avoids a third-party training/data-retention policy dependency.

A7: Small-team workload, one application instance and one worker justify SQLite. Files, sessions and metadata share durable local storage. Larger scale needs a PostgreSQL/object-storage migration, background inference jobs, quotas and operational monitoring.

Cuts: customs filing, HSN classification, duty computation and importer tracking portal are out of scope in the brief. Proprietary Excel integration, per-supplier accuracy dashboards, cryptographic audit seals, real-time collaboration, document replacement, multilingual benchmarks and automatic multi-page vision are deferred.

Next: obtain client import schema and tolerances; evaluate 200 historical packets with consent; calibrate field confidence; add document versions and page-level provenance; provision India infrastructure with backup/restore evidence; replace demo identities; add asynchronous inference and benchmark actual time saved. The first production acceptance gate is measured extraction/review performance, not a visual demo alone.
