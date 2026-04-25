import { useEffect, useState } from "react";
import { api, Posting } from "../lib/api";

const STATUSES = ["discovered", "scored", "queued", "review", "applying", "applied", "skipped", "failed"] as const;
type S = typeof STATUSES[number];

export default function Postings() {
  const [postings, setPostings] = useState<Posting[]>([]);
  const [filter, setFilter] = useState<S | "all">("review");

  async function load() {
    const url = filter === "all"
      ? "/api/automation/postings"
      : `/api/automation/postings?status=${filter}`;
    setPostings(await api.get<Posting[]>(url));
  }
  useEffect(() => { load(); }, [filter]);

  async function approve(id: string) {
    await api.post(`/api/automation/postings/${id}/approve`);
    load();
  }
  async function skip(id: string) {
    await api.post(`/api/automation/postings/${id}/skip`);
    load();
  }
  async function pollNow() {
    await api.post("/api/automation/sources/poll-now");
    setTimeout(load, 1500);
  }

  return (
    <div className="max-w-7xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Discovered postings</h1>
        <button onClick={pollNow}
                className="px-3 py-1.5 bg-blue-700 hover:bg-blue-600 rounded text-sm">
          poll sources now
        </button>
      </div>

      <div className="flex gap-2 text-sm">
        {(["all", ...STATUSES] as const).map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s as any)}
            className={`px-2 py-1 rounded ${
              filter === s ? "bg-zinc-700" : "bg-ash hover:bg-zinc-800"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="rounded border border-zinc-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-ash text-zinc-400 text-xs uppercase">
            <tr>
              <th className="text-left px-3 py-2">Score</th>
              <th className="text-left px-3 py-2">Company</th>
              <th className="text-left px-3 py-2">Role</th>
              <th className="text-left px-3 py-2">Location</th>
              <th className="text-left px-3 py-2">Salary</th>
              <th className="text-left px-3 py-2">Clearance</th>
              <th className="text-left px-3 py-2">ATS</th>
              <th className="text-left px-3 py-2">Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {postings.length === 0 && (
              <tr><td colSpan={9} className="px-3 py-4 text-center text-zinc-500">none</td></tr>
            )}
            {postings.map((p) => (
              <tr key={p.id} className="border-t border-zinc-800">
                <td className="px-3 py-2">
                  {p.score != null ? (p.score * 100).toFixed(0) : "—"}
                </td>
                <td className="px-3 py-2 font-medium">{p.company}</td>
                <td className="px-3 py-2">
                  <a className="hover:underline" href={p.job_url} target="_blank" rel="noreferrer">
                    {p.role_title}
                  </a>
                </td>
                <td className="px-3 py-2 text-zinc-400">
                  {p.location || "—"}{p.location_type ? ` · ${p.location_type}` : ""}
                </td>
                <td className="px-3 py-2 text-zinc-400">
                  {p.salary_min && p.salary_max
                    ? `$${(p.salary_min/1000).toFixed(0)}k–$${(p.salary_max/1000).toFixed(0)}k`
                    : "—"}
                </td>
                <td className="px-3 py-2 text-zinc-400">
                  {p.requires_clearance ? p.clearance_level || "yes" : "—"}
                </td>
                <td className="px-3 py-2 text-zinc-400">{p.ats || "—"}</td>
                <td className="px-3 py-2 text-zinc-400">{p.status}</td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => approve(p.id)}
                    className="px-2 py-0.5 rounded bg-emerald-700 hover:bg-emerald-600 text-xs"
                  >
                    apply
                  </button>
                  <button
                    onClick={() => skip(p.id)}
                    className="ml-1 px-2 py-0.5 rounded bg-zinc-700 hover:bg-zinc-600 text-xs"
                  >
                    skip
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
