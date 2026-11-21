"use client";
// Kanban board, task list and shared filters. All views render the same task records.
import { AlertCircle, ChevronDown, GitBranch, Link2, MoreHorizontal, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatShort, PRIORITIES, PRIORITY_LABEL, relativeDue, STATUS_LABEL, TASK_STATUSES, todayISO } from "@/lib/format";
import { useBulkUpdate, useUpdateTask, type TaskFilters } from "@/lib/queries";
import type { Priority, Task, TaskStatus } from "@/lib/types";
import { cn } from "@/lib/utils";
import { EmptyState, PriorityBadge, ProgressBar, STATUS_DOT, StatusBadge } from "./common";
import { useOpenTask } from "./task-sheet";

// ------------------------------------------------------------------ filters
const SORTS = [
  { value: "position", label: "Manual order" },
  { value: "priority", label: "Priority" },
  { value: "due_date", label: "Deadline" },
  { value: "status", label: "Status" },
  { value: "project", label: "Project" },
  { value: "updated", label: "Recently updated" },
];

export function TaskFilterBar({ filters, onChange, extra }: { filters: TaskFilters; onChange: (f: TaskFilters) => void; extra?: React.ReactNode }) {
  const toggle = (key: "status" | "priority", value: string) => {
    const current = new Set(filters[key] ?? []);
    if (current.has(value)) current.delete(value);
    else current.add(value);
    onChange({ ...filters, [key]: [...current] });
  };
  const active = (filters.status?.length ?? 0) + (filters.priority?.length ?? 0) + (filters.overdue ? 1 : 0) + (filters.blocked ? 1 : 0) + (filters.q ? 1 : 0);
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <div className="relative w-full sm:w-64">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input className="pl-8" placeholder="Search tasks…" aria-label="Search tasks" value={filters.q ?? ""} onChange={(e) => onChange({ ...filters, q: e.target.value })} />
      </div>
      {extra}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline">Status{filters.status?.length ? ` (${filters.status.length})` : ""} <ChevronDown /></Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          {TASK_STATUSES.map((s) => (
            <DropdownMenuCheckboxItem key={s} checked={filters.status?.includes(s)} onCheckedChange={() => toggle("status", s)} onSelect={(e) => e.preventDefault()}>
              {STATUS_LABEL[s]}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline">Priority{filters.priority?.length ? ` (${filters.priority.length})` : ""} <ChevronDown /></Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          {PRIORITIES.map((p) => (
            <DropdownMenuCheckboxItem key={p} checked={filters.priority?.includes(p)} onCheckedChange={() => toggle("priority", p)} onSelect={(e) => e.preventDefault()}>
              {PRIORITY_LABEL[p]}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
      <Button variant={filters.overdue ? "default" : "outline"} aria-pressed={!!filters.overdue} onClick={() => onChange({ ...filters, overdue: !filters.overdue })}>Overdue</Button>
      <Button variant={filters.blocked ? "default" : "outline"} aria-pressed={!!filters.blocked} onClick={() => onChange({ ...filters, blocked: !filters.blocked })}>Blocked</Button>
      <Select value={filters.sort ?? "position"} onValueChange={(v) => onChange({ ...filters, sort: v })}>
        <SelectTrigger className="w-44" aria-label="Sort by"><SelectValue /></SelectTrigger>
        <SelectContent>{SORTS.map((s) => <SelectItem key={s.value} value={s.value}>Sort: {s.label}</SelectItem>)}</SelectContent>
      </Select>
      {active > 0 && (
        <Button variant="ghost" onClick={() => onChange({ project_id: filters.project_id, sort: filters.sort })}>Clear filters</Button>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ shared bits
function TaskMeta({ task, showProject }: { task: Task; showProject?: boolean }) {
  const due = relativeDue(task.due_date);
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
      {showProject && <span className="truncate">{task.project_name}</span>}
      {task.workstream_name && <span className="truncate">{task.workstream_name}</span>}
      {task.due_date && task.status !== "completed" && task.status !== "cancelled" && (
        <span className={cn(task.is_overdue && "font-medium text-destructive")}>{due}</span>
      )}
      {task.subtask_count > 0 && (
        <span className="inline-flex items-center gap-0.5"><GitBranch className="size-3" aria-hidden />{task.subtasks_completed}/{task.subtask_count}</span>
      )}
      {task.open_dependencies.length > 0 && (
        <span className="inline-flex items-center gap-0.5 text-status-blocked" title={`Waiting on: ${task.open_dependencies.map((d) => d.title).join(", ")}`}>
          <Link2 className="size-3" aria-hidden />waiting on {task.open_dependencies.length}
        </span>
      )}
    </div>
  );
}

function MoveMenu({ task }: { task: Task }) {
  const update = useUpdateTask();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button size="icon-xs" variant="ghost" aria-label={`Actions for ${task.title}`} onClick={(e) => e.stopPropagation()}><MoreHorizontal /></Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent onClick={(e) => e.stopPropagation()}>
        <DropdownMenuLabel>Move to</DropdownMenuLabel>
        {TASK_STATUSES.filter((s) => s !== task.status).map((s) => (
          <DropdownMenuItem key={s} onSelect={() => update.mutate({ id: task.id, status: s })}>{STATUS_LABEL[s]}</DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => update.mutate({ id: task.id, scheduled_date: todayISO() })}>Plan for today</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// ------------------------------------------------------------------ Kanban
export function KanbanBoard({ tasks, showProject, showCancelled = false }: { tasks: Task[]; showProject?: boolean; showCancelled?: boolean }) {
  const update = useUpdateTask();
  const openTask = useOpenTask();
  const [dragId, setDragId] = useState<string | null>(null);
  const [over, setOver] = useState<TaskStatus | null>(null);
  const columns = TASK_STATUSES.filter((s) => showCancelled || s !== "cancelled");
  const byStatus = useMemo(() => {
    const m = new Map<TaskStatus, Task[]>(columns.map((c) => [c, []]));
    [...tasks].sort((a, b) => a.position - b.position).forEach((t) => m.get(t.status)?.push(t));
    return m;
  }, [tasks, columns]);

  function drop(status: TaskStatus, beforeId: string | null) {
    const id = dragId;
    setDragId(null);
    setOver(null);
    if (!id) return;
    const col = (byStatus.get(status) ?? []).filter((t) => t.id !== id);
    const idx = beforeId ? col.findIndex((t) => t.id === beforeId) : col.length;
    const prev = col[idx - 1]?.position;
    const next = col[idx]?.position;
    const position = prev === undefined && next === undefined ? 1000
      : prev === undefined ? next! - 1000
        : next === undefined ? prev + 1000
          : (prev + next) / 2;
    const task = tasks.find((t) => t.id === id);
    if (task && (task.status !== status || task.position !== position)) {
      update.mutate({ id, status, position });
    }
  }

  return (
    <div className="flex gap-3 overflow-x-auto pb-2" role="list" aria-label="Kanban board">
      {columns.map((status) => {
        const items = byStatus.get(status) ?? [];
        return (
          <div
            key={status}
            role="listitem"
            aria-label={`${STATUS_LABEL[status]} column, ${items.length} task(s)`}
            className={cn("flex w-72 shrink-0 flex-col rounded-xl border bg-muted/40 transition-colors", over === status && "border-primary bg-primary/5")}
            onDragOver={(e) => { e.preventDefault(); setOver(status); }}
            onDragLeave={() => setOver((o) => (o === status ? null : o))}
            onDrop={(e) => { e.preventDefault(); drop(status, null); }}
          >
            <div className="flex items-center gap-2 px-3 py-2.5">
              <span className={cn("size-2 rounded-full", STATUS_DOT[status])} aria-hidden />
              <h3 className="text-sm font-semibold">{STATUS_LABEL[status]}</h3>
              <span className="ml-auto text-xs text-muted-foreground tabular-nums">{items.length}</span>
            </div>
            <ul className="flex min-h-24 flex-col gap-2 px-2 pb-2">
              {items.map((t) => (
                <li
                  key={t.id}
                  draggable
                  onDragStart={(e) => { setDragId(t.id); e.dataTransfer.effectAllowed = "move"; }}
                  onDragEnd={() => { setDragId(null); setOver(null); }}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => { e.preventDefault(); e.stopPropagation(); drop(status, t.id); }}
                  className={cn("group rounded-lg border bg-card p-3 shadow-xs transition hover:border-primary/40", dragId === t.id && "opacity-40")}
                >
                  <div className="flex items-start gap-2">
                    <button className="min-w-0 flex-1 text-left text-sm font-medium leading-snug hover:underline" onClick={() => openTask(t.id)}>
                      {t.title}
                    </button>
                    <MoveMenu task={t} />
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <PriorityBadge priority={t.priority} showLabel={false} />
                    {t.progress > 0 && t.status !== "completed" && (
                      <span className="flex w-20 items-center gap-1.5"><ProgressBar value={t.progress} label={`${t.title} progress`} /><span className="text-[10px] tabular-nums text-muted-foreground">{t.progress}%</span></span>
                    )}
                  </div>
                  <div className="mt-1.5"><TaskMeta task={t} showProject={showProject} /></div>
                </li>
              ))}
              {items.length === 0 && <li className="rounded-lg border border-dashed px-3 py-4 text-center text-xs text-muted-foreground">Drop tasks here</li>}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

// ------------------------------------------------------------------ list
export function TaskTable({ tasks, showProject, emptyText = "No tasks match these filters." }: { tasks: Task[]; showProject?: boolean; emptyText?: string }) {
  const openTask = useOpenTask();
  const bulk = useBulkUpdate();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const visibleSelected = tasks.filter((t) => selected.has(t.id)).map((t) => t.id);
  const all = tasks.length > 0 && visibleSelected.length === tasks.length;

  if (tasks.length === 0) return <EmptyState title={emptyText} />;
  const apply = (changes: Parameters<typeof bulk.mutate>[0]["changes"]) =>
    bulk.mutate({ task_ids: visibleSelected, changes }, { onSuccess: () => setSelected(new Set()) });

  return (
    <div>
      {visibleSelected.length > 0 && (
        <div className="mb-2 flex flex-wrap items-center gap-2 rounded-lg border bg-muted/50 px-3 py-2 text-sm" role="region" aria-label="Bulk actions">
          <span className="font-medium">{visibleSelected.length} selected</span>
          <Select value="" onValueChange={(v) => apply({ status: v as TaskStatus })}>
            <SelectTrigger className="h-7 w-36" aria-label="Set status"><SelectValue placeholder="Set status…" /></SelectTrigger>
            <SelectContent>{TASK_STATUSES.map((s) => <SelectItem key={s} value={s}>{STATUS_LABEL[s]}</SelectItem>)}</SelectContent>
          </Select>
          <Select value="" onValueChange={(v) => apply({ priority: v as Priority })}>
            <SelectTrigger className="h-7 w-36" aria-label="Set priority"><SelectValue placeholder="Set priority…" /></SelectTrigger>
            <SelectContent>{PRIORITIES.map((p) => <SelectItem key={p} value={p}>{PRIORITY_LABEL[p]}</SelectItem>)}</SelectContent>
          </Select>
          <Button size="sm" variant="outline" onClick={() => apply({ scheduled_date: todayISO() })}>Plan for today</Button>
          <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>Clear selection</Button>
        </div>
      )}
      <div className="overflow-x-auto rounded-xl border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8">
                <Checkbox checked={all} aria-label="Select all tasks"
                  onCheckedChange={(c) => setSelected(c ? new Set(tasks.map((t) => t.id)) : new Set())} />
              </TableHead>
              <TableHead>Task</TableHead>
              {showProject && <TableHead>Project</TableHead>}
              <TableHead>Status</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Due</TableHead>
              <TableHead>Planned</TableHead>
              <TableHead className="w-32">Progress</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((t) => (
              <TableRow key={t.id} data-state={selected.has(t.id) ? "selected" : undefined}>
                <TableCell>
                  <Checkbox checked={selected.has(t.id)} aria-label={`Select ${t.title}`}
                    onCheckedChange={(c) => setSelected((s) => { const n = new Set(s); if (c) n.add(t.id); else n.delete(t.id); return n; })} />
                </TableCell>
                <TableCell className="max-w-md">
                  <button className="block max-w-full truncate text-left font-medium hover:underline" onClick={() => openTask(t.id)}>
                    {t.parent_id && <span className="text-muted-foreground">↳ </span>}{t.title}
                  </button>
                  <TaskMeta task={t} />
                </TableCell>
                {showProject && <TableCell className="text-sm">{t.project_name}</TableCell>}
                <TableCell><StatusBadge status={t.status} /></TableCell>
                <TableCell><PriorityBadge priority={t.priority} /></TableCell>
                <TableCell className={cn("text-sm whitespace-nowrap", t.is_overdue && "font-medium text-destructive")}>
                  {t.is_overdue && <AlertCircle className="mr-1 inline size-3.5" aria-label="Overdue" />}
                  {formatShort(t.due_date)}
                </TableCell>
                <TableCell className="text-sm whitespace-nowrap">{formatShort(t.scheduled_date)}</TableCell>
                <TableCell>
                  <span className="flex items-center gap-2"><ProgressBar value={t.progress} label={`${t.title} progress`} /><span className="w-8 text-xs tabular-nums text-muted-foreground">{t.progress}%</span></span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

/** Compact clickable task row for dashboards and planners. */
export function TaskRow({ task, showProject = true, action }: { task: Task; showProject?: boolean; action?: React.ReactNode }) {
  const openTask = useOpenTask();
  return (
    <li className="flex items-center gap-3 py-2">
      <span className={cn("size-2 shrink-0 rounded-full", STATUS_DOT[task.status])} title={STATUS_LABEL[task.status]} aria-hidden />
      <div className="min-w-0 flex-1">
        <button className={cn("block max-w-full truncate text-left text-sm font-medium hover:underline", task.status === "completed" && "text-muted-foreground line-through")} onClick={() => openTask(task.id)}>
          {task.title}
        </button>
        <TaskMeta task={task} showProject={showProject} />
      </div>
      <PriorityBadge priority={task.priority} showLabel={false} />
      {action}
    </li>
  );
}
