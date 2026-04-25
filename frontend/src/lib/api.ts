const BASE = import.meta.env.VITE_API_BASE || "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${text}`);
  }
  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => req<T>(path),
  post: <T>(path: string, body?: unknown) =>
    req<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    req<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    req<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => req<T>(path, { method: "DELETE" }),
};

export type ApplicationStatus =
  | "queued"
  | "applied"
  | "screening"
  | "interview"
  | "offer"
  | "rejected"
  | "ghosted";

export interface Application {
  id: string;
  company: string;
  role_title: string;
  location?: string;
  location_type?: string;
  salary_min?: number;
  salary_max?: number;
  source?: string;
  job_url?: string;
  contact_person?: string;
  notes?: string;
  status: ApplicationStatus;
  method: "auto" | "manual";
  date_applied?: string;
  last_response_at?: string;
  created_at: string;
  updated_at: string;
  tags?: { tag: { name: string; color?: string } }[];
}

export interface PausedSession {
  id: string;
  job_posting_id: string;
  application_id?: string;
  ats: string;
  reason: string;
  message: string;
  pending_questions: Array<{
    question: string;
    field_type: string;
    options: string[];
    llm_answer?: string;
    llm_confidence?: number;
    llm_rationale?: string;
  }>;
  screenshot_path?: string;
  resolved: boolean;
  created_at: string;
}

export interface Posting {
  id: string;
  source: string;
  source_id?: string;
  ats?: string;
  company: string;
  role_title: string;
  location?: string;
  location_type?: string;
  salary_min?: number;
  salary_max?: number;
  job_url: string;
  score?: number;
  score_breakdown: Record<string, unknown>;
  status: string;
  discovered_at: string;
  requires_clearance: boolean;
  clearance_level?: string;
}

export interface Analytics {
  totals_by_status: Record<string, number>;
  response_rate: number;
  interview_conversion: number;
  median_time_to_response_days: number | null;
  apps_per_week: { week: string; count: number }[];
  auto_vs_manual_success: Record<string, Record<string, number>>;
}
