"use client";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { PRIORITIES, PRIORITY_LABEL } from "@/lib/format";
import { useCreateProject, useStages, useUpdateProject } from "@/lib/queries";
import type { Priority, Project, ProjectFields } from "@/lib/types";
import { orNull, SelectField, TextAreaField, TextField } from "./form-fields";

export const SUGGESTED_WORKSTREAMS = [
  "Product and requirements", "Research and discovery", "UX/UI and design system", "Frontend development",
  "Backend/API development", "Database and data architecture", "AI and agent implementation", "AI evaluation",
  "Software testing and quality assurance", "Security, privacy and governance", "Integrations",
  "Infrastructure and deployment", "Documentation", "Stakeholder engagement", "Maintenance and operations",
];

const TEXT_FIELDS: { key: keyof ProjectFields; label: string; hint?: string }[] = [
  { key: "description", label: "Description" },
  { key: "problem_statement", label: "Problem statement" },
  { key: "objectives", label: "Objectives", hint: "One per line works well." },
  { key: "target_users", label: "Target users" },
  { key: "business_context", label: "Business context" },
  { key: "scope", label: "In scope" },
  { key: "out_of_scope", label: "Out of scope" },
  { key: "expected_outcomes", label: "Expected outcomes" },
  { key: "stakeholders", label: "Stakeholders and contacts" },
  { key: "dependencies", label: "Dependencies" },
  { key: "risks_assumptions", label: "Risks and assumptions" },
  { key: "tech_stack", label: "Technology stack" },
  { key: "notes", label: "Notes" },
];

type FormState = Record<string, string> & { priority: Priority; stage_id: string | null };

function initial(p?: Project): FormState {
  const base: Record<string, string> = {};
  for (const f of TEXT_FIELDS) base[f.key] = (p?.[f.key] as string | null) ?? "";
  return {
    ...base,
    name: p?.name ?? "",
    start_date: p?.start_date ?? "",
    target_date: p?.target_date ?? "",
    repository_url: p?.repository_url ?? "",
    docs_location: p?.docs_location ?? "",
    priority: (p?.priority ?? "medium") as Priority,
    stage_id: p?.stage_id ?? null,
  } as FormState;
}

export function ProjectFormDialog({ project, trigger }: { project?: Project; trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(() => initial(project));
  const [streams, setStreams] = useState<Set<string>>(new Set(SUGGESTED_WORKSTREAMS.slice(0, 4)));
  const [more, setMore] = useState(false);
  const stages = useStages();
  const create = useCreateProject();
  const update = useUpdateProject(project?.id ?? "");
  const router = useRouter();
  const set = (k: string, v: string | null) => setForm((f) => ({ ...f, [k]: v }) as FormState);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const body: Record<string, unknown> = {
      name: form.name.trim(),
      priority: form.priority,
      stage_id: form.stage_id,
      start_date: orNull(form.start_date),
      target_date: orNull(form.target_date),
      repository_url: orNull(form.repository_url),
      docs_location: orNull(form.docs_location),
    };
    for (const f of TEXT_FIELDS) body[f.key] = orNull((form as Record<string, string>)[f.key] ?? "");
    if (project) {
      update.mutate(body, { onSuccess: () => setOpen(false) });
    } else {
      create.mutate({ ...body, workstreams: SUGGESTED_WORKSTREAMS.filter((s) => streams.has(s)) }, {
        onSuccess: (p) => { setOpen(false); router.push(`/projects/${p.id}`); },
      });
    }
  }

  const pending = create.isPending || update.isPending;
  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) { setForm(initial(project)); setMore(!!project); } setOpen(o); }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{project ? "Edit project" : "New project"}</DialogTitle>
          <DialogDescription>Only the name is required. You can add context at any time — unknowns are fine.</DialogDescription>
        </DialogHeader>
        <form id="project-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <TextField label="Project name" required value={form.name} onChange={(v) => set("name", v)} className="sm:col-span-2" autoFocus />
          <SelectField label="Lifecycle stage" value={form.stage_id} onChange={(v) => set("stage_id", v)} noneLabel="Not set"
            options={(stages.data ?? []).filter((s) => s.is_active).map((s) => ({ value: s.id, label: s.name }))} />
          <SelectField label="Priority" value={form.priority} onChange={(v) => set("priority", v ?? "medium")}
            options={PRIORITIES.map((p) => ({ value: p, label: PRIORITY_LABEL[p] }))} />
          <TextField label="Start date" type="date" value={form.start_date} onChange={(v) => set("start_date", v)} />
          <TextField label="Target completion date" type="date" value={form.target_date} onChange={(v) => set("target_date", v)} />
          <TextAreaField label="Description" value={form.description} onChange={(v) => set("description", v)} className="sm:col-span-2" />
          <TextAreaField label="Objectives" value={form.objectives} onChange={(v) => set("objectives", v)} className="sm:col-span-2" hint="One per line works well." />

          {!project && (
            <fieldset className="sm:col-span-2">
              <legend className="mb-2 text-sm font-medium">Workstreams to create</legend>
              <p className="mb-2 text-xs text-muted-foreground">Pick only what this project needs. You can add, rename or remove workstreams later.</p>
              <div className="grid gap-1.5 sm:grid-cols-2">
                {SUGGESTED_WORKSTREAMS.map((s) => (
                  <label key={s} className="flex items-center gap-2 text-sm">
                    <Checkbox checked={streams.has(s)} onCheckedChange={(c) => setStreams((cur) => { const n = new Set(cur); if (c) n.add(s); else n.delete(s); return n; })} />
                    {s}
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          {more ? (
            <>
              {TEXT_FIELDS.filter((f) => f.key !== "description" && f.key !== "objectives").map((f) => (
                <TextAreaField key={f.key} label={f.label} hint={f.hint} rows={2} className="sm:col-span-2"
                  value={(form as Record<string, string>)[f.key] ?? ""} onChange={(v) => set(f.key, v)} />
              ))}
              <TextField label="Repository location or URL" value={form.repository_url} onChange={(v) => set("repository_url", v)} />
              <TextField label="Documentation location" value={form.docs_location} onChange={(v) => set("docs_location", v)} />
            </>
          ) : (
            <Button type="button" variant="link" className="justify-self-start px-0" onClick={() => setMore(true)}>
              Add problem statement, scope, users, risks and more…
            </Button>
          )}
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button type="submit" form="project-form" disabled={pending || !form.name.trim()}>
            {pending ? "Saving…" : project ? "Save project" : "Create project"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
