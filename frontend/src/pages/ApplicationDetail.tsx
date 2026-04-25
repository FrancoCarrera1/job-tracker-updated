import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, Application } from "../lib/api";
import StatusBadge from "../components/StatusBadge";

export default function ApplicationDetail() {
  const { id } = useParams<{ id: string }>();
  const [app, setApp] = useState<Application | null>(null);
  const [audit, setAudit] = useState<any[]>([]);
  const [emails, setEmails] = useState<any[]>([]);

  useEffect(() => {
    if (!id) return;
    api.get<Application>(`/api/applications/${id}`).then(setApp);
    api.get<any[]>(`/api/applications/${id}/audit`).then(setAudit);
    api.get<any[]>(`/api/applications/${id}/emails`).then(setEmails);
  }, [id]);

  if (!app) return <div className="text-zinc-500">loading…</div>;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-zinc-500">{app.company}</div>
          <h1 className="text-2xl font-semibold">{app.role_title}</h1>
          <div className="mt-1 text-sm text-zinc-400">
            {app.location || ""}{app.location_type ? ` · ${app.location_type}` : ""}
            {app.salary_min && app.salary_max
              ? ` · $${(app.salary_min/1000).toFixed(0)}k–$${(app.salary_max/1000).toFixed(0)}k`
              : ""}
          </div>
        </div>
        <StatusBadge status={app.status} />
      </div>

      {app.job_url && (
        <a href={app.job_url} target="_blank" rel="noreferrer"
           className="text-sm text-blue-300 hover:underline">
          {app.job_url}
        </a>
      )}

      {app.notes && (
        <section>
          <h2 className="text-sm uppercase text-zinc-400 mb-2">Notes</h2>
          <p className="text-zinc-200 whitespace-pre-wrap">{app.notes}</p>
        </section>
      )}

      <section>
        <h2 className="text-sm uppercase text-zinc-400 mb-2">Email thread</h2>
        {emails.length === 0 ? (
          <div className="text-zinc-500 text-sm">no emails linked yet</div>
        ) : (
          <ul className="space-y-2">
            {emails.map((e) => (
              <li key={e.id} className="rounded border border-zinc-800 bg-ash p-3">
                <div className="flex justify-between text-xs text-zinc-500">
                  <span>{e.sender}</span>
                  <span>{new Date(e.received_at).toLocaleString()}</span>
                </div>
                <div className="text-sm font-medium">{e.subject}</div>
                <div className="text-xs text-zinc-400 mt-1">{e.snippet}</div>
                <div className="text-xs mt-1">
                  <span className="text-zinc-500">classification: </span>
                  <span className="text-amber-300">{e.classification}</span>
                  <span className="text-zinc-500"> ({(e.classification_confidence*100).toFixed(0)}%)</span>
                  {" · "}
                  <a
                    href={`https://mail.google.com/mail/u/0/#all/${e.gmail_thread_id}`}
                    className="text-blue-300 hover:underline"
                    target="_blank"
                    rel="noreferrer"
                  >
                    open in Gmail
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-sm uppercase text-zinc-400 mb-2">Audit log</h2>
        <ul className="space-y-1 text-sm">
          {audit.map((a) => (
            <li key={a.id} className="flex justify-between gap-3 py-1 border-b border-zinc-900">
              <span className="text-zinc-300">{a.action}</span>
              <span className="text-zinc-500 text-xs">{new Date(a.created_at).toLocaleString()}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
