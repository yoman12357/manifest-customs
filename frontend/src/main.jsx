import React, { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  Anchor,
  ArrowUpRight,
  ArrowLeft,
  ArrowRight,
  Plus,
  Search,
  LayoutGrid,
  Files,
  Activity,
  LogOut,
  ChevronRight,
  Check,
  CheckCircle2,
  AlertTriangle,
  Clock,
  UploadCloud,
  FileText,
  Download,
  X,
  ShieldCheck,
  Menu,
  RefreshCw,
  ExternalLink,
  Ship,
  Package,
  ScanLine,
  Loader2,
} from "lucide-react";
import "./styles.css";

let session = null;
async function api(path, options = {}) {
  const r = await fetch("/api" + path, {
    ...options,
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      "X-CSRF-Token": session?.csrf || "",
      ...options.headers,
    },
  });
  if (!r.ok) {
    let e = await r
      .json()
      .catch(() => ({ detail: "Service unavailable. Please try again." }));
    if (r.status === 401 && path != "/login")
      window.dispatchEvent(new Event("signedout"));
    throw Error(
      typeof e.detail === "string"
        ? e.detail
        : "Please check the entered values.",
    );
  }
  return r.json();
}
const label = (k) =>
  k.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
const date = (t) =>
  new Date(t * 1000).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
const time = (t) =>
  new Date(t * 1000).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
