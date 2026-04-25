import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, PausedSession } from "../lib/api";

export default function Paused() {
  const [items, setItems] = useState<PausedSession[]>([]);
  useEffect(() => {
    api.get<PausedSession[]>("/api/automation/paused").then(setItems);
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <h1 className="text-2xl font-semibold">Paused — needs your input</h1>
      {items.length === 0 ? (
        <p className="text-zinc-500">Nothing paused. Automation is moving freely.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((p) => (
            <li key={p.id} className="rounded border border-amber-800/40 bg-amber-950/30 p-4">
              <div className="flex justify-between">
                <div>
                  <div className="text-xs uppercase text-amber-300">{p.reason}</div>
                  <div className="text-sm mt-1 font-medium">
                    {p.role_title || "Paused application"}
                    {p.company ? ` @ ${p.company}` : ""}
                  </div>
                  <div className="text-sm mt-1 text-zinc-300">{p.message}</div>
                  <div className="text-xs text-zinc-500 mt-1">
                    ATS: {p.ats} · {new Date(p.created_at).toLocaleString()}
                  </div>
                </div>
                <Link to={`/paused/${p.id}`}
                      className="self-start px-3 py-1 rounded bg-amber-700 hover:bg-amber-600 text-sm">
                  resolve →
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
