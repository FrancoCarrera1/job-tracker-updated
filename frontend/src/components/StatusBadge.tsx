import type { ApplicationStatus } from "../lib/api";

const COLORS: Record<ApplicationStatus, string> = {
  queued: "bg-zinc-700 text-zinc-200",
  applied: "bg-blue-900/60 text-blue-200",
  screening: "bg-indigo-900/60 text-indigo-200",
  interview: "bg-amber-900/60 text-amber-200",
  offer: "bg-emerald-900/60 text-emerald-200",
  rejected: "bg-red-900/50 text-red-200",
  ghosted: "bg-zinc-800 text-zinc-400",
};

export default function StatusBadge({ status }: { status: ApplicationStatus }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${COLORS[status]}`}>
      {status}
    </span>
  );
}
