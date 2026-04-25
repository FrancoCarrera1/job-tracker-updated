import { useEffect, useState } from "react";
import { api, Analytics as A } from "../lib/api";

export default function Analytics() {
  const [data, setData] = useState<A | null>(null);
  useEffect(() => {
    api.get<A>("/api/analytics").then(setData);
  }, []);
  if (!data) return <div className="text-zinc-500">loading…</div>;

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <h1 className="text-2xl font-semibold">Analytics</h1>

      <div className="grid grid-cols-3 gap-4">
        <Stat label="Response rate" value={`${(data.response_rate * 100).toFixed(0)}%`} />
        <Stat label="Interview conversion" value={`${(data.interview_conversion * 100).toFixed(0)}%`} />
        <Stat label="Median time-to-response"
              value={data.median_time_to_response_days != null
                ? `${data.median_time_to_response_days.toFixed(1)} days`
                : "—"} />
      </div>

      <section>
        <h2 className="text-sm uppercase text-zinc-400 mb-2">Totals by status</h2>
        <div className="grid grid-cols-7 gap-2">
          {Object.entries(data.totals_by_status).map(([k, v]) => (
            <div key={k} className="rounded bg-ash p-3 border border-zinc-800">
              <div className="text-xs text-zinc-500 capitalize">{k}</div>
              <div className="text-xl">{v}</div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-sm uppercase text-zinc-400 mb-2">Apps per week</h2>
        <div className="flex items-end gap-2 h-40 border border-zinc-800 rounded p-3 bg-ash">
          {data.apps_per_week.map((p) => (
            <div key={p.week} className="flex-1 flex flex-col items-center">
              <div
                className="w-full bg-blue-600/70 rounded-sm"
                style={{ height: `${Math.min(100, p.count * 10)}%` }}
                title={`${p.week}: ${p.count}`}
              />
              <div className="text-[10px] text-zinc-500 mt-1">
                {new Date(p.week).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-sm uppercase text-zinc-400 mb-2">Auto vs manual</h2>
        <table className="text-sm">
          <thead>
            <tr className="text-zinc-400">
              <th></th>
              <th className="px-3 py-1">Applied</th>
              <th className="px-3 py-1">Interview</th>
              <th className="px-3 py-1">Offer</th>
              <th className="px-3 py-1">Rejected</th>
              <th className="px-3 py-1">Ghosted</th>
            </tr>
          </thead>
          <tbody>
            {(["auto", "manual"] as const).map((m) => (
              <tr key={m} className="border-t border-zinc-800">
                <td className="px-3 py-1 capitalize">{m}</td>
                {["applied", "interview", "offer", "rejected", "ghosted"].map((k) => (
                  <td key={k} className="px-3 py-1 text-center">
                    {data.auto_vs_manual_success[m]?.[k] ?? 0}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-zinc-800 p-4 bg-ash">
      <div className="text-xs uppercase text-zinc-500">{label}</div>
      <div className="text-2xl mt-1">{value}</div>
    </div>
  );
}
