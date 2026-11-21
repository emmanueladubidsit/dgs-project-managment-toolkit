// British English labels and en-GB date formatting.
import type { MilestoneStatus, Priority, ProjectStatus, TaskStatus, WorkLogKind } from "./types";

export const TASK_STATUSES: TaskStatus[] = ["todo", "in_progress", "blocked", "in_review", "completed", "cancelled"];
export const PRIORITIES: Priority[] = ["critical", "high", "medium", "low"];

export const STATUS_LABEL: Record<TaskStatus, string> = {
  todo: "To Do",
  in_progress: "In Progress",
  blocked: "Blocked",
  in_review: "In Review",
  completed: "Completed",
  cancelled: "Cancelled",
};
export const PRIORITY_LABEL: Record<Priority, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};
export const PROJECT_STATUS_LABEL: Record<ProjectStatus, string> = {
  active: "Active",
  on_hold: "On hold",
  completed: "Completed",
  archived: "Archived",
};
export const MILESTONE_STATUS_LABEL: Record<MilestoneStatus, string> = {
  planned: "Planned",
  in_progress: "In progress",
  achieved: "Achieved",
  missed: "Missed",
  cancelled: "Cancelled",
};
export const WORKLOG_KIND_LABEL: Record<WorkLogKind, string> = {
  progress: "Progress update",
  decision: "Decision",
  blocker: "Blocker",
  research: "Research",
  unplanned: "Unplanned work",
  note: "Note",
};

/** Parse "YYYY-MM-DD" as a local date (not UTC) to avoid off-by-one days. */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function toISODate(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export const todayISO = () => toISODate(new Date());

export function addDays(iso: string, days: number): string {
  const d = parseDate(iso);
  d.setDate(d.getDate() + days);
  return toISODate(d);
}

export function formatDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = {}): string {
  if (!iso) return "—";
  return parseDate(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", ...opts });
}

export const formatShort = (iso: string | null | undefined) =>
  iso ? parseDate(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "—";

export const formatLong = (iso: string) =>
  parseDate(iso).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

export function relativeDue(iso: string | null): string | null {
  if (!iso) return null;
  const diff = Math.round((parseDate(iso).getTime() - parseDate(todayISO()).getTime()) / 86400000);
  if (diff === 0) return "Due today";
  if (diff === 1) return "Due tomorrow";
  if (diff === -1) return "1 day overdue";
  if (diff < 0) return `${-diff} days overdue`;
  return `Due in ${diff} days`;
}

export const hours = (h: string | number | null | undefined) =>
  h === null || h === undefined ? "—" : `${Number(h).toLocaleString("en-GB")}h`;