function IconButton({ children, ...props }) {
  return (
    <button className="icon-button" {...props}>
      {children}
    </button>
  );
}
function Badge({ status }) {
  return (
    <span
      className={
        "badge " +
        (status === "Approved"
          ? "green"
          : status === "In review"
            ? "amber"
            : "gray")
      }
    >
      <i />
      {status}
    </span>
  );
}
function App() {
  const [user, setUser] = useState(null),
    [boot, setBoot] = useState(true),
    [page, setPage] = useState("overview"),
    [sid, setSid] = useState(null),
    [error, setError] = useState(""),
    [mobile, setMobile] = useState(false),
    [version, setVersion] = useState(0);
  useEffect(() => {
    api("/me")
      .then((u) => {
        session = u;
        setUser(u);
      })
      .catch(() => {})
      .finally(() => setBoot(false));
    const fn = () => {
      session = null;
      setUser(null);
    };
    window.addEventListener("signedout", fn);
    return () => window.removeEventListener("signedout", fn);
  }, []);
  function go(p, id = null) {
    setPage(p);
    setSid(id);
    setMobile(false);
    setError("");
  }
  if (boot)
    return (
      <div className="fullscreen">
        <Loader2 className="spin" /> Opening your workspace…
      </div>
    );
  if (!user)
    return (
      <Login
        onLogin={(u) => {
          session = u;
          setUser(u);
        }}
      />
    );
  return (
    <div className="app">
      <aside className={mobile ? "sidebar open" : "sidebar"}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            go("overview");
          }}
        >
          <span className="brand-icon">
            <Anchor size={23} />
          </span>
          manifest<span className="brand-dot">.</span>
        </a>
        <div className="workspace">
          <span className="workspace-avatar">A</span>
          <div>
            Company A<div className="muted small">Customs documentation</div>
          </div>
          <span className="small workspace-tag">DEMO</span>
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav>
          {[
            ["overview", LayoutGrid, "Overview"],
            ["shipments", Files, "Shipments"],
            ["activity", Activity, "Activity log"],
          ].map(([p, I, t]) => (
            <button
              key={p}
              className={page === p ? "nav-item active" : "nav-item"}
              onClick={() => go(p)}
            >
              <I size={19} />
              {t}
              {p === "shipments" && <ChevronRight size={16} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-card">
            <ShieldCheck size={20} />
            <b>Human judgment. Always.</b>
            <p>
              AI prepares the draft.
              <br />
              Your team makes the call.
            </p>
          </div>
          <div className="profile">
            <span className="avatar">
              {user.name
                .split(" ")
                .map((s) => s[0])
                .join("")}
            </span>
            <div>
              <b>{user.name}</b>
              <div className="small muted">{label(user.role)}</div>
            </div>
            <IconButton
              title="Sign out"
              onClick={async () => {
                try {
                  await api("/logout", { method: "POST" });
                  session = null;
                  setUser(null);
                } catch (e) {
                  setError(e.message);
                }
              }}
            >
              <LogOut size={17} />
            </IconButton>
          </div>
        </div>
      </aside>
      {mobile && <div className="scrim" onClick={() => setMobile(false)} />}
      <main>
        <header className="topbar">
          <button
            className="mobile-menu icon-button"
            onClick={() => setMobile(!mobile)}
            aria-label="Open navigation"
          >
            <Menu />
          </button>
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />{" "}
            <b>{sid ? "Shipment review" : label(page)}</b>
          </div>
          <div className="top-right">
            <span className="online-dot" /> Local-first workspace{" "}
            <span className="top-divider" />
            <span className="small">Nhava Sheva, India</span>
          </div>
        </header>
        <div className="content">
          {error && (
            <div role="alert" className="notice error">
              {error}
              <IconButton title="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </IconButton>
            </div>
          )}
          {sid ? (
            <Shipment
              id={sid}
              user={user}
              back={() => go("shipments")}
              onError={setError}
            />
          ) : page === "activity" ? (
            <ActivityPage />
          ) : (
            <Dashboard
              overview={page === "overview"}
              version={version}
              open={(id) => go("shipments", id)}
              onCreate={() => {
                setVersion(version + 1);
              }}
              onError={setError}
            />
          )}
        </div>
        <footer>
          <span>MANIFEST / DOCUMENT INTELLIGENCE</span>
          <span>Built for a more certain clearance.</span>
        </footer>
      </main>
    </div>
  );
}
function Login({ onLogin }) {
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <div className="login">
      <section className="login-story">
        <div className="brand light">
          <span className="brand-icon">
            <Anchor />
          </span>
          manifest.
        </div>
        <span className="eyebrow">LESS RETYPING. MORE CERTAINTY.</span>
        <h1>
          Every shipment.
          <br />A clearer picture.
        </h1>
        <p>
          Turn shipping documents into reviewed, reliable data. With your team
          in control at every step.
        </p>
        <div className="document-art">
          <div className="art-page">
            <FileText size={32} />
            <b>COMMERCIAL INVOICE</b>
            <span />
            <span />
            <span />
            <div className="art-check">
              <Check size={16} /> Checked against packing list
            </div>
          </div>
          <div className="art-float">
            <ShieldCheck size={22} />
            <div>
              Ready for human review<small>Extract · Verify · Export</small>
            </div>
          </div>
        </div>
        <div className="login-foot">
          A thoughtful workspace for customs documentation.
        </div>
      </section>
      <section className="login-form">
        <div>
          <span className="eyebrow green-text">YOUR DOCUMENTATION DESK</span>
          <h2>Welcome back.</h2>
          <p className="muted">Sign in to keep your shipments moving.</p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              try {
                onLogin(
                  await api("/login", {
                    method: "POST",
                    body: JSON.stringify({ email, password }),
                  }),
                );
              } catch (e) {
                setError(e.message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Email address
              <input
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
              />
            </label>
            {error && (
              <div className="notice error" role="alert">
                {error}
              </div>
            )}
            <button className="primary full" disabled={busy}>
              {busy ? (
                <Loader2 className="spin" size={18} />
              ) : (
                <>
                  Sign in to workspace <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
          <div className="demo-box">
            <b>Reviewing the demo?</b>
            <p>Choose a role to fill in its demo credentials.</p>
            <div className="demo-roles">
              <button
                onClick={() => {
                  setEmail("executive@manifest.demo");
                  setPassword("ManifestDemo!2026");
                }}
              >
                Documentation executive
              </button>
              <button
                onClick={() => {
                  setEmail("manager@manifest.demo");
                  setPassword("ManifestDemo!2026");
                }}
              >
                Documentation manager
              </button>
            </div>
            <small>Fictional data only · Demo accounts are shared</small>
          </div>
          <p className="login-security">
            <ShieldCheck size={15} /> Local processing. No automatic customs
            filing.
          </p>
        </div>
      </section>
    </div>
  );
}

function Dashboard({ overview, version, open, onCreate, onError }) {
  const [rows, setRows] = useState(null),
    [q, setQ] = useState(""),
    [filter, setFilter] = useState("All shipments"),
    [modal, setModal] = useState(false),
    [loadError, setLoadError] = useState("");
  async function load() {
    setLoadError("");
    try {
      setRows(await api("/shipments"));
    } catch (e) {
      setLoadError(e.message);
    }
  }
  useEffect(() => {
    load();
  }, [version]);
  const filtered = rows?.filter(
    (r) =>
      (r.id + " " + r.supplier + " " + r.reference)
        .toLowerCase()
        .includes(q.toLowerCase()) &&
      (filter === "All shipments" || r.status === filter),
  );
  if (loadError) return <ErrorState message={loadError} retry={load} />;
  if (!rows) return <Loading />;
  const review = rows.filter((r) => r.status === "In review").length,
    approved = rows.filter((r) => r.status === "Approved").length;
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            {overview
              ? "YOUR OPERATIONS, AT A GLANCE"
              : "THE DOCUMENTATION DESK"}
          </span>
          <h1>
            {overview
              ? "A clear view. A confident next step."
              : "Shipment workspace"}
          </h1>
          <p className="muted">
            {overview
              ? "From the first document to the final check. Keep every shipment moving."
              : "One place for every document, discrepancy and decision."}
          </p>
        </div>
        <button className="primary" onClick={() => setModal(true)}>
          <Plus size={18} />
          New shipment
        </button>
      </div>
      {overview && (
        <>
          <div className="stats">
            <Stat
              title="Total shipments"
              value={rows.length.toString().padStart(2, "0")}
              sub="In your workspace"
              icon={Ship}
            />
            <Stat
              title="Needs review"
              value={review.toString().padStart(2, "0")}
              sub="Your attention makes the difference"
              icon={ScanLine}
              amber
            />
            <Stat
              title="Ready to export"
              value={approved.toString().padStart(2, "0")}
              sub="Verified and manager-approved"
              icon={CheckCircle2}
            />
            <Stat
              title="Documents received"
              value={rows
                .reduce((n, r) => n + r.document_count, 0)
                .toString()
                .padStart(2, "0")}
              sub="Originals, always within reach"
              icon={FileText}
            />
          </div>
          <div className="insight">
            <div className="insight-symbol">
              <ScanLine size={25} />
            </div>
            <div>
              <span className="eyebrow">A SECOND PAIR OF EYES</span>
              <h3>Small discrepancies. Big differences.</h3>
              <p>
                Manifest checks weights, packages and invoice totals across your
                documents. Resolve the details before they become delays.
              </p>
            </div>
            <span className="insight-decoration">
              01 <span>/</span> 03
            </span>
          </div>
        </>
      )}
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>
              {overview ? "Your shipments" : "All shipments"}{" "}
              <span className="count">{rows.length}</span>
            </h2>
            <p className="muted small">
              Every document connected. Every decision traceable.
            </p>
          </div>
          <IconButton title="Refresh shipments" onClick={load}>
            <RefreshCw size={17} />
          </IconButton>
        </div>
        <div className="table-tools">
          <div className="tabs">
            {[
              "All shipments",
              "In review",
              "Approved",
              "Awaiting documents",
            ].map((f) => (
              <button
                key={f}
                className={f === filter ? "selected" : ""}
                onClick={() => setFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="search">
            <Search size={17} />
            <input
              aria-label="Search shipments"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search shipments…"
            />
          </div>
        </div>
        <div className="table-wrap">
          <table className="shipments-table">
            <thead>
              <tr>
                <th>SHIPMENT / REFERENCE</th>
                <th>SUPPLIER</th>
                <th>DOCUMENTS</th>
                <th>STATUS</th>
                <th>UPDATED</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.id} onClick={() => open(r.id)}>
                  <td>
                    <button
                      className="shipment-link"
                      onClick={(e) => {
                        e.stopPropagation();
                        open(r.id);
                      }}
                    >
                      {r.id}
                    </button>
                    <div className="muted small">{r.reference}</div>
                  </td>
                  <td>
                    <b className="supplier">{r.supplier}</b>
                    <div className="small muted">Import shipment</div>
                  </td>
                  <td>
                    <span className="doc-progress">
                      {[0, 1, 2].map((i) => (
                        <span
                          key={i}
                          className={r.document_count > i ? "filled" : ""}
                        >
                          <FileText size={13} />
                        </span>
                      ))}
                      <span className="muted small">{r.document_count}/3</span>
                    </span>
                  </td>
                  <td>
                    <Badge status={r.status} />
                  </td>
                  <td className="muted small">{date(r.updated)}</td>
                  <td>
                    <ArrowUpRight size={17} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <Empty
            title={q ? "No matching shipments" : "A clean slate"}
            text={
              q
                ? "Try a different reference or supplier name."
                : "Create a shipment to start your first document packet."
            }
          />
        )}
        <div className="table-foot">
          <span>
            {filtered.length} shipment{filtered.length !== 1 ? "s" : ""}
          </span>
          <span>
            <ShieldCheck size={14} /> Export requires human review
          </span>
        </div>
      </section>
      <div className="workflow-note">
        <span>YOUR PATH TO CLEARANCE</span>
        <div>
          <b>01</b> Upload documents <ChevronRight size={15} />
          <b>02</b> Review & reconcile <ChevronRight size={15} />
          <b>03</b> Approve & export
        </div>
      </div>
      {modal && (
        <NewShipment
          close={() => setModal(false)}
          created={(id) => {
            setModal(false);
            onCreate();
            open(id);
          }}
        />
      )}
    </>
  );
}
function Stat({ title, value, sub, icon: I, amber }) {
  return (
    <div className="stat">
      <div>
        {title}
        <I size={18} className={amber ? "amber-text" : "muted"} />
      </div>
      <strong>{value}</strong>
      <small>
        {amber && <i className="amber-dot" />}
        {sub}
      </small>
    </div>
  );
}
function NewShipment({ close, created }) {
  const [supplier, setSupplier] = useState(""),
    [reference, setReference] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <div className="modal-backdrop">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-title"
      >
        <div className="modal-head">
          <span className="eyebrow">START A DOCUMENT PACKET</span>
          <IconButton title="Close" onClick={close}>
            <X />
          </IconButton>
        </div>
        <h2 id="new-title">New shipment</h2>
        <p className="muted">Add the basics. Bring the documents next.</p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            try {
              created(
                (
                  await api("/shipments", {
                    method: "POST",
                    body: JSON.stringify({ supplier, reference }),
                  })
                ).id,
              );
            } catch (e) {
              setError(e.message);
              setBusy(false);
            }
          }}
        >
          <label>
            Supplier
            <input
              autoFocus
              required
              minLength={2}
              maxLength={120}
              value={supplier}
              onChange={(e) => setSupplier(e.target.value)}
              placeholder="e.g. Company B (China)"
            />
          </label>
          <label>
            Your reference
            <input
              required
              minLength={2}
              maxLength={120}
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="e.g. LED panel lights · November"
            />
          </label>
          {error && (
            <p className="error-text" role="alert">
              {error}
            </p>
          )}
          <button className="primary full" disabled={busy}>
            {busy ? "Creating…" : "Create shipment"}
            <ArrowRight size={17} />
          </button>
        </form>
      </section>
    </div>
  );
}

function Shipment({ id, user, back, onError }) {
  const [s, setS] = useState(null),
    [tab, setTab] = useState("documents"),
    [active, setActive] = useState("invoice"),
    [busy, setBusy] = useState(false),
    [uploading, setUploading] = useState(""),
    [error, setError] = useState("");
  async function load() {
    try {
      setS(await api("/shipments/" + id));
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => {
    load();
  }, [id]);
  async function upload(kind, file) {
    if (!file) return;
    setUploading(kind);
    onError("");
    const form = new FormData();
    form.append("kind", kind);
    form.append("file", file);
    try {
      await api("/shipments/" + id + "/documents", {
        method: "POST",
        body: form,
      });
      await load();
      setActive(kind);
    } catch (e) {
      onError(e.message);
    } finally {
      setUploading("");
    }
  }
  if (error) return <ErrorState message={error} retry={load} />;
  if (!s) return <Loading />;
  const failed = s.checks.filter((c) => !c.passed),
    doc = s.documents.find((d) => d.kind === active),
    confirmed = s.documents.reduce(
      (n, d) => n + Object.values(d.fields).filter((f) => f.confirmed).length,
      0,
    ),
    total = s.documents.reduce((n, d) => n + Object.keys(d.fields).length, 0);
  return (
    <>
      <button className="back-button" onClick={back}>
        <ArrowLeft size={16} /> All shipments
      </button>
      <div className="page-heading shipment-heading">
        <div>
          <span className="eyebrow">SHIPMENT PACKET</span>
          <h1>
            {s.id} <Badge status={s.status} />
          </h1>
          <p className="muted">
            {s.supplier} <span className="middle-dot">·</span> {s.reference}
          </p>
        </div>
        <div className="actions">
          {user.role === "manager" && (
            <button
              className="secondary"
              disabled={busy || failed.length > 0 || s.status === "Approved"}
              onClick={async () => {
                setBusy(true);
                try {
                  await api("/shipments/" + id + "/approve", {
                    method: "POST",
                    body: JSON.stringify({ revision: s.revision }),
                  });
                  await load();
                } catch (e) {
                  onError(e.message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <ShieldCheck size={17} />
              Approve packet
            </button>
          )}
          <button
            className="primary"
            disabled={s.status !== "Approved"}
            title={
              s.status !== "Approved"
                ? "Complete review and manager approval to export"
                : "Download reviewed data"
            }
            onClick={() => {
              window.location.href = "/api/shipments/" + id + "/export";
              setTimeout(load, 500);
            }}
          >
            <Download size={17} /> Export CSV
          </button>
        </div>
      </div>
      <div className="packet-summary">
        <span>
          <Files size={17} />
          <b>{s.documents.length}/3</b> documents
        </span>
        <span>
          <CheckCircle2 size={17} />
          <b>
            {confirmed}/{total}
          </b>{" "}
          fields confirmed
        </span>
        <span className={failed.length ? "amber-text" : "green-text"}>
          {failed.length ? (
            <AlertTriangle size={17} />
          ) : (
            <ShieldCheck size={17} />
          )}
          <b>{failed.length}</b> open checks
        </span>
      </div>
      <div className="detail-tabs">
        {[
          ["documents", "Documents & review"],
          ["checks", "Cross-checks"],
          ["history", "Edit history"],
        ].map(([key, title]) => (
          <button
            key={key}
            className={tab === key ? "selected" : ""}
            onClick={() => setTab(key)}
          >
            {title}
            {key === "checks" && failed.length > 0 && (
              <span className="count amber-count">{failed.length}</span>
            )}
          </button>
        ))}
      </div>
      {tab === "documents" && (
        <>
          <div className="document-slots">
            {["invoice", "packing_list", "bill_of_lading"].map((kind, i) => {
              const d = s.documents.find((d) => d.kind === kind);
              return (
                <div
                  key={kind}
                  className={
                    "document-slot " + (active === kind ? "chosen" : "")
                  }
                >
                  <button
                    className="slot-select"
                    onClick={() => setActive(kind)}
                  >
                    <div className="slot-icon">
                      <FileText size={21} />
                    </div>
                    <div>
                      <span className="eyebrow">DOCUMENT 0{i + 1}</span>
                      <b>{label(kind)}</b>
                      <small>
                        {d ? d.filename : "PDF, PNG or JPEG · up to 10 MB"}
                      </small>
                    </div>
                    {d ? (
                      <CheckCircle2 size={18} className="green-text" />
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </button>
                  {!d && (
                    <label
                      className={
                        "upload-button " + (uploading ? "disabled" : "")
                      }
                    >
                      <UploadCloud size={15} />
                      {uploading === kind
                        ? "Reading document…"
                        : "Upload document"}
                      <input
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg"
                        disabled={!!uploading}
                        onChange={(e) => {
                          upload(kind, e.target.files[0]);
                          e.target.value = "";
                        }}
                      />
                    </label>
                  )}
                </div>
              );
            })}
          </div>
          {uploading && (
            <div className="notice">
              <Loader2 className="spin" size={18} /> Extracting from your
              original document. Vision may take up to two minutes. You can
              review every reading before it is used.
            </div>
          )}
          {doc ? (
            <>
              <div className="review-heading">
                <div>
                  <h2>Read. Compare. Confirm.</h2>
                  <p className="muted small">
                    Confirm each field against its source. Corrections are saved
                    to the audit trail.
                  </p>
                </div>
                <span className="engine-label">
                  <ScanLine size={15} />
                  {doc.engine === "local-vision"
                    ? "Local vision draft"
                    : doc.engine === "pdf-text"
                      ? "PDF text extraction"
                      : "Manual entry required"}
                </span>
              </div>
              <div className="notice compact">{doc.note}</div>
              <div className="review-grid">
                <section className="original-panel">
                  <div className="original-bar">
                    <span>
                      <FileText size={16} />
                      Original document
                    </span>
                    <a
                      href={"/api/documents/" + doc.id + "/file"}
                      target="_blank"
                      rel="noreferrer"
                      title="Open original document"
                    >
                      <ExternalLink size={16} />
                    </a>
                  </div>
                  {doc.mime === "application/pdf" ? (
                    <iframe
                      title={"Original " + label(doc.kind)}
                      src={"/api/documents/" + doc.id + "/file#toolbar=1"}
                    />
                  ) : (
                    <img
                      alt={"Original " + label(doc.kind)}
                      src={"/api/documents/" + doc.id + "/file"}
                    />
                  )}
                  <div className="source-foot">
                    Read from the original. Confirm with confidence.
                  </div>
                </section>
                <section className="fields-panel">
                  <div className="fields-heading">
                    <b>Extracted fields</b>
                    <span className="small muted">
                      {
                        Object.values(doc.fields).filter((f) => f.confirmed)
                          .length
                      }
                      /{Object.keys(doc.fields).length} confirmed
                    </span>
                  </div>
                  {Object.entries(doc.fields).map(([key, f]) => (
                    <FieldRow
                      key={doc.id + key + f.value + f.confirmed}
                      fieldKey={key}
                      field={f}
                      disabled={busy}
                      save={async (value) => {
                        setBusy(true);
                        try {
                          await api("/documents/" + doc.id + "/fields/" + key, {
                            method: "PATCH",
                            body: JSON.stringify({
                              value,
                              revision: s.revision,
                            }),
                          });
                          await load();
                        } catch (e) {
                          onError(e.message);
                        } finally {
                          setBusy(false);
                        }
                      }}
                    />
                  ))}
                  <div className="fields-footer">
                    <ShieldCheck size={16} /> Nothing exports without a human
                    check.
                  </div>
                </section>
              </div>
            </>
          ) : (
            <div
              className="upload-empty"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                if (!uploading) upload(active, e.dataTransfer.files[0]);
              }}
            >
              <span className="empty-icon">
                <UploadCloud size={34} />
              </span>
              <h2>Bring your {label(active).toLowerCase()} into focus.</h2>
              <p className="muted">
                Drop a file here, or use the upload button above.
                <br />
                We’ll prepare a draft. You’ll have the final say.
              </p>
              <div className="small muted">
                PDF, PNG or JPEG · 10 MB maximum · 10 pages maximum
              </div>
            </div>
          )}
        </>
      )}
      {tab === "checks" && (
        <>
          <div
            className={"check-banner " + (!failed.length ? "all-clear" : "")}
          >
            <span className="empty-icon">
              {failed.length ? <AlertTriangle /> : <ShieldCheck />}
            </span>
            <div>
              <h2>
                {failed.length
                  ? "A few details need a closer look."
                  : "The documents tell the same story."}
              </h2>
              <p>
                {failed.length
                  ? "Resolve discrepancies in Documents & review. Checks update as you confirm fields."
                  : user.role === "manager"
                    ? "The packet is ready for your approval."
                    : "Ask your documentation manager to approve this packet."}
              </p>
            </div>
          </div>
          <div className="checks-list">
            {s.checks.map((c) => (
              <div key={c.code} className="check-row">
                {c.passed ? (
                  <CheckCircle2 className="green-text" size={21} />
                ) : (
                  <AlertTriangle className="amber-text" size={21} />
                )}
                <div>
                  <b>{c.title}</b>
                  <p className="muted small">{c.detail}</p>
                </div>
                <span
                  className={
                    "check-label " + (c.passed ? "green-text" : "amber-text")
                  }
                >
                  {c.passed ? "Passed" : "Needs review"}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
      {tab === "history" && <Audit rows={s.audit} />}
      {s.status !== "Approved" && (
        <div className="review-guidance">
          <ShieldCheck size={18} />
          {failed.length
            ? "Export is locked until required fields are confirmed and every cross-check passes."
            : user.role === "manager"
              ? "All checks passed. Approve the packet to unlock CSV export."
              : "All checks passed. Your manager can now approve this packet."}
        </div>
      )}
    </>
  );
}
function FieldRow({ fieldKey, field: f, save, disabled }) {
  const [value, setValue] = useState(f.value);
  const lines = fieldKey === "line_items";
  return (
    <div
      className={
        "field-row " +
        (f.confirmed ? "confirmed" : f.confidence < 0.8 ? "uncertain" : "")
      }
    >
      <div className="field-meta">
        <label htmlFor={fieldKey}>
          {label(fieldKey)}
          {["gross_weight", "net_weight"].includes(fieldKey) && " (kg)"}
        </label>
        <span
          className={
            f.confirmed
              ? "green-text"
              : f.confidence < 0.8
                ? "amber-text"
                : "muted"
          }
        >
          {f.confirmed ? (
            <>
              <Check size={12} /> Verified
            </>
          ) : f.confidence === 0 ? (
            "Manual entry"
          ) : (
            Math.round(f.confidence * 100) + "% ? draft"
          )}
        </span>
      </div>
      {lines && <LineItems value={value} change={setValue} />}
      <div className="field-input">
        {!lines && (
          <input
            id={fieldKey}
            value={value}
            maxLength={500}
            onChange={(e) => setValue(e.target.value)}
            aria-label={label(fieldKey)}
            placeholder="Enter from original document"
          />
        )}
        <button
          disabled={
            disabled || !value.trim() || (f.confirmed && value === f.value)
          }
          className={f.confirmed && value === f.value ? "confirmed-button" : ""}
          onClick={() => save(value)}
          title={"Confirm " + label(fieldKey)}
        >
          {f.confirmed && value === f.value ? (
            <Check size={16} />
          ) : (
            <>
              Confirm{lines ? " line items" : ""}
              <Check size={13} />
            </>
          )}
        </button>
      </div>
      <p className="field-source">{f.source}</p>
    </div>
  );
}
function LineItems({ value, change }) {
  let items;
  try {
    items = JSON.parse(value);
    if (!Array.isArray(items)) items = [];
  } catch {
    items = [];
  }
  const update = (n, key, v) =>
    change(
      JSON.stringify(
        items.map((i, idx) => (idx === n ? { ...i, [key]: v } : i)),
      ),
    );
  return (
    <div className="line-items">
      {items.map((item, n) => (
        <div className="line-item" key={n}>
          <div className="line-item-title">
            Item {n + 1}
            <button
              title={"Remove item " + (n + 1)}
              onClick={() =>
                change(JSON.stringify(items.filter((_, i) => i !== n)))
              }
            >
              <X size={13} />
            </button>
          </div>
          <label>
            Description
            <input
              aria-label={"Item " + (n + 1) + " description"}
              value={item.description || ""}
              onChange={(e) => update(n, "description", e.target.value)}
            />
          </label>
          <div className="line-item-numbers">
            {[
              ["hsn", "HSN"],
              ["quantity", "Quantity"],
              ["unit_price", "Unit price"],
            ].map(([key, title]) => (
              <label key={key}>
                {title}
                <input
                  aria-label={"Item " + (n + 1) + " " + title}
                  value={item[key] ?? ""}
                  inputMode={key === "hsn" ? "text" : "decimal"}
                  onChange={(e) => update(n, key, e.target.value)}
                />
              </label>
            ))}
          </div>
        </div>
      ))}
      <button
        className="add-line"
        disabled={items.length >= 100}
        onClick={() =>
          change(
            JSON.stringify([
              ...items,
              { description: "", hsn: "", quantity: "", unit_price: "" },
            ]),
          )
        }
      >
        <Plus size={13} />
        Add line item
      </button>
    </div>
  );
}
function ActivityPage() {
  const [rows, setRows] = useState(null),
    [err, setErr] = useState("");
  async function load() {
    try {
      setRows(await api("/activity"));
      setErr("");
    } catch (e) {
      setErr(e.message);
    }
  }
  useEffect(() => {
    load();
  }, []);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">A RECORD OF EVERY DECISION</span>
          <h1>Nothing lost in the handover.</h1>
          <p className="muted">
            Uploads, corrections, approvals and exports. A shared trail you can
            trust.
          </p>
        </div>
      </div>
      {err ? (
        <ErrorState message={err} retry={load} />
      ) : rows ? (
        <Audit rows={rows} />
      ) : (
        <Loading />
      )}
    </>
  );
}
function Audit({ rows }) {
  return (
    <section className="panel audit">
      <div className="panel-header">
        <h2>Activity trail</h2>
        <span className="small muted">Latest 100 events</span>
      </div>
      {rows.length ? (
        rows.map((r) => (
          <div className="audit-row" key={r.id}>
            <span className="audit-icon">
              <Activity size={16} />
            </span>
            <div>
              <b>{r.action}</b>
              <p className="small muted">
                {r.actor} · {r.shipment}
              </p>
              {r.detail && <p className="audit-detail">{r.detail}</p>}
            </div>
            <time className="small muted">{time(r.created)}</time>
          </div>
        ))
      ) : (
        <Empty
          title="Every story starts somewhere"
          text="Your team's actions will appear here."
        />
      )}
    </section>
  );
}
function Loading() {
  return (
    <div className="loading">
      <Loader2 className="spin" />
      Loading your workspace…
    </div>
  );
}
function ErrorState({ message, retry }) {
  return (
    <div className="empty">
      <AlertTriangle />
      <h2>We couldn’t load this view.</h2>
      <p>{message}</p>
      <button className="secondary" onClick={retry}>
        <RefreshCw size={16} />
        Try again
      </button>
    </div>
  );
}
function Empty({ title, text }) {
  return (
    <div className="empty">
      <Package size={30} />
      <h3>{title}</h3>
      <p className="muted">{text}</p>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
