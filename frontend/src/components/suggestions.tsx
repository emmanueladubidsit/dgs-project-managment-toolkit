"use client";
import { AlertTriangle, Check, Clock, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PRIORITIES, PRIORITY_LABEL, STATUS_LABEL, todayISO } from "@/lib/format";
import { useProjects } from "@/lib/queries";
import { useSuggestionAction, useSuggestions } from "@/lib/queries-library";
import type { Suggestion } from "@/lib/types";
import { SelectField } from "./form-fields";
import { useOpenTask } from "./task-sheet";

const KIND_LABEL = { task: "Task", task_update: "Task update", blocker: "Blocker", decision: "Decision", progress: "Progress" };
const SOURCE_LABEL = (g: string) => (g === "claude" ? "from Claude Code" : g === "git" ? "from a commit" : g.startsWith("ai:") ? "suggested by AI" : null);

/** Review one suggestion: edit, then approve (creates the task/update), reject or defer. */
export function SuggestionCard({ s, noteProjectId, hideProject }: { s: Suggestion; noteProjectId: string | null; hideProject?: boolean }) {
  const act = useSuggestionAction();
  const projects = useProjects();
  const openTask = useOpenTask();
  const [title, setTitle] = useState(s.payload.title ?? "");
  const [priority, setPriority] = useState(s.payload.priority ?? "medium");
  const [project, setProject] = useState<string | null>(s.project_id ?? noteProjectId);
  const approve = (allow = false) => act.mutate({ id: s.id, action: "approve", body: { title, priority, project_id: project, allow_duplicate: allow, entry_date: todayISO() } });
  return (
    <li className="rounded-lg border p-3">
      <div className="mb-2 flex items-center gap-2 text-xs">
        <span className="rounded bg-primary/10 px-1.5 py-0.5 font-medium text-primary">{KIND_LABEL[s.kind]}</span>
        {SOURCE_LABEL(s.generator) && <span className="text-muted-foreground">{SOURCE_LABEL(s.generator)}</span>}
        {s.payload.estimate_hours ? <span className="text-muted-foreground">· est. {s.payload.estimate_hours}h</span> : null}
        {s.status === "deferred" && <span className="flex items-center gap-1 text-muted-foreground"><Clock className="size-3" /> Deferred</span>}
      </div>
      {s.kind === "task_update" ? (
        <p className="text-sm">Mark <button className="font-medium underline-offset-2 hover:underline" onClick={() => s.payload.task_id && openTask(s.payload.task_id)}>“{s.payload.title}”</button> as <strong>{STATUS_LABEL[s.payload.status ?? "completed"]}</strong></p>
      ) : s.kind === "task" ? (
        <div className="space-y-2">
          <Input value={title} onChange={(e) => setTitle(e.target.value)} aria-label="Task title" />
          <div className="grid grid-cols-2 gap-2">
            <Select value={priority} onValueChange={(v) => setPriority(v as never)}>
              <SelectTrigger aria-label="Priority"><SelectValue /></SelectTrigger>
              <SelectContent>{PRIORITIES.map((p) => <SelectItem key={p} value={p}>{PRIORITY_LABEL[p]}</SelectItem>)}</SelectContent>
            </Select>
            {!hideProject && <SelectField label="Project" value={project} onChange={setProject} noneLabel="Choose a project" options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />}
          </div>
        </div>
      ) : <p className="text-sm">{s.evidence}</p>}
      {s.kind === "task" && s.payload.acceptance_criteria && <p className="mt-2 text-xs"><span className="text-muted-foreground">Done when: </span>{s.payload.acceptance_criteria}</p>}
      {(s.kind === "task" || s.kind === "task_update") && s.evidence && <p className="mt-2 text-xs text-muted-foreground">{s.kind === "task_update" ? "Evidence: " : "From: "}“{s.evidence}”</p>}
      {s.duplicate_of_task_id && (
        <p className="mt-2 flex items-start gap-1.5 text-xs text-warning"><AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
          Possible duplicate of <button className="underline" onClick={() => openTask(s.duplicate_of_task_id!)}>“{s.duplicate_of_title}”</button>.</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {s.duplicate_of_task_id && s.kind === "task"
          ? <Button size="sm" variant="outline" onClick={() => approve(true)} disabled={!title.trim() || !project}><Check /> Create anyway</Button>
          : <Button size="sm" onClick={() => approve()} disabled={s.kind === "task" && (!title.trim() || !project)}><Check /> {s.kind === "task" ? "Create task" : s.kind === "task_update" ? "Apply" : "Record update"}</Button>}
        <Button size="sm" variant="ghost" onClick={() => act.mutate({ id: s.id, action: "reject" })}><X /> Reject</Button>
        {s.status !== "deferred" && <Button size="sm" variant="ghost" onClick={() => act.mutate({ id: s.id, action: "defer" })}><Clock /> Later</Button>}
      </div>
    </li>
  );
}

/** Pending suggestions for a project, with “Approve all” for task updates. */
export function PendingReview({ projectId, title = "Waiting for your review", sources }: { projectId?: string; title?: string; sources?: string[] }) {
  const q = useSuggestions({ status: "pending", project_id: projectId });
  const act = useSuggestionAction();
  const items = (q.data ?? []).filter((s) => !sources || sources.includes(s.generator));
  const updates = items.filter((s) => s.kind === "task_update");
  if (!items.length) return null;
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">{title} ({items.length})</h2>
        {updates.length > 1 && <Button size="sm" variant="outline" onClick={async () => { for (const u of updates) await act.mutateAsync({ id: u.id, action: "approve" }); }}>Apply all {updates.length} task updates</Button>}
      </div>
      <ul className="space-y-3">{items.slice(0, 20).map((s) => <SuggestionCard key={s.id} s={s} noteProjectId={s.project_id} hideProject={!!projectId} />)}</ul>
    </div>
  );
}
