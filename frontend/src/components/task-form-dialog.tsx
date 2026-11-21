"use client";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { PRIORITIES, PRIORITY_LABEL, STATUS_LABEL, TASK_STATUSES } from "@/lib/format";
import { useCreateTask, useMilestones, useProjects, useUpdateTask, useWorkstreams } from "@/lib/queries";
import type { Priority, Task, TaskStatus } from "@/lib/types";
import { numOrNull, orNull, SelectField, TextAreaField, TextField } from "./form-fields";

type Defaults = Partial<Pick<Task, "project_id" | "workstream_id" | "milestone_id" | "parent_id" | "status" | "scheduled_date" | "due_date">>;

function initial(task?: Task, defaults: Defaults = {}) {
  return {
    title: task?.title ?? "",
    project_id: task?.project_id ?? defaults.project_id ?? null,
    workstream_id: task?.workstream_id ?? defaults.workstream_id ?? null,
    milestone_id: task?.milestone_id ?? defaults.milestone_id ?? null,
    status: (task?.status ?? defaults.status ?? "todo") as TaskStatus,
    priority: (task?.priority ?? "medium") as Priority,
    start_date: task?.start_date ?? "",
    due_date: task?.due_date ?? defaults.due_date ?? "",
    scheduled_date: task?.scheduled_date ?? defaults.scheduled_date ?? "",
    estimate_hours: task?.estimate_hours != null ? String(Number(task.estimate_hours)) : "",
    actual_hours: task?.actual_hours != null ? String(Number(task.actual_hours)) : "",
    progress: String(task?.progress ?? 0),
    weight: task?.weight != null ? String(task.weight) : "",
    description: task?.description ?? "",
    acceptance_criteria: task?.acceptance_criteria ?? "",
    deliverables: task?.deliverables ?? "",
    labels: (task?.labels ?? []).join(", "),
  };
}

/** Create or edit a task. Pass `task` to edit; `defaults` to pre-fill a new task. */
export function TaskFormDialog({ task, defaults, trigger, open, onOpenChange, onCreated }: {
  task?: Task; defaults?: Defaults; trigger?: ReactNode;
  open?: boolean; onOpenChange?: (o: boolean) => void; onCreated?: (t: Task) => void;
}) {
  const [innerOpen, setInnerOpen] = useState(false);
  const isOpen = open ?? innerOpen;
  const setOpen = onOpenChange ?? setInnerOpen;
  return (
    <Dialog open={isOpen} onOpenChange={setOpen}>
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        {/* Mounted only while open, so every opening starts from fresh values. */}
        {isOpen && <TaskForm task={task} defaults={defaults} close={() => setOpen(false)} onCreated={onCreated} />}
      </DialogContent>
    </Dialog>
  );
}

