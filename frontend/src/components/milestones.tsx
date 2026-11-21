"use client";
import { AlertTriangle, Pencil, Plus, Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { formatDate, MILESTONE_STATUS_LABEL } from "@/lib/format";
import {
  useCreateMilestone, useCreateWorkstream, useDeleteMilestone, useDeleteWorkstream, useUpdateMilestone,
  useUpdateWorkstream, useWorkstreams,
} from "@/lib/queries";
import type { Milestone, MilestoneStatus, Workstream } from "@/lib/types";
import { cn } from "@/lib/utils";
import { EmptyState, ExplainedProgress } from "./common";
import { ConfirmDialog } from "./confirm-dialog";
import { orNull, SelectField, TextAreaField, TextField } from "./form-fields";
import { SUGGESTED_WORKSTREAMS } from "./project-form-dialog";
import { TaskFormDialog } from "./task-form-dialog";

const MS_STATUS_CLASS: Record<MilestoneStatus, string> = {
  planned: "bg-muted text-muted-foreground",
  in_progress: "bg-primary/10 text-primary",
  achieved: "bg-success/15 text-success",
  missed: "bg-destructive/10 text-destructive",
  cancelled: "bg-muted text-muted-foreground line-through",
};

export function MilestoneStatusBadge({ status }: { status: MilestoneStatus }) {
  return <span className={cn("rounded px-1.5 py-0.5 text-xs font-medium", MS_STATUS_CLASS[status])}>{MILESTONE_STATUS_LABEL[status]}</span>;
}

export function MilestoneFormDialog({ projectId, milestone, trigger }: { projectId: string; milestone?: Milestone; trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  const fresh = () => ({
    title: milestone?.title ?? "",
    description: milestone?.description ?? "",
    deliverables: milestone?.deliverables ?? "",
    due_date: milestone?.due_date ?? "",
    status: milestone?.status ?? ("planned" as MilestoneStatus),
    workstream_id: milestone?.workstream_id ?? null as string | null,
  });
  const [form, setForm] = useState(fresh);
  const workstreams = useWorkstreams(projectId);
  const create = useCreateMilestone(projectId);
  const update = useUpdateMilestone();
  const set = (k: string, v: string | null) => setForm((f) => ({ ...f, [k]: v }));
  function submit(e: React.FormEvent) {
    e.preventDefault();
    const body = { title: form.title.trim(), description: orNull(form.description), deliverables: orNull(form.deliverables),
      due_date: orNull(form.due_date), status: form.status, workstream_id: form.workstream_id };
    if (milestone) update.mutate({ id: milestone.id, ...body }, { onSuccess: () => setOpen(false) });
    else create.mutate(body, { onSuccess: () => setOpen(false) });
  }
  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) setForm(fresh()); setOpen(o); }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{milestone ? "Edit milestone" : "New milestone"}</DialogTitle>
          <DialogDescription>A milestone is never marked achieved automatically — you decide when it is met.</DialogDescription>
        </DialogHeader>
        <form id="milestone-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <TextField label="Title" required value={form.title} onChange={(v) => set("title", v)} className="sm:col-span-2" autoFocus />
          <TextField label="Due date" type="date" value={form.due_date} onChange={(v) => set("due_date", v)} />
          <SelectField label="Status" value={form.status} onChange={(v) => set("status", v ?? "planned")}
            options={Object.entries(MILESTONE_STATUS_LABEL).map(([value, label]) => ({ value, label }))} />
          <SelectField label="Workstream" value={form.workstream_id} onChange={(v) => set("workstream_id", v)} noneLabel="Across workstreams"
            options={(workstreams.data ?? []).map((w) => ({ value: w.id, label: w.name }))} className="sm:col-span-2" />
          <TextAreaField label="Deliverables" value={form.deliverables} onChange={(v) => set("deliverables", v)} className="sm:col-span-2"
            hint="What will exist when this milestone is met?" />
          <TextAreaField label="Description" value={form.description} onChange={(v) => set("description", v)} className="sm:col-span-2" />
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button type="submit" form="milestone-form" disabled={!form.title.trim() || create.isPending || update.isPending}>Save milestone</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function MilestoneList({ milestones, projectId, showProject }: { milestones: Milestone[]; projectId?: string; showProject?: boolean }) {
  const del = useDeleteMilestone();
  const [addTaskFor, setAddTaskFor] = useState<Milestone | null>(null);
  if (milestones.length === 0) {
    return <EmptyState title="No milestones yet" description="Milestones mark meaningful points of delivery. Link tasks to them to track progress."
      action={projectId && <MilestoneFormDialog projectId={projectId} trigger={<Button><Plus /> Add milestone</Button>} />} />;
  }
  return (
    <>
      <ul className="space-y-3">
        {milestones.map((m) => (
          <li key={m.id} className="rounded-xl border bg-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold">{m.title}</h3>
                  <MilestoneStatusBadge status={m.status} />
                </div>
                <p className="text-xs text-muted-foreground">
                  {showProject && <>{m.project_name} · </>}Due {formatDate(m.due_date)}
                  {m.achieved_at && <> · Achieved {formatDate(m.achieved_at.slice(0, 10))}</>}
                </p>
              </div>
              <div className="flex gap-1">
                <Button size="sm" variant="ghost" onClick={() => setAddTaskFor(m)}><Plus /> Task</Button>
                <MilestoneFormDialog projectId={m.project_id} milestone={m} trigger={<Button size="icon-sm" variant="ghost" aria-label={`Edit ${m.title}`}><Pencil /></Button>} />
                <ConfirmDialog trigger={<Button size="icon-sm" variant="ghost" aria-label={`Delete ${m.title}`}><Trash2 /></Button>}
                  title="Delete this milestone?" description="Linked tasks are kept but will no longer be associated with a milestone."
                  onConfirm={() => del.mutate(m.id)} />
              </div>
            </div>
            <div className="mt-3 max-w-md"><ExplainedProgress progress={m.progress} /></div>
            {m.deliverables && <p className="mt-2 text-sm"><span className="font-medium">Deliverables: </span>{m.deliverables}</p>}
            {m.warnings.length > 0 && (
              <ul className="mt-2 space-y-0.5">
                {m.warnings.map((w) => (
                  <li key={w} className="flex items-center gap-1.5 text-xs text-warning"><AlertTriangle className="size-3.5" aria-hidden />{w}</li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
      {addTaskFor && (
        <TaskFormDialog open onOpenChange={(o) => !o && setAddTaskFor(null)}
          defaults={{ project_id: addTaskFor.project_id, milestone_id: addTaskFor.id, workstream_id: addTaskFor.workstream_id, due_date: addTaskFor.due_date }} />
      )}
    </>
  );
}

export function WorkstreamManager({ projectId }: { projectId: string }) {
  const q = useWorkstreams(projectId);
  const create = useCreateWorkstream(projectId);
  const update = useUpdateWorkstream();
  const del = useDeleteWorkstream();
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const existing = new Set((q.data ?? []).map((w: Workstream) => w.name));
  const suggestions = SUGGESTED_WORKSTREAMS.filter((s) => !existing.has(s));
  return (
    <div className="space-y-4">
      <ul className="divide-y rounded-xl border">
        {(q.data ?? []).length === 0 && <li className="px-4 py-3 text-sm text-muted-foreground">No workstreams. Add only the ones this project needs.</li>}
        {(q.data ?? []).map((w) => (
          <li key={w.id} className="flex items-center gap-2 px-4 py-2">
            {editing === w.id ? (
              <form className="flex flex-1 gap-2" onSubmit={(e) => { e.preventDefault(); update.mutate({ id: w.id, name: draft.trim() }, { onSuccess: () => setEditing(null) }); }}>
                <Input value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Workstream name" autoFocus />
                <Button size="sm" type="submit" disabled={!draft.trim()}>Save</Button>
                <Button size="sm" variant="ghost" type="button" onClick={() => setEditing(null)}>Cancel</Button>
              </form>
            ) : (
              <>
                <span className="flex-1 text-sm">{w.name}</span>
                <Button size="icon-sm" variant="ghost" aria-label={`Rename ${w.name}`} onClick={() => { setEditing(w.id); setDraft(w.name); }}><Pencil /></Button>
                <ConfirmDialog trigger={<Button size="icon-sm" variant="ghost" aria-label={`Remove ${w.name}`}><Trash2 /></Button>}
                  title={`Remove “${w.name}”?`} description="Tasks and milestones in this workstream are kept; they simply become unassigned." confirmLabel="Remove"
                  onConfirm={() => del.mutate(w.id)} />
              </>
            )}
          </li>
        ))}
      </ul>
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); create.mutate({ name: name.trim() }, { onSuccess: () => setName("") }); }}>
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="New workstream name" aria-label="New workstream name" />
        <Button type="submit" disabled={!name.trim()}><Plus /> Add</Button>
      </form>
      {suggestions.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs text-muted-foreground">Suggestions</p>
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((s) => (
              <Button key={s} size="xs" variant="outline" onClick={() => create.mutate({ name: s })}><Plus /> {s}</Button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

