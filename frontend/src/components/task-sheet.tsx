"use client";
import { Archive, ArchiveRestore, CalendarDays, Link2, Pencil, Plus, Trash2, X } from "lucide-react";
import { createContext, useContext, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import {
  formatDate, formatDateTime, hours, PRIORITIES, PRIORITY_LABEL, relativeDue, STATUS_LABEL, TASK_STATUSES,
} from "@/lib/format";
import {
  useAddComment, useAddDependency, useArchiveTask, useComments, useDeleteTask, useRemoveDependency,
  useTask, useTaskActivity, useTasks, useUpdateTask,
} from "@/lib/queries";
import type { Activity, Priority, TaskDetail, TaskInput, TaskStatus } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ErrorState, LoadingState, ProgressBar, StatusBadge } from "./common";
import { ConfirmDialog } from "./confirm-dialog";
import { TaskFormDialog } from "./task-form-dialog";

const Ctx = createContext<(id: string) => void>(() => {});
export const useOpenTask = () => useContext(Ctx);

export function TaskSheetProvider({ children }: { children: ReactNode }) {
  const [taskId, setTaskId] = useState<string | null>(null);
  return (
    <Ctx.Provider value={setTaskId}>
      {children}
      <Sheet open={!!taskId} onOpenChange={(o) => !o && setTaskId(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          {taskId && <TaskPanel id={taskId} onNavigate={setTaskId} onClose={() => setTaskId(null)} />}
        </SheetContent>
      </Sheet>
    </Ctx.Provider>
  );
}

function TaskPanel({ id, onNavigate, onClose }: { id: string; onNavigate: (id: string) => void; onClose: () => void }) {
  const q = useTask(id);
  if (q.isPending) return <div className="p-6"><SheetTitle className="sr-only">Loading task</SheetTitle><LoadingState /></div>;
  if (q.error || !q.data) return <div className="p-6"><SheetTitle className="sr-only">Task unavailable</SheetTitle><ErrorState error={q.error} onRetry={() => q.refetch()} /></div>;
  return <TaskBody task={q.data} onNavigate={onNavigate} onClose={onClose} />;
}

function TaskBody({ task, onNavigate, onClose }: { task: TaskDetail; onNavigate: (id: string) => void; onClose: () => void }) {
  const update = useUpdateTask();
  const archive = useArchiveTask();
  const del = useDeleteTask();
  const [editing, setEditing] = useState(false);
  const patch = (body: TaskInput) => update.mutate({ id: task.id, ...body });

  const due = relativeDue(task.due_date);
  return (
    <div className="flex flex-col gap-6 p-6">
      <SheetHeader className="p-0">
        <p className="text-xs text-muted-foreground">
          {task.project_name}
          {task.workstream_name && <> · {task.workstream_name}</>}
          {task.milestone_title && <> · Milestone: {task.milestone_title}</>}
        </p>
        <SheetTitle className={cn("pr-8 text-lg", task.status === "cancelled" && "line-through")}>{task.title}</SheetTitle>
        <SheetDescription className="sr-only">Task details, subtasks, dependencies, comments and history.</SheetDescription>
        {task.archived_at && <p className="rounded-md bg-warning/15 px-2 py-1 text-xs text-warning">This task is archived and hidden from boards and plans.</p>}
      </SheetHeader>

      {/* Quick controls */}
      <div className="grid grid-cols-2 gap-3">
        <label className="space-y-1 text-xs font-medium">
          Status
          <Select value={task.status} onValueChange={(v) => patch({ status: v as TaskStatus })}>
            <SelectTrigger className="w-full" aria-label="Status"><SelectValue /></SelectTrigger>
            <SelectContent>{TASK_STATUSES.map((s) => <SelectItem key={s} value={s}>{STATUS_LABEL[s]}</SelectItem>)}</SelectContent>
          </Select>
        </label>
        <label className="space-y-1 text-xs font-medium">
          Priority
          <Select value={task.priority} onValueChange={(v) => patch({ priority: v as Priority })}>
            <SelectTrigger className="w-full" aria-label="Priority"><SelectValue /></SelectTrigger>
            <SelectContent>{PRIORITIES.map((p) => <SelectItem key={p} value={p}>{PRIORITY_LABEL[p]}</SelectItem>)}</SelectContent>
          </Select>
        </label>
        <label className="space-y-1 text-xs font-medium">
          Progress (%)
          <ProgressInput key={task.progress} value={task.progress} busy={update.isPending}
            onSet={(v) => patch({ progress: v })} />
        </label>
        <label className="space-y-1 text-xs font-medium">
          Planned for
          <Input type="date" value={task.scheduled_date ?? ""} onChange={(e) => patch({ scheduled_date: e.target.value || null })} />
        </label>
      </div>
      <ProgressBar value={task.progress} label="Task progress" />

      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
        <Meta label="Due">{formatDate(task.due_date)}{due && <span className={cn("block text-xs", task.is_overdue ? "text-destructive" : "text-muted-foreground")}>{due}</span>}</Meta>
        <Meta label="Start">{formatDate(task.start_date)}</Meta>
        <Meta label="Estimate / actual">{hours(task.estimate_hours)} / {hours(task.actual_hours)}</Meta>
        <Meta label="Completed">{task.completed_at ? formatDateTime(task.completed_at) : "—"}</Meta>
        <Meta label="Weight">{task.weight ?? "Default"}</Meta>
        <Meta label="Labels">{task.labels.length ? task.labels.join(", ") : "—"}</Meta>
      </dl>

      <TextBlock title="Description" text={task.description} />
      <TextBlock title="Acceptance criteria" text={task.acceptance_criteria} missing="No acceptance criteria yet — define what “done” means." />
      <TextBlock title="Expected deliverables" text={task.deliverables} />

      <Subtasks task={task} onNavigate={onNavigate} />
      <Dependencies task={task} onNavigate={onNavigate} />
      <Comments taskId={task.id} />
      <History taskId={task.id} />

      <div className="flex flex-wrap gap-2 border-t pt-4">
        <Button variant="outline" onClick={() => setEditing(true)}><Pencil /> Edit all fields</Button>
        <Button variant="outline" onClick={() => archive.mutate({ id: task.id, restore: !!task.archived_at })}>
          {task.archived_at ? <><ArchiveRestore /> Restore</> : <><Archive /> Archive</>}
        </Button>
        <ConfirmDialog
          trigger={<Button variant="destructive"><Trash2 /> Delete</Button>}
          title="Delete this task permanently?"
          description={<>This removes the task{task.subtask_count > 0 && <> and its <strong>{task.subtask_count} subtask(s)</strong></>}, its comments and its history. It cannot be undone. Archive it instead if you may need it later.</>}
          onConfirm={() => del.mutate(task.id, { onSuccess: onClose })}
        />
      </div>
      <TaskFormDialog task={task} open={editing} onOpenChange={setEditing} />
    </div>
  );
}

function ProgressInput({ value, busy, onSet }: { value: number; busy: boolean; onSet: (v: number) => void }) {
  const [draft, setDraft] = useState(String(value));
  return (
    <div className="flex gap-2">
      <Input type="number" min={0} max={100} value={draft} onChange={(e) => setDraft(e.target.value)} />
      <Button variant="outline" disabled={Number(draft) === value || busy}
        onClick={() => onSet(Math.max(0, Math.min(100, Math.round(Number(draft) || 0))))}>Set</Button>
    </div>
  );
}

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function TextBlock({ title, text, missing }: { title: string; text: string | null; missing?: string }) {
  if (!text && !missing) return null;
  return (
    <div>
      <h3 className="mb-1 text-sm font-semibold">{title}</h3>
      {text ? <p className="text-sm whitespace-pre-wrap">{text}</p> : <p className="text-sm text-muted-foreground italic">{missing}</p>}
    </div>
  );
}

function Subtasks({ task, onNavigate }: { task: TaskDetail; onNavigate: (id: string) => void }) {
  const [adding, setAdding] = useState(false);
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Subtasks {task.subtask_count > 0 && <span className="font-normal text-muted-foreground">({task.subtasks_completed}/{task.subtask_count} completed)</span>}</h3>
        <Button size="sm" variant="ghost" onClick={() => setAdding(true)}><Plus /> Add subtask</Button>
      </div>
      {task.subtasks.length === 0 ? (
        <p className="text-sm text-muted-foreground">No subtasks.</p>
      ) : (
        <ul className="divide-y rounded-lg border">
          {task.subtasks.map((s) => (
            <li key={s.id}>
              <button className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-muted" onClick={() => onNavigate(s.id)}>
                <span className={cn(s.status === "completed" && "text-muted-foreground line-through")}>{s.title}</span>
                <StatusBadge status={s.status} />
              </button>
            </li>
          ))}
        </ul>
      )}
      {task.subtask_count > 0 && task.status !== "completed" && task.subtasks_completed === task.subtask_count && (
        <p className="mt-2 text-xs text-muted-foreground">All subtasks are completed. The parent is not completed automatically — update its status when you are satisfied.</p>
      )}
      <TaskFormDialog open={adding} onOpenChange={setAdding}
        defaults={{ project_id: task.project_id, parent_id: task.id, workstream_id: task.workstream_id, milestone_id: task.milestone_id }} />
    </div>
  );
}

function Dependencies({ task, onNavigate }: { task: TaskDetail; onNavigate: (id: string) => void }) {
  const add = useAddDependency(task.id);
  const remove = useRemoveDependency(task.id);
  const candidates = useTasks({ project_id: task.project_id, sort: "status" });
  const taken = new Set([task.id, ...task.dependencies.map((d) => d.id)]);
  const options = (candidates.data ?? []).filter((t) => !taken.has(t.id));
  return (
    <div>
      <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold"><Link2 className="size-4" aria-hidden /> Dependencies</h3>
      {task.dependencies.length === 0 ? (
        <p className="mb-2 text-sm text-muted-foreground">This task does not depend on anything.</p>
      ) : (
        <ul className="mb-2 space-y-1">
          {task.dependencies.map((d) => (
            <li key={d.id} className="flex items-center justify-between gap-2 text-sm">
              <button className="truncate text-left underline-offset-2 hover:underline" onClick={() => onNavigate(d.id)}>Waits for: {d.title}</button>
              <span className="flex items-center gap-1">
                <StatusBadge status={d.status} />
                <Button size="icon-xs" variant="ghost" aria-label={`Remove dependency on ${d.title}`} onClick={() => remove.mutate(d.id)}><X /></Button>
              </span>
            </li>
          ))}
        </ul>
      )}
      {task.open_dependencies.length > 0 && (
        <p className="mb-2 text-xs text-status-blocked">Waiting on {task.open_dependencies.length} unfinished task(s).</p>
      )}
      {options.length > 0 && (
        <Select value="" onValueChange={(v) => add.mutate(v)}>
          <SelectTrigger className="w-full" aria-label="Add a dependency"><SelectValue placeholder="Add a task this depends on…" /></SelectTrigger>
          <SelectContent>{options.map((t) => <SelectItem key={t.id} value={t.id}>{t.title}</SelectItem>)}</SelectContent>
        </Select>
      )}
      {task.dependents.length > 0 && (
        <p className="mt-2 text-xs text-muted-foreground">Blocks: {task.dependents.map((d) => d.title).join(", ")}</p>
      )}
    </div>
  );
}

function Comments({ taskId }: { taskId: string }) {
  const comments = useComments(taskId);
  const add = useAddComment(taskId);
  const [body, setBody] = useState("");
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold">Updates and comments</h3>
      <ul className="mb-3 space-y-2">
        {(comments.data ?? []).map((c) => (
          <li key={c.id} className="rounded-lg bg-muted/60 px-3 py-2 text-sm">
            <p className="whitespace-pre-wrap">{c.body}</p>
            <p className="mt-1 text-xs text-muted-foreground">{formatDateTime(c.created_at)}</p>
          </li>
        ))}
      </ul>
      <form onSubmit={(e) => { e.preventDefault(); if (body.trim()) add.mutate(body, { onSuccess: () => setBody("") }); }} className="space-y-2">
        <Textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="Record an update…" aria-label="New comment" rows={2} />
        <Button size="sm" type="submit" disabled={!body.trim() || add.isPending}>Add update</Button>
      </form>
    </div>
  );
}

