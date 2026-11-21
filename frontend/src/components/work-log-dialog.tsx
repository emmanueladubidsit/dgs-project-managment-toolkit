"use client";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { todayISO, WORKLOG_KIND_LABEL } from "@/lib/format";
import { useCreateWorkLog, useProjects, useTasks } from "@/lib/queries";
import type { WorkLogKind } from "@/lib/types";
import { numOrNull, SelectField, TextAreaField, TextField } from "./form-fields";

/** Record a daily progress update, decision, blocker, research note or unplanned work. */
export function WorkLogDialog({ trigger, defaults }: { trigger: ReactNode; defaults?: { kind?: WorkLogKind; project_id?: string; entry_date?: string } }) {
  const [open, setOpen] = useState(false);
  const fresh = () => ({
    entry_date: defaults?.entry_date ?? todayISO(),
    kind: defaults?.kind ?? ("progress" as WorkLogKind),
    summary: "",
    hours: "",
    project_id: defaults?.project_id ?? (null as string | null),
    task_id: null as string | null,
  });
  const [form, setForm] = useState(fresh);
  const projects = useProjects();
  const tasks = useTasks({ project_id: form.project_id ?? undefined, sort: "updated" });
  const create = useCreateWorkLog();
  const set = <K extends keyof ReturnType<typeof fresh>>(k: K, v: ReturnType<typeof fresh>[K]) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) setForm(fresh()); setOpen(o); }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add an update</DialogTitle>
          <DialogDescription>Updates feed the daily and weekly reports exactly as written.</DialogDescription>
        </DialogHeader>
        <form id="worklog-form" className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => {
          e.preventDefault();
          create.mutate({ ...form, summary: form.summary.trim(), hours: numOrNull(form.hours) }, { onSuccess: () => setOpen(false) });
        }}>
          <SelectField label="Type" value={form.kind} onChange={(v) => set("kind", (v ?? "progress") as WorkLogKind)}
            options={Object.entries(WORKLOG_KIND_LABEL).map(([value, label]) => ({ value, label }))} />
          <TextField label="Date" type="date" value={form.entry_date} onChange={(v) => set("entry_date", v)} required />
          <TextAreaField label="What happened?" value={form.summary} onChange={(v) => set("summary", v)} rows={4} className="sm:col-span-2" />
          <SelectField label="Project" value={form.project_id} noneLabel="No specific project"
            onChange={(v) => setForm((f) => ({ ...f, project_id: v, task_id: null }))}
            options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
          <SelectField label="Related task" value={form.task_id} noneLabel="None" onChange={(v) => set("task_id", v)}
            options={(form.project_id ? tasks.data ?? [] : []).map((t) => ({ value: t.id, label: t.title }))} disabled={!form.project_id} />
          <TextField label="Hours spent (optional)" type="number" min={0} max={24} step="0.25" value={form.hours} onChange={(v) => set("hours", v)} />
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button type="submit" form="worklog-form" disabled={!form.summary.trim() || create.isPending}>Save update</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
