import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_BASE_DEFAULT =
  import.meta.env.VITE_API_BASE || "https://permissions-as-data-ojt.onrender.com";

const SAMPLE_POLICY = `{
  "rules": [
    { "role": "manager", "action": "write", "effect": "allow", "resource_match": { "status": "DRAFT" } },
    { "role": "employee", "action": "read", "effect": "allow" },
    { "role": "*", "action": "*", "effect": "deny", "resource_match": { "category": "finance" } }
  ]
}`;

const SAMPLE_BATCH = `[
  {
    "subject": { "role": "manager" },
    "action": "write",
    "resource": { "status": "DRAFT" },
    "dry_run": false
  },
  {
    "subject": { "role": "employee" },
    "action": "write",
    "resource": { "status": "FINAL" },
    "dry_run": false
  }
]`;

const tabs = [
  { id: "auth", label: "Authorization" },
  { id: "batch", label: "Batch" },
  { id: "roles", label: "Roles (Admin)" },
  { id: "policies", label: "Policies (Admin)" },
  { id: "health", label: "Health" },
];

function StatusChip({ ok, status }) {
  const cls = ok ? "chip success" : "chip danger";
  return <span className={cls}>{ok ? "OK" : "ERR"} {status}</span>;
}

export default function App() {
  const [apiBase, setApiBase] = useState(API_BASE_DEFAULT);
  const [adminKey, setAdminKey] = useState("");
  const [tab, setTab] = useState("auth");
  const [output, setOutput] = useState({ message: "Waiting for actions..." });
  const [history, setHistory] = useState([]);
  const [lastRequest, setLastRequest] = useState(null);

  // Forms
  const [subjectText, setSubjectText] = useState(`{ "role": "manager" }`);
  const [actionText, setActionText] = useState("write");
  const [resourceText, setResourceText] = useState(`{ "status": "DRAFT" }`);
  const [dryRun, setDryRun] = useState(false);

  const [batchText, setBatchText] = useState(SAMPLE_BATCH);

  const [roleName, setRoleName] = useState("manager");
  const [roleDesc, setRoleDesc] = useState("Manager role");
  const [roleParents, setRoleParents] = useState("employee");

  const [policyName, setPolicyName] = useState("default_policy");
  const [policyContent, setPolicyContent] = useState(SAMPLE_POLICY);
  const [activateId, setActivateId] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("adminKey");
    if (stored) setAdminKey(stored);
    const storedBase = localStorage.getItem("apiBase");
    if (storedBase) setApiBase(storedBase);
  }, []);

  const saveAdminKey = () => {
    localStorage.setItem("adminKey", adminKey);
    setOutput({ message: "Admin key saved (localStorage)", adminKeySet: !!adminKey });
  };

  const saveApiBase = () => {
    localStorage.setItem("apiBase", apiBase);
    setOutput({ message: "API base saved", apiBase });
  };

  const parseJSON = (text, fallback = null) => {
    try {
      return JSON.parse(text);
    } catch (e) {
      throw new Error("Invalid JSON: " + e.message);
    }
  };

  const request = async (method, path, body = null, needAdmin = false) => {
    const url = `${apiBase}${path}`;
    const headers = { "Content-Type": "application/json" };
    if (needAdmin) {
      if (!adminKey) {
        setOutput({ error: "Admin key required" });
        return;
      }
      headers.Authorization = `Bearer ${adminKey}`;
    }
    const reqInfo = { method, url, headers, body };
    setLastRequest(reqInfo);

    try {
      const res = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
      let data = null;
      try {
        data = await res.json();
      } catch {
        data = await res.text();
      }
      const result = { ok: res.ok, status: res.status, data, path };
      setOutput(result);
      setHistory((h) => [{ ...result, ts: new Date().toISOString(), method }, ...h].slice(0, 25));
    } catch (err) {
      const error = { ok: false, status: "network", data: err.message };
      setOutput(error);
      setHistory((h) => [{ ...error, ts: new Date().toISOString(), method, path }, ...h].slice(0, 25));
    }
  };

  const copyCurl = () => {
    if (!lastRequest) return;
    const { method, url, headers, body } = lastRequest;
    const headerStr = Object.entries(headers)
      .map(([k, v]) => `-H "${k}: ${v}"`)
      .join(" ");
    const bodyStr = body ? `-d '${JSON.stringify(body)}'` : "";
    const curl = `curl -X ${method} ${headerStr} ${bodyStr} "${url}"`;
    navigator.clipboard.writeText(curl);
    setOutput((o) => ({ ...o, message: "cURL copied to clipboard" }));
  };

  const latestStatus = useMemo(() => {
    if (!history.length) return null;
    const h = history[0];
    return <StatusChip ok={h.ok} status={h.status} />;
  }, [history]);

  return (
    <div className="page">
      <header className="top">
      <div>
          <h1>Permissions-as-Data Console</h1>
          <p className="muted">Hybrid RBAC + ABAC • Policy versioning • Audit</p>
        </div>
        <div className="pill">
          <span className="badge">API Base</span>
          <input value={apiBase} onChange={(e) => setApiBase(e.target.value)} />
          <button onClick={saveApiBase}>Save</button>
        </div>
        <div className="pill">
          <span className="badge">Admin Key</span>
          <input
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            placeholder="SUPER_SECRET_ADMIN_KEY_2404"
          />
          <button onClick={saveAdminKey}>Save</button>
        </div>
      </header>

      <nav className="tabs">
        {tabs.map((t) => (
          <button key={t.id} className={tab === t.id ? "tab active" : "tab"} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
        <div className="status">{latestStatus}</div>
        <div className="status">
          {lastRequest && <button onClick={copyCurl} className="ghost">Copy cURL</button>}
      </div>
      </nav>

      {tab === "auth" && (
        <section className="grid two">
      <div className="card">
            <h3>Single Access Check</h3>
            <label>Subject (JSON)</label>
            <textarea value={subjectText} onChange={(e) => setSubjectText(e.target.value)} />
            <label>Action</label>
            <input value={actionText} onChange={(e) => setActionText(e.target.value)} />
            <label>Resource (JSON)</label>
            <textarea value={resourceText} onChange={(e) => setResourceText(e.target.value)} />
            <label className="row-line">
              <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} /> Dry run (skip audit log)
            </label>
            <button
              onClick={() =>
                request("POST", "/access", {
                  subject: parseJSON(subjectText),
                  action: actionText,
                  resource: parseJSON(resourceText),
                  dry_run: dryRun,
                })
              }
            >
              Evaluate
        </button>
          </div>
        </section>
      )}

      {tab === "batch" && (
        <section className="grid one">
          <div className="card">
            <h3>Batch Access Check</h3>
            <label>Requests (JSON array)</label>
            <textarea value={batchText} onChange={(e) => setBatchText(e.target.value)} />
            <button onClick={() => request("POST", "/access/batch", parseJSON(batchText))}>Evaluate Batch</button>
      </div>
        </section>
      )}

      {tab === "roles" && (
        <section className="grid two">
          <div className="card">
            <h3>Create Role</h3>
            <label>Name</label>
            <input value={roleName} onChange={(e) => setRoleName(e.target.value)} />
            <label>Description</label>
            <input value={roleDesc} onChange={(e) => setRoleDesc(e.target.value)} />
            <label>Parent names (comma-separated)</label>
            <input value={roleParents} onChange={(e) => setRoleParents(e.target.value)} />
            <button
              onClick={() =>
                request(
                  "POST",
                  "/roles/",
                  {
                    name: roleName,
                    description: roleDesc || null,
                    parent_names: roleParents
                      ? roleParents.split(",").map((s) => s.trim()).filter(Boolean)
                      : [],
                  },
                  true
                )
              }
            >
              Create Role
            </button>
          </div>
        </section>
      )}

      {tab === "policies" && (
        <section className="grid two">
          <div className="card">
            <h3>Create Policy</h3>
            <label>Name</label>
            <input value={policyName} onChange={(e) => setPolicyName(e.target.value)} />
            <label>Content (JSON)</label>
            <textarea value={policyContent} onChange={(e) => setPolicyContent(e.target.value)} />
            <div className="row-line">
              <button onClick={() => request("POST", "/policies/", { name: policyName, content: parseJSON(policyContent) }, true)}>
                Create Policy
              </button>
              <button className="ghost" onClick={() => setPolicyContent(SAMPLE_POLICY)}>Reset sample</button>
            </div>
          </div>

          <div className="card">
            <h3>Manage Policies</h3>
            <label>Activate policy ID</label>
            <input value={activateId} onChange={(e) => setActivateId(e.target.value)} />
            <div className="row-line">
              <button onClick={() => request("POST", `/policies/${activateId}/activate`, null, true)}>Activate</button>
              <button className="ghost" onClick={() => request("GET", "/policies/", null, true)}>List Policies</button>
              <button className="ghost" onClick={() => request("GET", "/policies/active", null, true)}>Get Active</button>
            </div>
          </div>
        </section>
      )}

      {tab === "health" && (
        <section className="grid one">
          <div className="card">
            <h3>Health</h3>
            <button onClick={() => request("GET", "/health")}>Check /health</button>
            <p className="muted">Also: GET / for a simple status</p>
          </div>
        </section>
      )}

      <section className="grid two">
        <div className="card">
          <h3>Latest Response</h3>
          <pre>{JSON.stringify(output, null, 2)}</pre>
        </div>
        <div className="card">
          <h3>History</h3>
          {history.length === 0 && <p className="muted">No requests yet.</p>}
          {history.map((h, i) => (
            <div key={i} className="history-row">
              <div className="row-line">
                <StatusChip ok={h.ok} status={h.status} />
                <span className="muted">{h.method} {h.path}</span>
                <span className="muted">{h.ts}</span>
              </div>
              <pre>{JSON.stringify(h.data, null, 2)}</pre>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