function TaskForm({ task, defaults, close, onCreated }: { task?: Task; defaults?: Defaults; close: () => void; onCreated?: (t: Task) => void }) {
  const [form, setForm] = useState(() => initial(task, defaults));
  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) => setForm((f) => ({ ...f, [k]: v }));

  const projects = useProjects();
  const workstreams = useWorkstreams(form.project_id ?? undefined);
  const milestones = useMilestones(form.project_id ?? undefined);
  const create = useCreateTask();
  const update = useUpdateTask({ success: "Task saved." });
  const pending = create.isPending || update.isPending;
  const projectFixed = !!task || !!defaults?.parent_id;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.project_id) return;
    const body = {
      title: form.title.trim(),
      workstream_id: form.workstream_id,
      milestone_id: form.milestone_id,
      status: form.status,
      priority: form.priority,
      start_date: orNull(form.start_date),
      due_date: orNull(form.due_date),
      scheduled_date: orNull(form.scheduled_date),
      estimate_hours: numOrNull(form.estimate_hours),
      actual_hours: numOrNull(form.actual_hours),
      progress: Number(form.progress) || 0,
      weight: numOrNull(form.weight),
      description: orNull(form.description),
      acceptance_criteria: orNull(form.acceptance_criteria),
      deliverables: orNull(form.deliverables),
      labels: form.labels.split(",").map((l) => l.trim()).filter(Boolean),
    };
    if (task) {
      update.mutate({ id: task.id, ...body }, { onSuccess: close });
    } else {
      create.mutate(
        { ...body, project_id: form.project_id, parent_id: defaults?.parent_id ?? null },
        { onSuccess: (t) => { close(); onCreated?.(t); } },
      );
    }
  }

  const projectOptions = (projects.data ?? []).map((p) => ({ value: p.id, label: p.name }));
  return (
    <>
        <DialogHeader>
          <DialogTitle>{task ? "Edit task" : defaults?.parent_id ? "New subtask" : "New task"}</DialogTitle>
          <DialogDescription>Only the title and project are required. Status and progress are recorded separately.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" id="task-form">
          <TextField label="Title" required value={form.title} onChange={(v) => set("title", v)} className="sm:col-span-2" autoFocus />
          {projectOptions.length === 0 && !projects.isPending ? (
            <p className="text-sm text-destructive sm:col-span-2">Create a project first — every task belongs to a project.</p>
          ) : (
            <SelectField label="Project (required)" value={form.project_id} disabled={projectFixed}
              onChange={(v) => setForm((f) => ({ ...f, project_id: v, workstream_id: null, milestone_id: null }))}
              options={projectOptions} noneLabel={form.project_id ? undefined : "Choose a project"} className="sm:col-span-2" />
          )}
          <SelectField label="Workstream" value={form.workstream_id} onChange={(v) => set("workstream_id", v)} noneLabel="None"
            options={(workstreams.data ?? []).map((w) => ({ value: w.id, label: w.name }))} disabled={!form.project_id} />
          <SelectField label="Milestone" value={form.milestone_id} onChange={(v) => set("milestone_id", v)} noneLabel="None"
            options={(milestones.data ?? []).map((m) => ({ value: m.id, label: m.title }))} disabled={!form.project_id} />
          <SelectField label="Status" value={form.status} onChange={(v) => set("status", (v ?? "todo") as TaskStatus)}
            options={TASK_STATUSES.map((s) => ({ value: s, label: STATUS_LABEL[s] }))} />
          <SelectField label="Priority" value={form.priority} onChange={(v) => set("priority", (v ?? "medium") as Priority)}
            options={PRIORITIES.map((p) => ({ value: p, label: PRIORITY_LABEL[p] }))} />
          <TextField label="Start date" type="date" value={form.start_date} onChange={(v) => set("start_date", v)} />
          <TextField label="Due date" type="date" value={form.due_date} onChange={(v) => set("due_date", v)} />
          <TextField label="Planned for (day)" type="date" value={form.scheduled_date} onChange={(v) => set("scheduled_date", v)} hint="Shows the task in the daily and weekly planner." />
          <TextField label="Progress (%)" type="number" min={0} max={100} value={form.progress} onChange={(v) => set("progress", v)} />
          <TextField label="Estimated effort (hours)" type="number" min={0} step="0.25" value={form.estimate_hours} onChange={(v) => set("estimate_hours", v)} />
          <TextField label="Actual effort (hours)" type="number" min={0} step="0.25" value={form.actual_hours} onChange={(v) => set("actual_hours", v)} />
          <TextField label="Weight (1–100, optional)" type="number" min={1} max={100} value={form.weight} onChange={(v) => set("weight", v)}
            hint="Overrides the estimate when calculating weighted progress." />
          <TextField label="Labels" value={form.labels} onChange={(v) => set("labels", v)} placeholder="api, research" hint="Separate with commas." />
          <TextAreaField label="Description" value={form.description} onChange={(v) => set("description", v)} className="sm:col-span-2" />
          <TextAreaField label="Acceptance criteria" value={form.acceptance_criteria} onChange={(v) => set("acceptance_criteria", v)} className="sm:col-span-2"
            placeholder="This task is done when…" />
          <TextAreaField label="Expected deliverables" value={form.deliverables} onChange={(v) => set("deliverables", v)} className="sm:col-span-2" rows={2} />
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={close}>Cancel</Button>
          <Button type="submit" form="task-form" disabled={pending || !form.title.trim() || !form.project_id}>
            {pending ? "Saving…" : task ? "Save task" : "Create task"}
          </Button>
        </DialogFooter>
    </>
  );
}
