import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface JobSource {
  id: string;
  kind: string;
  identifier: string;
  enabled: boolean;
  tos_acknowledged: boolean;
  last_polled_at?: string;
  last_error?: string;
}

interface KillSwitch {
  kill_switch: boolean;
  dry_run: boolean;
  per_job_approval: boolean;
}

interface GmailStatus {
  connected: boolean;
  user_email?: string;
  last_scanned_at?: string;
}

const SOURCE_KINDS = [
  "greenhouse_board",
  "lever_board",
  "rss",
  "clearancejobs",
  "linkedin",
  "indeed",
];

export default function Settings() {
  const [sources, setSources] = useState<JobSource[]>([]);
  const [ks, setKs] = useState<KillSwitch | null>(null);
  const [gmail, setGmail] = useState<GmailStatus | null>(null);
  const [newSource, setNewSource] = useState({
    kind: "greenhouse_board",
    identifier: "",
    tos_acknowledged: false,
  });

  async function reload() {
    setSources(await api.get<JobSource[]>("/api/automation/sources"));
    setKs(await api.get<KillSwitch>("/api/automation/kill-switch"));
    setGmail(await api.get<GmailStatus>("/api/auth/gmail/status"));
  }
  useEffect(() => { reload(); }, []);

  async function toggleKill() {
    await api.post(`/api/automation/kill-switch?value=${!ks?.kill_switch}`);
    reload();
  }
  async function addSource() {
    if (!newSource.identifier) return;
    if ((newSource.kind === "linkedin" || newSource.kind === "indeed") && !newSource.tos_acknowledged) {
      alert("LinkedIn/Indeed automation prohibited by ToS. Tick the acknowledgement to proceed.");
      return;
    }
    await api.post("/api/automation/sources", newSource);
    setNewSource({ kind: "greenhouse_board", identifier: "", tos_acknowledged: false });
    reload();
  }
  async function deleteSource(id: string) {
    await api.del(`/api/automation/sources/${id}`);
    reload();
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <section className="rounded border border-zinc-800 p-4 bg-ash space-y-3">
        <h2 className="font-medium">Safety</h2>
        <div className="flex items-center gap-3">
          <span className={`px-2 py-0.5 rounded text-xs ${
            ks?.kill_switch ? "bg-red-900/50 text-red-200" : "bg-emerald-900/50 text-emerald-200"
          }`}>
            kill_switch: {String(ks?.kill_switch)}
          </span>
          <span className="px-2 py-0.5 rounded text-xs bg-zinc-800">
            dry_run: {String(ks?.dry_run)}
          </span>
          <span className="px-2 py-0.5 rounded text-xs bg-zinc-800">
            per_job_approval: {String(ks?.per_job_approval)}
          </span>
        </div>
        <button
          onClick={toggleKill}
          className={`px-4 py-1.5 rounded text-sm ${
            ks?.kill_switch
              ? "bg-emerald-700 hover:bg-emerald-600"
              : "bg-red-700 hover:bg-red-600"
          }`}
        >
          {ks?.kill_switch ? "release kill switch" : "trip kill switch"}
        </button>
        <p className="text-xs text-zinc-500">
          dry_run and per_job_approval live in .env; restart the worker to change them.
        </p>
      </section>

      <section className="rounded border border-zinc-800 p-4 bg-ash space-y-3">
        <h2 className="font-medium">Gmail</h2>
        {gmail?.connected ? (
          <div className="text-sm">
            connected as <span className="text-emerald-300">{gmail.user_email}</span>
            {gmail.last_scanned_at && (
              <span className="text-zinc-500 ml-2">
                (last scanned {new Date(gmail.last_scanned_at).toLocaleString()})
              </span>
            )}
            <div className="mt-2 flex gap-2">
              <button
                onClick={async () => {
                  await api.post("/api/automation/email/scan-now");
                  alert("scan queued");
                }}
                className="px-3 py-1 rounded bg-blue-700 hover:bg-blue-600 text-sm"
              >
                scan now
              </button>
              <button
                onClick={async () => { await api.del("/api/auth/gmail"); reload(); }}
                className="px-3 py-1 rounded bg-zinc-700 hover:bg-zinc-600 text-sm"
              >
                disconnect
              </button>
            </div>
          </div>
        ) : (
          <a href="/api/auth/gmail/start"
             className="inline-block px-3 py-1.5 rounded bg-emerald-700 hover:bg-emerald-600 text-sm">
            connect Gmail (read-only)
          </a>
        )}
      </section>

      <section className="rounded border border-zinc-800 p-4 bg-ash space-y-3">
        <h2 className="font-medium">Job sources</h2>
        <ul className="space-y-1 text-sm">
          {sources.map((s) => (
            <li key={s.id} className="flex justify-between items-center p-2 rounded bg-zinc-900">
              <span>
                <span className="text-zinc-400">[{s.kind}]</span>{" "}
                <span className="font-mono">{s.identifier}</span>
                {(s.kind === "linkedin" || s.kind === "indeed") && (
                  <span className="ml-2 text-xs text-amber-300">opt-in</span>
                )}
                {s.last_error && (
                  <span className="ml-2 text-xs text-red-400">err: {s.last_error}</span>
                )}
              </span>
              <button onClick={() => deleteSource(s.id)} className="text-xs text-red-300">
                remove
              </button>
            </li>
          ))}
        </ul>
        <div className="flex gap-2 items-center">
          <select
            value={newSource.kind}
            onChange={(e) => setNewSource({ ...newSource, kind: e.target.value })}
            className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-sm"
          >
            {SOURCE_KINDS.map((k) => <option key={k}>{k}</option>)}
          </select>
          <input
            value={newSource.identifier}
            onChange={(e) => setNewSource({ ...newSource, identifier: e.target.value })}
            placeholder="company slug, RSS url, or query"
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-sm"
          />
          {(newSource.kind === "linkedin" || newSource.kind === "indeed") && (
            <label className="text-xs flex items-center gap-1 text-amber-300">
              <input
                type="checkbox"
                checked={newSource.tos_acknowledged}
                onChange={(e) => setNewSource({ ...newSource, tos_acknowledged: e.target.checked })}
              />
              I accept ToS / ban risk
            </label>
          )}
          <button onClick={addSource}
                  className="px-3 py-1 rounded bg-blue-700 hover:bg-blue-600 text-sm">
            add
          </button>
        </div>
      </section>
    </div>
  );
}
