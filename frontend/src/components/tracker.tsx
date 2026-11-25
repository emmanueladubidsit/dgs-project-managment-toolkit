"use client";
// Project tracker review (ADR 0010): refresh the tracker, then review what it proposes, grouped
// by working day, milestone and plan week. Nothing changes until you approve (ADR 0002).
import { AlertTriangle, Check, ChevronDown, ChevronUp, Clock, FileText, RefreshCw, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { formatDate, formatDateTime, MILESTONE_STATUS_LABEL, STATUS_LABEL, TASK_STATUSES } from "@/lib/format";
import { useMilestones, useWorkstreams } from "@/lib/queries";
import { useApproveBatch, useConnection, useRefreshTracker, useSuggestionAction, useSuggestions } from "@/lib/queries-library";
import type { ApproveEdits, MilestoneStatus, Suggestion, TaskStatus } from "@/lib/types";
import { EmptyState, LoadingState, Section, StatusBadge } from "./common";
import { SelectField, TextAreaField, TextField } from "./form-fields";
import { useOpenTask } from "./task-sheet";

const MILESTONE_STATUSES: MilestoneStatus[] = ["planned", "in_progress", "achieved", "missed", "cancelled"];
const PENDING_MS = "pending:";
type Edits = Record<string, ApproveEdits>;
type Group = { key: string; title: string; note?: string; items: Suggestion[] };

const dayLabel = (iso: string) => formatDate(iso, { weekday: "short", day: "numeric", month: "short", year: "numeric" });

/** Split tracker suggestions into review sections. */
export function groupTracker(items: Suggestion[]) {
  const milestones = items.filter((s) => s.kind === "milestone");
  const byKind = (k: string) => items.filter((s) => s.kind !== "milestone" && (s.payload.tracker_kind ?? "done") === k);
  const days = new Map<string, Group>();
  for (const s of [...byKind("day"), ...byKind("done")]) {
    const d = s.payload.item_date ?? "undated";
    const g = days.get(d) ?? { key: `day-${d}`, title: d === "undated" ? "Undated" : dayLabel(d), items: [] };
    if (s.payload.carried_from) g.note = `Includes weekend work from ${s.payload.carried_from}, counted on Monday.`;
    g.items.push(s);
    days.set(d, g);
  }
  const byMilestone = (list: Suggestion[], prefix: string) => {
    const m = new Map<string, Group>();
    for (const s of list) {
      const k = s.payload.milestone_key ?? s.payload.section ?? "other";
      const g = m.get(k) ?? { key: `${prefix}-${k}`, title: s.payload.milestone_title ?? s.payload.section ?? "Other", items: [] };
      g.items.push(s);
      m.set(k, g);
    }
    return [...m.values()];
  };
  const sortDays = [...days.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([, g]) => {
    // The day's work-log entry first, then the individual pieces of work.
    g.items.sort((a, b) => Number(b.kind === "progress") - Number(a.kind === "progress"));
    return g;
  });
  const plan = byMilestone(byKind("plan"), "plan");
  for (const g of plan) g.items.sort((a, b) => (a.payload.item_date ?? "").localeCompare(b.payload.item_date ?? ""));
  return { milestones, days: sortDays, status: byMilestone(byKind("status"), "status"), plan };
}

function approveBody(s: Suggestion, e: ApproveEdits | undefined): { id: string } & ApproveEdits {
  const body: { id: string } & ApproveEdits = { id: s.id, ...(e ?? {}) };
  if (typeof body.milestone_id === "string" && body.milestone_id.startsWith(PENDING_MS)) delete body.milestone_id;
  return body;
}

/** The Tracker tab: file status, Refresh, and the review list. */
export function TrackerPanel({ projectId }: { projectId: string }) {
  const conn = useConnection(projectId);
  const refresh = useRefreshTracker(projectId);
  const q = useSuggestions({ status: "pending", project_id: projectId });
  const batch = useApproveBatch();
  const [edits, setEdits] = useState<Edits>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const items = useMemo(() => (q.data ?? []).filter((s) => s.generator === "tracker"), [q.data]);
  const groups = useMemo(() => groupTracker(items), [items]);
  const c = conn.data;

  const approveMany = (list: Suggestion[], extra: ApproveEdits = {}) =>
    batch.mutate(list.map((s) => approveBody(s, { ...edits[s.id], ...extra })), {
      onSuccess: (r) => setErrors(Object.fromEntries(r.results.filter((x) => !x.ok).map((x) => [x.id, x.error ?? "Could not approve."]))),
    });
  const setEdit = (id: string, patch: ApproveEdits) => setEdits((all) => ({ ...all, [id]: { ...all[id], ...patch } }));

  if (conn.isPending) return <LoadingState rows={4} />;
  if (!c) {
    return (
      <EmptyState
        icon={<FileText className="size-6" />}
        title="Connect the project's folder first"
        description="Open the Codebase tab and connect the folder (read only). The tracker is read from docs/project-management/PROGRESS-AND-PLAN-YYYY-MM-DD.md inside it."
      />
    );
  }
  const shared = { projectId, edits, errors, setEdit, approveOne: (s: Suggestion, extra?: ApproveEdits) => approveMany([s], extra) };
  return (
    <div className="space-y-4">
      <Section
        title="Project tracker"
        actions={<Button size="sm" onClick={() => refresh.mutate()} disabled={refresh.isPending}><RefreshCw className={refresh.isPending ? "animate-spin" : undefined} /> {refresh.isPending ? "Reading…" : "Refresh tracker"}</Button>}
      >
        <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
          <dt className="text-muted-foreground">File</dt>
          <dd className="font-mono text-xs break-all">{c.tracker_file ?? "None found yet"}</dd>
          <dt className="text-muted-foreground">Last read</dt>
          <dd>{c.tracker_read_at ? formatDateTime(c.tracker_read_at) : "Never"}</dd>
          <dt className="text-muted-foreground">Working days</dt>
          <dd>Monday to Friday. Weekend work is counted on the following Monday.</dd>
        </dl>
        {c.tracker_warnings.length > 0 && (
          <ul className="mt-3 space-y-1 text-sm text-warning">
            {c.tracker_warnings.map((w) => <li key={w} className="flex items-start gap-1.5"><AlertTriangle className="mt-0.5 size-3.5 shrink-0" />{w}</li>)}
          </ul>
        )}
      </Section>

      {q.isPending ? <LoadingState rows={6} /> : items.length === 0 ? (
        <EmptyState title="Nothing to review" description="Everything in the tracker is already reflected here, or was reviewed. Press Refresh tracker after Claude Code updates it." />
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border bg-card p-4">
            <p className="text-sm"><strong>{items.length}</strong> item(s) from the tracker are waiting for review. Edit any item before approving; nothing changes until you approve.</p>
            <Button onClick={() => approveMany(items)} disabled={batch.isPending}><Check /> Approve all {items.length}</Button>
          </div>
          {groups.milestones.length > 0 && (
            <ReviewGroup group={{ key: "ms", title: "Milestones", items: groups.milestones }} onApproveAll={approveMany} busy={batch.isPending} {...shared} />
          )}
          {groups.days.length > 0 && <h2 className="pt-2 text-base font-semibold">Work done, by working day</h2>}
          {groups.days.map((g) => <ReviewGroup key={g.key} group={g} onApproveAll={approveMany} busy={batch.isPending} {...shared} />)}
          {groups.status.length > 0 && <h2 className="pt-2 text-base font-semibold">Milestone criteria</h2>}
          {groups.status.map((g) => <ReviewGroup key={g.key} group={g} onApproveAll={approveMany} busy={batch.isPending} {...shared} />)}
          {groups.plan.length > 0 && <h2 className="pt-2 text-base font-semibold">Plan (to do)</h2>}
          {groups.plan.map((g) => <ReviewGroup key={g.key} group={g} onApproveAll={approveMany} busy={batch.isPending} {...shared} />)}
        </>
      )}
    </div>
  );
}

type Shared = {
  projectId: string; edits: Edits; errors: Record<string, string>;
  setEdit: (id: string, patch: ApproveEdits) => void; approveOne: (s: Suggestion, extra?: ApproveEdits) => void;
};

function ReviewGroup({ group, onApproveAll, busy, ...shared }: { group: Group; onApproveAll: (l: Suggestion[]) => void; busy: boolean } & Shared) {
  return (
    <section className="rounded-xl border bg-card p-4" aria-label={group.title}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">{group.title} <span className="font-normal text-muted-foreground">({group.items.length})</span></h3>
          {group.note && <p className="text-xs text-muted-foreground">{group.note}</p>}
        </div>
        {group.items.length > 1 && <Button size="sm" variant="outline" onClick={() => onApproveAll(group.items)} disabled={busy}><Check /> Approve {group.items.length}</Button>}
      </div>
      <ul className="space-y-2">{group.items.map((s) => <ReviewRow key={s.id} s={s} {...shared} />)}</ul>
    </section>
  );
}

function ReviewRow({ s, projectId, edits, errors, setEdit, approveOne }: { s: Suggestion } & Shared) {
  const act = useSuggestionAction();
  const openTask = useOpenTask();
  const [open, setOpen] = useState(false);
  const e = edits[s.id] ?? {};
  const p = s.payload;
  const title = e.title ?? p.title ?? "";
  const isTask = s.kind === "task" || s.kind === "task_update";
  const status = (e.status ?? p.status ?? "todo") as string;
  const kindLabel = s.kind === "milestone" ? (p.milestone_id ? "Update milestone" : "New milestone")
    : s.kind === "task_update" ? "Existing task" : s.kind === "progress" ? "Work log" : "New task";

  return (
    <li className="rounded-lg border p-3">
      <div className="flex flex-wrap items-start gap-2">
        <span className="rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">{kindLabel}</span>
        <div className="min-w-0 flex-1 text-sm">
          {s.kind === "progress" ? (
            <p><strong>{p.title}</strong>: {e.description ?? s.evidence}</p>
          ) : s.kind === "task_update" ? (
            <p>
              <button className="font-medium underline-offset-2 hover:underline" onClick={() => p.task_id && openTask(p.task_id)}>“{e.title ?? p.title}”</button>
              {p.current_status && <> · now {STATUS_LABEL[p.current_status]}</>}
              {p.tracker_title && p.tracker_title !== p.title && <span className="block text-xs text-muted-foreground">Tracker: “{p.tracker_title}”</span>}
            </p>
          ) : <p className="font-medium">{title}</p>}
          <p className="mt-0.5 text-xs text-muted-foreground">
            {p.original_date && <>Done {dayLabel(p.original_date)}, counted on {dayLabel(p.item_date ?? p.original_date)} · </>}
            {s.kind === "milestone" && (e.due_date ?? p.due_date) && <>Due {dayLabel((e.due_date ?? p.due_date)!)} · </>}
            {p.tracker_kind === "plan" && (e.scheduled_date ?? p.scheduled_date) && <>Planned for {dayLabel((e.scheduled_date ?? p.scheduled_date)!)}{p.current_scheduled_date && <> (currently {dayLabel(p.current_scheduled_date)})</>} · </>}
            {isTask && p.milestone_title && !p.task_has_milestone && <>Milestone: {p.milestone_title} · </>}
            {p.tracker_file && <span className="font-mono text-[0.7rem]">{p.tracker_file.split("/").pop()}</span>}
          </p>
        </div>
        {isTask && <StatusBadge status={status as TaskStatus} />}
        {s.kind === "milestone" && <span className="rounded-full border px-2 py-0.5 text-xs">{MILESTONE_STATUS_LABEL[status as MilestoneStatus] ?? status}</span>}
      </div>
      {s.kind === "task" && s.duplicate_of_task_id && (
        <p className="mt-2 flex items-start gap-1.5 text-xs text-warning"><AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
          <span>Possibly the same as the existing task <button className="underline" onClick={() => openTask(s.duplicate_of_task_id!)}>“{s.duplicate_of_title}”</button>. Reject this one if so.</span></p>
      )}
      {open && <RowEditor s={s} projectId={projectId} e={e} onChange={(patch) => setEdit(s.id, patch)} />}
      {errors[s.id] && <p className="mt-2 flex items-start gap-1.5 text-xs text-destructive"><AlertTriangle className="mt-0.5 size-3.5 shrink-0" />{errors[s.id]}</p>}
      <div className="mt-2 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => approveOne(s)}><Check /> Approve</Button>
        {errors[s.id] && s.kind === "task" && <Button size="sm" variant="outline" onClick={() => approveOne(s, { allow_duplicate: true })}>Create anyway</Button>}
        <Button size="sm" variant="outline" onClick={() => setOpen((o) => !o)} aria-expanded={open}>{open ? <ChevronUp /> : <ChevronDown />} Edit</Button>
        <Button size="sm" variant="ghost" onClick={() => act.mutate({ id: s.id, action: "reject" })}><X /> Reject</Button>
        <Button size="sm" variant="ghost" onClick={() => act.mutate({ id: s.id, action: "defer" })}><Clock /> Later</Button>
      </div>
    </li>
  );
}

function RowEditor({ s, projectId, e, onChange }: { s: Suggestion; projectId: string; e: ApproveEdits; onChange: (p: ApproveEdits) => void }) {
  const milestones = useMilestones(projectId);
  const workstreams = useWorkstreams(projectId);
  const p = s.payload;
  if (s.kind === "progress") {
    return (
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <TextField label="Date" type="date" value={e.entry_date ?? p.entry_date ?? ""} onChange={(v) => onChange({ entry_date: v })} />
        <TextAreaField label="Summary" value={e.description ?? s.evidence ?? ""} onChange={(v) => onChange({ description: v })} className="sm:col-span-2" rows={4} />
      </div>
    );
  }
  if (s.kind === "milestone") {
    return (
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <TextField label="Title" value={e.title ?? p.title ?? ""} onChange={(v) => onChange({ title: v })} className="sm:col-span-3" />
        <SelectField label="Status" value={e.status ?? (p.status as string) ?? "planned"} onChange={(v) => onChange({ status: v ?? "planned" })}
          options={MILESTONE_STATUSES.map((m) => ({ value: m, label: MILESTONE_STATUS_LABEL[m] }))} />
        <TextField label="Due date" type="date" value={e.due_date ?? p.due_date ?? ""} onChange={(v) => onChange({ due_date: v || null })} />
      </div>
    );
  }
  const pendingMs = !p.milestone_id && p.milestone_key && p.milestone_title
    ? [{ value: `${PENDING_MS}${p.milestone_key}`, label: `${p.milestone_title} (new, from the tracker)` }] : [];
  const msValue = e.milestone_id !== undefined ? e.milestone_id : p.milestone_id ?? (pendingMs[0]?.value ?? null);
  return (
    <div className="mt-3 grid gap-3 sm:grid-cols-3">
      <TextField label="Title" value={e.title ?? p.title ?? ""} onChange={(v) => onChange({ title: v })} className="sm:col-span-3" />
      <SelectField label="Status" value={e.status ?? (p.status as string) ?? "todo"} onChange={(v) => onChange({ status: v ?? "todo" })}
        options={TASK_STATUSES.map((t) => ({ value: t, label: STATUS_LABEL[t] }))} />
      <TextField label="Progress (%)" type="number" min={0} max={100} value={e.progress != null ? String(e.progress) : ""}
        onChange={(v) => onChange({ progress: v === "" ? undefined : Math.max(0, Math.min(100, Number(v))) })} hint="Completed work is always 100%." />
      <SelectField label="Milestone" value={msValue} onChange={(v) => onChange({ milestone_id: v })} noneLabel="None"
        options={[...pendingMs, ...(milestones.data ?? []).map((m) => ({ value: m.id, label: m.title }))]} />
      <SelectField label="Workstream" value={e.workstream_id ?? null} onChange={(v) => onChange({ workstream_id: v })} noneLabel="None"
        options={(workstreams.data ?? []).map((w) => ({ value: w.id, label: w.name }))} />
      <TextField label="Planned for (day)" type="date" value={e.scheduled_date ?? p.scheduled_date ?? ""} onChange={(v) => onChange({ scheduled_date: v || null })} />
      <TextField label="Due date" type="date" value={e.due_date ?? ""} onChange={(v) => onChange({ due_date: v || null })} />
    </div>
  );
}
