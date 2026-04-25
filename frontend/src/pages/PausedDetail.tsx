import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, apiUrl, PausedSession } from "../lib/api";

export default function PausedDetail() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [p, setP] = useState<PausedSession | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!id) return;
    api.get<PausedSession>(`/api/automation/paused/${id}`).then((s) => {
      setP(s);
      const initial: Record<string, string> = {};
      for (const q of s.pending_questions) {
        if (q.llm_answer) initial[q.question] = q.llm_answer;
      }
      setAnswers(initial);
    });
  }, [id]);

  if (!p) return <div className="text-zinc-500">loading…</div>;

  const screenshotUrl = apiUrl(p.screenshot_url);
  const isCaptcha = p.reason === "captcha";
  const primaryLabel = p.pending_questions.length > 0 ? "save answers and resume" : "retry application";
  const secondaryLabel = isCaptcha ? "skip for now" : "dismiss without retrying";

  async function resolve(proceed: boolean) {
    setSubmitting(true);
    await api.post(`/api/automation/paused/${id}/resolve`, { answers, proceed });
    setSubmitting(false);
    nav("/paused");
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <header>
        <div className="text-xs uppercase text-amber-300">{p.reason}</div>
        <h1 className="text-2xl font-semibold">
          {p.role_title || "Paused application"}
          {p.company ? <span className="text-zinc-400"> @ {p.company}</span> : null}
        </h1>
        <div className="text-xs text-zinc-500 mt-1">
          ATS: {p.ats} · {new Date(p.created_at).toLocaleString()}
        </div>
        <p className="text-zinc-300 mt-4 max-w-3xl">{p.message}</p>
        {p.job_url && (
          <div className="mt-4">
            <a
              href={p.job_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center rounded bg-zinc-800 px-3 py-2 text-sm hover:bg-zinc-700"
            >
              open posting
            </a>
          </div>
        )}
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="space-y-4">
          {screenshotUrl ? (
            <div className="rounded border border-zinc-800 bg-ash p-3">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm uppercase text-zinc-400">Captured page</h2>
                <a
                  href={screenshotUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-blue-300 hover:underline"
                >
                  open image
                </a>
              </div>
              <img
                src={screenshotUrl}
                alt="Paused application screenshot"
                className="w-full rounded border border-zinc-900 bg-zinc-950"
              />
            </div>
          ) : p.screenshot_path ? (
            <div className="rounded border border-zinc-800 bg-ash p-4">
              <h2 className="text-sm uppercase text-zinc-400 mb-2">Captured page</h2>
              <div className="text-xs text-zinc-500 break-all">{p.screenshot_path}</div>
            </div>
          ) : null}

          {isCaptcha && (
            <div className="rounded border border-amber-800/40 bg-amber-950/20 p-4 text-sm text-amber-100">
              This dashboard page cannot solve the live CAPTCHA for you. Review the screenshot,
              open the posting if you need more context, then retry the application when you are ready.
            </div>
          )}
        </section>

        {p.pending_questions.length > 0 && (
          <section>
            <h2 className="text-sm uppercase text-zinc-400 mb-3">Questions</h2>
            <div className="space-y-3">
              {p.pending_questions.map((q, idx) => (
                <div key={idx} className="rounded border border-zinc-800 bg-ash p-4">
                  <div className="text-sm mb-2">{q.question}</div>
                  {q.llm_answer && (
                    <div className="text-xs text-zinc-400 mb-2">
                      LLM suggested:{" "}
                      <span className="text-amber-300">{q.llm_answer}</span>
                      {q.llm_confidence != null && (
                        <span className="text-zinc-500">
                          {" "}({(q.llm_confidence * 100).toFixed(0)}% confidence)
                        </span>
                      )}
                      {q.llm_rationale && (
                        <div className="text-zinc-500 mt-1">why: {q.llm_rationale}</div>
                      )}
                    </div>
                  )}
                  {q.field_type === "select" || q.field_type === "radio" ? (
                    <select
                      value={answers[q.question] || ""}
                      onChange={(e) => setAnswers({ ...answers, [q.question]: e.target.value })}
                      className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-sm"
                    >
                      <option value="">— select —</option>
                      {q.options.map((o) => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ) : q.field_type === "textarea" ? (
                    <textarea
                      rows={4}
                      value={answers[q.question] || ""}
                      onChange={(e) => setAnswers({ ...answers, [q.question]: e.target.value })}
                      className="w-full bg-zinc-900 border border-zinc-700 rounded p-2 text-sm"
                    />
                  ) : (
                    <input
                      value={answers[q.question] || ""}
                      onChange={(e) => setAnswers({ ...answers, [q.question]: e.target.value })}
                      className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-sm"
                    />
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      <div className="flex gap-3">
        <button
          disabled={submitting}
          onClick={() => resolve(true)}
          className="px-4 py-2 rounded bg-emerald-700 hover:bg-emerald-600 text-sm"
        >
          {primaryLabel}
        </button>
        <button
          disabled={submitting}
          onClick={() => resolve(false)}
          className="px-4 py-2 rounded bg-zinc-800 hover:bg-zinc-700 text-sm"
        >
          {secondaryLabel}
        </button>
      </div>
    </div>
  );
}
