import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Application, ApplicationStatus } from "../lib/api";
import StatusBadge from "../components/StatusBadge";

const PIPELINE: ApplicationStatus[] = [
  "queued",
  "applied",
  "screening",
  "interview",
  "offer",
  "rejected",
  "ghosted",
];

export default function Dashboard() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "all">("all");

  useEffect(() => {
    api.get<Application[]>("/api/applications").then((data) => {
      setApps(data);
      setLoading(false);
    });
  }, []);

  const filtered = apps.filter((a) => {
    if (statusFilter !== "all" && a.status !== statusFilter) return false;
    if (search && !`${a.company} ${a.role_title}`.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    return true;
  });

  const counts: Record<ApplicationStatus, number> = {
    queued: 0, applied: 0, screening: 0, interview: 0, offer: 0, rejected: 0, ghosted: 0,
  };
  apps.forEach((a) => (counts[a.status] += 1));

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold">Pipeline</h1>

      <div className="grid grid-cols-7 gap-3">
        {PIPELINE.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(statusFilter === s ? "all" : s)}
            className={`text-left rounded border p-3 transition ${
              statusFilter === s
                ? "border-zinc-500 bg-zinc-800"
                : "border-zinc-800 hover:border-zinc-700 bg-ash"
            }`}
          >
            <div className="text-xs text-zinc-400 capitalize">{s}</div>
            <div className="text-2xl font-medium">{counts[s]}</div>
          </button>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="search company / role"
          className="px-3 py-2 rounded bg-ash border border-zinc-800 text-sm flex-1 max-w-md"
        />
        {statusFilter !== "all" && (
          <button
            onClick={() => setStatusFilter("all")}
            className="text-xs text-zinc-400 hover:text-white"
          >
            clear filter ({statusFilter})
          </button>
        )}
      </div>

      <div className="rounded border border-zinc-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-ash border-b border-zinc-800 text-zinc-400 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2">Company</th>
              <th className="text-left px-4 py-2">Role</th>
              <th className="text-left px-4 py-2">Location</th>
              <th className="text-left px-4 py-2">Salary</th>
              <th className="text-left px-4 py-2">Method</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-zinc-500">loading…</td></tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-zinc-500">no applications yet</td></tr>
            )}
            {filtered.map((a) => (
              <tr key={a.id} className="border-t border-zinc-800 hover:bg-zinc-900/50">
                <td className="px-4 py-2 font-medium">
                  <Link to={`/applications/${a.id}`} className="hover:underline">{a.company}</Link>
                </td>
                <td className="px-4 py-2 text-zinc-300">{a.role_title}</td>
                <td className="px-4 py-2 text-zinc-400">
                  {a.location || "—"}{a.location_type ? ` · ${a.location_type}` : ""}
                </td>
                <td className="px-4 py-2 text-zinc-400">
                  {a.salary_min && a.salary_max
                    ? `$${(a.salary_min/1000).toFixed(0)}k–$${(a.salary_max/1000).toFixed(0)}k`
                    : "—"}
                </td>
                <td className="px-4 py-2">
                  <span className={a.method === "auto" ? "text-emerald-400" : "text-zinc-400"}>
                    {a.method}
                  </span>
                </td>
                <td className="px-4 py-2"><StatusBadge status={a.status} /></td>
                <td className="px-4 py-2 text-zinc-500 text-xs">
                  {new Date(a.updated_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
