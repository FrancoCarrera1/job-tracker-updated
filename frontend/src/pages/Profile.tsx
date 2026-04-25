import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface ProfileData {
  full_name: string;
  email: string;
  phone?: string;
  location?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  salary_min?: number;
  salary_max?: number;
  work_authorization?: string;
  requires_sponsorship: boolean;
  willing_to_relocate: boolean;
  security_clearance?: string;
  summary?: string;
  standard_answers: Record<string, string>;
  eeo_answers: Record<string, string>;
  skills: Record<string, number>;
  certifications: { name: string; issued?: string; expires?: string }[];
  work_history: any[];
  education: any[];
  references: any[];
  cover_letter_templates: Record<string, string>;
}

const EMPTY: ProfileData = {
  full_name: "",
  email: "",
  requires_sponsorship: false,
  willing_to_relocate: false,
  standard_answers: {},
  eeo_answers: {},
  skills: {},
  certifications: [],
  work_history: [],
  education: [],
  references: [],
  cover_letter_templates: { default: "" },
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<ProfileData>(EMPTY);
  const [resumes, setResumes] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    api.get<ProfileData | null>("/api/profile").then((p) => {
      if (p) setProfile({ ...EMPTY, ...p });
    });
    api.get<any[]>("/api/profile/resumes").then(setResumes);
  }, []);

  async function save() {
    setSaving(true);
    await api.put("/api/profile", profile);
    setSaving(false);
    setSavedAt(new Date().toLocaleTimeString());
  }

  async function uploadResume(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const r = await fetch("/api/profile/resumes", { method: "POST", body: fd });
    if (!r.ok) {
      alert(await r.text());
      return;
    }
    setResumes(await api.get<any[]>("/api/profile/resumes"));
    (e.currentTarget as HTMLFormElement).reset();
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Master profile</h1>
        <div className="flex items-center gap-3">
          {savedAt && <span className="text-xs text-zinc-500">saved {savedAt}</span>}
          <button
            onClick={save}
            disabled={saving}
            className="px-4 py-1.5 rounded bg-emerald-700 hover:bg-emerald-600 text-sm"
          >
            {saving ? "saving…" : "Save profile"}
          </button>
        </div>
      </div>

      <Section title="Identity">
        <Field label="Full name" value={profile.full_name}
               onChange={(v) => setProfile({ ...profile, full_name: v })} />
        <Field label="Email" value={profile.email}
               onChange={(v) => setProfile({ ...profile, email: v })} />
        <Field label="Phone" value={profile.phone || ""}
               onChange={(v) => setProfile({ ...profile, phone: v })} />
        <Field label="Location" value={profile.location || ""}
               onChange={(v) => setProfile({ ...profile, location: v })} />
        <Field label="LinkedIn" value={profile.linkedin_url || ""}
               onChange={(v) => setProfile({ ...profile, linkedin_url: v })} />
        <Field label="GitHub" value={profile.github_url || ""}
               onChange={(v) => setProfile({ ...profile, github_url: v })} />
      </Section>

      <Section title="Work prefs">
        <Field label="Salary min" type="number" value={String(profile.salary_min ?? "")}
               onChange={(v) => setProfile({ ...profile, salary_min: v ? Number(v) : undefined })} />
        <Field label="Salary max" type="number" value={String(profile.salary_max ?? "")}
               onChange={(v) => setProfile({ ...profile, salary_max: v ? Number(v) : undefined })} />
        <Field label="Work authorization" value={profile.work_authorization || ""}
               onChange={(v) => setProfile({ ...profile, work_authorization: v })} />
        <Field label="Security clearance" value={profile.security_clearance || ""}
               onChange={(v) => setProfile({ ...profile, security_clearance: v })} />
        <Toggle label="Requires sponsorship" value={profile.requires_sponsorship}
                onChange={(v) => setProfile({ ...profile, requires_sponsorship: v })} />
        <Toggle label="Willing to relocate" value={profile.willing_to_relocate}
                onChange={(v) => setProfile({ ...profile, willing_to_relocate: v })} />
      </Section>

      <Section title="Summary">
        <textarea
          rows={4}
          value={profile.summary || ""}
          onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
          className="col-span-2 w-full bg-ash border border-zinc-800 rounded p-2 text-sm"
        />
      </Section>

      <Section title="Resumes">
        <div className="col-span-2">
          <ul className="space-y-1 text-sm mb-3">
            {resumes.map((r) => (
              <li key={r.id} className="flex items-center justify-between p-2 rounded bg-ash">
                <span>
                  {r.name}
                  <span className="text-zinc-500 ml-2 text-xs">
                    [{r.tags.join(", ")}]
                  </span>
                  {r.is_default && <span className="ml-2 text-emerald-400 text-xs">default</span>}
                </span>
                <button
                  onClick={async () => {
                    await api.del(`/api/profile/resumes/${r.id}`);
                    setResumes(await api.get<any[]>("/api/profile/resumes"));
                  }}
                  className="text-xs text-red-300 hover:text-red-200"
                >
                  delete
                </button>
              </li>
            ))}
          </ul>
          <form onSubmit={uploadResume} className="flex gap-2 items-end">
            <input name="name" placeholder="variant name (e.g. DevOps)"
                   className="bg-ash border border-zinc-800 rounded px-2 py-1 text-sm" required />
            <input name="tags" placeholder="tags (comma sep)"
                   className="bg-ash border border-zinc-800 rounded px-2 py-1 text-sm" />
            <label className="text-xs flex items-center gap-1">
              <input type="checkbox" name="is_default" /> default
            </label>
            <input type="file" name="file" accept="application/pdf"
                   className="text-xs" required />
            <button className="px-3 py-1 bg-blue-700 hover:bg-blue-600 rounded text-sm">
              upload
            </button>
          </form>
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-sm uppercase tracking-wide text-zinc-400 mb-3">{title}</h2>
      <div className="grid grid-cols-2 gap-3">{children}</div>
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <label className="text-sm">
      <span className="block text-xs text-zinc-400 mb-1">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-ash border border-zinc-800 rounded px-2 py-1.5"
      />
    </label>
  );
}

function Toggle({
  label,
  value,
  onChange,
}: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="text-sm flex items-center gap-2">
      <input type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}