export function describeActivity(a: Activity): string {
  const label = (field: string, v: unknown) =>
    field === "status" ? STATUS_LABEL[v as TaskStatus] ?? String(v)
      : field === "priority" ? PRIORITY_LABEL[v as Priority] ?? String(v)
        : field === "progress" ? `${v}%`
          : v === null || v === "" ? "empty" : String(v);
  if (a.action === "created") return "Created the task";
  if (a.action === "commented") return "Added an update";
  if (a.action === "archived") return "Archived the task";
  if (a.action === "restored") return "Restored the task";
  if (a.action === "dependency_added") return `Added dependency on “${a.changes.depends_on?.[1]}”`;
  if (a.action === "dependency_removed") return `Removed dependency on “${a.changes.depends_on?.[0]}”`;
  const parts = Object.entries(a.changes).map(([field, [o, n]]) => {
    const name = field.replace(/_id$/, "").replace(/_/g, " ");
    if (["description", "acceptance_criteria", "deliverables", "notes"].includes(field)) return `edited ${name}`;
    if (field.endsWith("_id")) return `changed ${name}`;
    return `${name} ${label(field, o)} → ${label(field, n)}`;
  });
  const text = parts.join("; ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function History({ taskId }: { taskId: string }) {
  const q = useTaskActivity(taskId);
  return (
    <div>
      <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold"><CalendarDays className="size-4" aria-hidden /> History</h3>
      <ol className="space-y-1.5 border-l pl-4">
        {(q.data ?? []).map((a) => (
          <li key={a.id} className="text-sm">
            <span>{describeActivity(a)}</span>
            <span className="ml-2 text-xs text-muted-foreground">{formatDateTime(a.created_at)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

