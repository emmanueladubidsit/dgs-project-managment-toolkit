"use client";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { CLASSIFICATION_LABEL, DELIVERABLE_STATUS_LABEL, formatDate, METHODOLOGY_KIND_LABEL } from "@/lib/format";
import { useProjects } from "@/lib/queries";
import {
  useAdopt, useAdoptions, useCreateMethodology, useFromProject, useMethodologies, useMethodology, useMethodologyAction,
  useRemoveAdoption, useUpdateProjectDeliverable,
} from "@/lib/queries-library";
import type { Classification, MethodologyDetail } from "@/lib/types";
import { cn } from "@/lib/utils";
import { EmptyState, NONE, Section } from "./common";
import { ConfirmDialog } from "./confirm-dialog";
import { orNull, SelectField, TextAreaField, TextField } from "./form-fields";

export const CLASS_STYLE: Record<Classification, string> = {
  mandatory: "bg-destructive/10 text-destructive",
  recommended: "bg-primary/10 text-primary",
  optional: "bg-muted text-muted-foreground",
  not_applicable: "bg-muted text-muted-foreground line-through",
};

export const STATUS_STYLE: Record<string, string> = {
  draft: "bg-warning/15 text-warning", published: "bg-success/12 text-success", deprecated: "bg-muted text-muted-foreground line-through",
};

export function ClassificationBadge({ value }: { value: Classification }) {
  return <span className={cn("rounded px-1.5 py-0.5 text-xs font-medium", CLASS_STYLE[value])}>{CLASSIFICATION_LABEL[value]}</span>;
}

// ------------------------------------------------------------------ create / from project
export function NewMethodologyDialog({ trigger }: { trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [kind, setKind] = useState("methodology");
  const [purpose, setPurpose] = useState("");
  const create = useCreateMethodology();
  const router = useRouter();
  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) { setName(""); setPurpose(""); } setOpen(o); }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>New methodology</DialogTitle><DialogDescription>Starts as a draft. Add stages, activities and deliverables next.</DialogDescription></DialogHeader>
        <form id="new-m" className="space-y-4" onSubmit={(e) => { e.preventDefault(); create.mutate({ name: name.trim(), kind, purpose: orNull(purpose) }, { onSuccess: (m) => { setOpen(false); router.push(`/methodologies/${m.id}`); } }); }}>
          <TextField label="Name" required value={name} onChange={setName} autoFocus />
          <SelectField label="Type" value={kind} onChange={(v) => setKind(v ?? "methodology")} options={Object.entries(METHODOLOGY_KIND_LABEL).map(([value, label]) => ({ value, label }))} />
          <TextAreaField label="Purpose" value={purpose} onChange={setPurpose} />
        </form>
        <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" form="new-m" disabled={!name.trim() || create.isPending}>Create draft</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function FromProjectDialog({ trigger, projectId }: { trigger: ReactNode; projectId?: string }) {
  const [open, setOpen] = useState(false);
  const [project, setProject] = useState<string | null>(projectId ?? null);
  const [name, setName] = useState("");
  const [kind, setKind] = useState("playbook");
  const projects = useProjects({ include_archived: true });
  const from = useFromProject();
  const router = useRouter();
  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) { setName(""); setProject(projectId ?? null); } setOpen(o); }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create a reusable playbook from a project</DialogTitle>
          <DialogDescription>Milestones become stages and tasks become activities. Dates, people and progress are not copied. Review it for project-specific or confidential details before publishing.</DialogDescription>
        </DialogHeader>
        <form id="from-p" className="space-y-4" onSubmit={(e) => { e.preventDefault(); if (project) from.mutate({ projectId: project, name: name.trim(), kind }, { onSuccess: (m) => { setOpen(false); router.push(`/methodologies/${m.id}`); } }); }}>
          <SelectField label="Project" value={project} onChange={setProject} noneLabel={project ? undefined : "Choose a project"} disabled={!!projectId}
            options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
          <TextField label="Name" required value={name} onChange={setName} placeholder="e.g. Launching an internal tool" />
          <SelectField label="Type" value={kind} onChange={(v) => setKind(v ?? "playbook")} options={Object.entries(METHODOLOGY_KIND_LABEL).map(([value, label]) => ({ value, label }))} />
        </form>
        <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" form="from-p" disabled={!name.trim() || !project || from.isPending}>Create draft</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ------------------------------------------------------------------ adopt
export function AdoptDialog({ trigger, methodology, projectId }: { trigger: ReactNode; methodology?: MethodologyDetail; projectId?: string }) {
  const [open, setOpen] = useState(false);
  const [mid, setMid] = useState<string | null>(methodology?.id ?? null);
  const [project, setProject] = useState<string | null>(projectId ?? null);
  const [stages, setStages] = useState<Set<string> | null>(null);
  const [milestones, setMilestones] = useState(true);
  const [tasks, setTasks] = useState(true);
  const [start, setStart] = useState("");
  const list = useMethodologies({});
  const detail = useMethodology(mid ?? "");
  const m = methodology ?? (mid ? detail.data : undefined);
  const projects = useProjects();
  const adopt = useAdopt();
  const selected = stages ?? new Set(m?.stages.map((s) => s.id) ?? []);
  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) { setStages(null); setProject(projectId ?? null); setMid(methodology?.id ?? null); } setOpen(o); }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Adopt {m ? `“${m.name}”` : "a methodology"}</DialogTitle>
          <DialogDescription>Adopt it whole or only the stages you need. Tasks that already exist with the same title are not duplicated.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {!methodology && <SelectField label="Methodology" value={mid} onChange={(v) => { setMid(v); setStages(null); }} noneLabel={mid ? undefined : "Choose…"}
            options={(list.data ?? []).filter((x) => x.status !== "deprecated").map((x) => ({ value: x.id, label: `${x.name} (${METHODOLOGY_KIND_LABEL[x.kind]})` }))} />}
          {!projectId && <SelectField label="Project" value={project} onChange={setProject} noneLabel={project ? undefined : "Choose a project"}
            options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />}
          {m && (
            <fieldset>
              <legend className="mb-2 text-sm font-medium">Stages to adopt</legend>
              <div className="space-y-1.5">
                {m.stages.map((s) => (
                  <label key={s.id} className="flex items-center gap-2 text-sm">
                    <Checkbox checked={selected.has(s.id)} onCheckedChange={(c) => { const n = new Set(selected); if (c) n.add(s.id); else n.delete(s.id); setStages(n); }} />
                    {s.name} <span className="text-xs text-muted-foreground">({s.activities.length} activit{s.activities.length === 1 ? "y" : "ies"})</span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}
          <label className="flex items-center gap-2 text-sm"><Checkbox checked={milestones} onCheckedChange={(c) => setMilestones(!!c)} /> Create a milestone for each stage</label>
          <label className="flex items-center gap-2 text-sm"><Checkbox checked={tasks} onCheckedChange={(c) => setTasks(!!c)} /> Create a task for each activity (expected output becomes acceptance criteria)</label>
          {milestones && <TextField label="Start date (optional)" type="date" value={start} onChange={setStart} hint="Milestones are spaced a week apart from here. Leave blank to set dates yourself." />}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button disabled={!m || !project || selected.size === 0 || adopt.isPending}
            onClick={() => m && project && adopt.mutate({ projectId: project, methodology_id: m.id, stage_ids: [...selected], create_milestones: milestones, create_tasks: tasks, start_date: orNull(start) }, { onSuccess: () => setOpen(false) })}>
            Adopt
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ------------------------------------------------------------------ edit details
const META_FIELDS: [keyof MethodologyDetail, string][] = [
  ["purpose", "Purpose"], ["when_to_use", "When to use it"], ["prerequisites", "Prerequisites"], ["tools", "Tools"],
  ["dependencies", "Dependencies"], ["common_risks", "Common risks"], ["completion_criteria", "Completion criteria"], ["limitations", "Limitations"],
];

export function MetaDialog({ m, trigger }: { m: MethodologyDetail; trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  const fresh = () => ({ name: m.name, kind: m.kind as string, note: "", ...Object.fromEntries(META_FIELDS.map(([k]) => [k, (m[k] as string | null) ?? ""])) }) as Record<string, string>;
  const [form, setForm] = useState(fresh);
  const act = useMethodologyAction(m.id);
  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) setForm(fresh()); setOpen(o); }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader><DialogTitle>Edit details</DialogTitle><DialogDescription>Saving creates a new version.</DialogDescription></DialogHeader>
        <form id="meta" className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => {
          e.preventDefault();
          act.mutate({ method: "PATCH", success: "Saved.", body: { name: form.name.trim(), kind: form.kind, change_note: orNull(form.note), ...Object.fromEntries(META_FIELDS.map(([k]) => [k, orNull(form[k as string])])) } }, { onSuccess: () => setOpen(false) });
        }}>
          <TextField label="Name" required value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
          <SelectField label="Type" value={form.kind} onChange={(v) => setForm({ ...form, kind: v ?? "methodology" })} options={Object.entries(METHODOLOGY_KIND_LABEL).map(([value, label]) => ({ value, label }))} />
          {META_FIELDS.map(([k, label]) => <TextAreaField key={k} label={label} rows={2} className="sm:col-span-2" value={form[k as string]} onChange={(v) => setForm({ ...form, [k]: v })} />)}
          <TextField label="Change note (optional)" value={form.note} onChange={(v) => setForm({ ...form, note: v })} className="sm:col-span-2" />
        </form>
        <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" form="meta" disabled={!form.name.trim() || act.isPending}>Save</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ------------------------------------------------------------------ structure editor
type EActivity = { title: string; instructions: string; expected_output: string };
type EStage = { key: string; name: string; description: string; validation_criteria: string; activities: EActivity[] };
type EDeliverable = { name: string; description: string; classification: Classification; stage_key: string | null };

const move = <T,>(arr: T[], i: number, d: number) => { const n = [...arr]; const j = i + d; if (j < 0 || j >= n.length) return n; [n[i], n[j]] = [n[j], n[i]]; return n; };

export function StructureDialog({ m, trigger }: { m: MethodologyDetail; trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  const fresh = () => ({
    stages: m.stages.map((s) => ({ key: s.id, name: s.name, description: s.description ?? "", validation_criteria: s.validation_criteria ?? "",
      activities: s.activities.map((a) => ({ title: a.title, instructions: a.instructions ?? "", expected_output: a.expected_output ?? "" })) })) as EStage[],
    deliverables: m.deliverables.map((d) => ({ name: d.name, description: d.description ?? "", classification: d.classification, stage_key: d.stage_id })) as EDeliverable[],
    note: "",
  });
  const [form, setForm] = useState(fresh);
  const act = useMethodologyAction(m.id);
  const setStage = (i: number, s: Partial<EStage>) => setForm((f) => ({ ...f, stages: f.stages.map((x, j) => (j === i ? { ...x, ...s } : x)) }));
  const setAct = (i: number, k: number, a: Partial<EActivity>) => setStage(i, { activities: form.stages[i].activities.map((x, j) => (j === k ? { ...x, ...a } : x)) });
  const valid = form.stages.every((s) => s.name.trim() && s.activities.every((a) => a.title.trim())) && form.deliverables.every((d) => d.name.trim());

  function save() {
    act.mutate({ path: "/structure", method: "PUT", success: "Structure saved as a new version.", body: {
      change_note: orNull(form.note),
      stages: form.stages.map((s) => ({ key: s.key, name: s.name.trim(), description: orNull(s.description), validation_criteria: orNull(s.validation_criteria),
        activities: s.activities.map((a) => ({ title: a.title.trim(), instructions: orNull(a.instructions), expected_output: orNull(a.expected_output) })) })),
      deliverables: form.deliverables.map((d) => ({ name: d.name.trim(), description: orNull(d.description), classification: d.classification,
        stage_key: d.stage_key && form.stages.some((s) => s.key === d.stage_key) ? d.stage_key : null })),
    } }, { onSuccess: () => setOpen(false) });
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) setForm(fresh()); setOpen(o); }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Edit stages, activities and deliverables</DialogTitle>
          <DialogDescription>The previous structure is kept as a version. Projects that already adopted it keep their tasks.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {form.stages.map((s, i) => (
            <fieldset key={s.key} className="rounded-xl border p-3">
              <legend className="px-1 text-sm font-semibold">Stage {i + 1}</legend>
              <div className="mb-2 flex gap-2">
                <Input value={s.name} onChange={(e) => setStage(i, { name: e.target.value })} placeholder="Stage name" aria-label={`Stage ${i + 1} name`} />
                <Button size="icon-sm" variant="ghost" aria-label="Move stage up" onClick={() => setForm((f) => ({ ...f, stages: move(f.stages, i, -1) }))}><ArrowUp /></Button>
                <Button size="icon-sm" variant="ghost" aria-label="Move stage down" onClick={() => setForm((f) => ({ ...f, stages: move(f.stages, i, 1) }))}><ArrowDown /></Button>
                <Button size="icon-sm" variant="ghost" aria-label="Remove stage" onClick={() => setForm((f) => ({ ...f, stages: f.stages.filter((_, j) => j !== i) }))}><Trash2 /></Button>
              </div>
              <Textarea rows={1} className="mb-2" value={s.description} onChange={(e) => setStage(i, { description: e.target.value })} placeholder="Description (optional)" aria-label={`Stage ${i + 1} description`} />
              <ul className="space-y-2 border-l-2 pl-3">
                {s.activities.map((a, k) => (
                  <li key={k} className="space-y-1">
                    <div className="flex gap-2">
                      <Input value={a.title} onChange={(e) => setAct(i, k, { title: e.target.value })} placeholder="Activity" aria-label={`Stage ${i + 1} activity ${k + 1}`} />
                      <Button size="icon-sm" variant="ghost" aria-label="Move activity up" onClick={() => setStage(i, { activities: move(s.activities, k, -1) })}><ArrowUp /></Button>
                      <Button size="icon-sm" variant="ghost" aria-label="Remove activity" onClick={() => setStage(i, { activities: s.activities.filter((_, j) => j !== k) })}><Trash2 /></Button>
                    </div>
                    <div className="grid gap-1 sm:grid-cols-2">
                      <Input value={a.expected_output} onChange={(e) => setAct(i, k, { expected_output: e.target.value })} placeholder="Expected output" aria-label="Expected output" />
                      <Input value={a.instructions} onChange={(e) => setAct(i, k, { instructions: e.target.value })} placeholder="Instructions (optional)" aria-label="Instructions" />
                    </div>
                  </li>
                ))}
              </ul>
              <Button size="xs" variant="ghost" className="mt-2" onClick={() => setStage(i, { activities: [...s.activities, { title: "", instructions: "", expected_output: "" }] })}><Plus /> Activity</Button>
            </fieldset>
          ))}
          <Button size="sm" variant="outline" onClick={() => setForm((f) => ({ ...f, stages: [...f.stages, { key: `new-${Date.now()}`, name: "", description: "", validation_criteria: "", activities: [] }] }))}><Plus /> Add stage</Button>

          <div>
            <h3 className="mb-2 text-sm font-semibold">Deliverables</h3>
            <ul className="space-y-2">
              {form.deliverables.map((d, i) => (
                <li key={i} className="grid gap-2 sm:grid-cols-[1fr_10rem_12rem_auto]">
                  <Input value={d.name} onChange={(e) => setForm((f) => ({ ...f, deliverables: f.deliverables.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)) }))} placeholder="Deliverable" aria-label={`Deliverable ${i + 1}`} />
                  <Select value={d.classification} onValueChange={(v) => setForm((f) => ({ ...f, deliverables: f.deliverables.map((x, j) => (j === i ? { ...x, classification: v as Classification } : x)) }))}>
                    <SelectTrigger aria-label="Classification"><SelectValue /></SelectTrigger>
                    <SelectContent>{Object.entries(CLASSIFICATION_LABEL).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
                  </Select>
                  <Select value={d.stage_key ?? NONE} onValueChange={(v) => setForm((f) => ({ ...f, deliverables: f.deliverables.map((x, j) => (j === i ? { ...x, stage_key: v === NONE ? null : v } : x)) }))}>
                    <SelectTrigger aria-label="Stage"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NONE}>Whole methodology</SelectItem>
                      {form.stages.map((s, j) => <SelectItem key={s.key} value={s.key}>{s.name || `Stage ${j + 1}`}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Button size="icon-sm" variant="ghost" aria-label="Remove deliverable" onClick={() => setForm((f) => ({ ...f, deliverables: f.deliverables.filter((_, j) => j !== i) }))}><Trash2 /></Button>
                </li>
              ))}
            </ul>
            <Button size="sm" variant="outline" className="mt-2" onClick={() => setForm((f) => ({ ...f, deliverables: [...f.deliverables, { name: "", description: "", classification: "recommended", stage_key: null }] }))}><Plus /> Add deliverable</Button>
          </div>
          <TextField label="Change note (optional)" value={form.note} onChange={(v) => setForm((f) => ({ ...f, note: v }))} />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={save} disabled={!valid || act.isPending}>{valid ? "Save structure" : "Fill in all names"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ------------------------------------------------------------------ project panel
export function ProjectMethodologies({ projectId }: { projectId: string }) {
  const q = useAdoptions(projectId);
  const update = useUpdateProjectDeliverable();
  const remove = useRemoveAdoption();
  const adoptions = q.data ?? [];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-end gap-2">
        <FromProjectDialog projectId={projectId} trigger={<Button variant="outline">Save as reusable playbook</Button>} />
        <AdoptDialog projectId={projectId} trigger={<Button><Plus /> Adopt a methodology</Button>} />
      </div>
      {adoptions.length === 0 ? (
        <EmptyState title="No methodology adopted" description="Adopt a methodology to plan this project from a proven structure, and track its required deliverables." />
      ) : adoptions.map((a) => {
        const required = a.deliverables.filter((d) => d.classification === "mandatory");
        const done = required.filter((d) => d.status === "done").length;
        return (
          <Section key={a.id} title={<><Link href={`/methodologies/${a.methodology_id}`} className="hover:underline">{a.methodology_name}</Link> <span className="font-normal text-muted-foreground">· adopted v{a.methodology_version} on {formatDate(a.adopted_at.slice(0, 10))}</span></>}
            actions={<ConfirmDialog trigger={<Button size="xs" variant="ghost">Remove</Button>} confirmLabel="Remove" title="Stop tracking this methodology?"
              description="Its deliverable tracking is removed. Milestones and tasks it created are kept." onConfirm={() => remove.mutate(a.id)} />}>
            {a.current_version > a.methodology_version && <p className="mb-2 text-xs text-info">A newer version (v{a.current_version}) of this methodology exists.</p>}
            <p className="mb-3 text-sm">Mandatory deliverables: <strong>{done} of {required.length}</strong> done.</p>
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-muted-foreground"><th className="py-1 font-medium">Deliverable</th><th className="font-medium">Classification</th><th className="font-medium">Status</th></tr></thead>
              <tbody>
                {a.deliverables.map((d) => (
                  <tr key={d.id} className="border-t">
                    <td className="py-1.5">{d.name}</td>
                    <td>
                      <Select value={d.classification} onValueChange={(v) => update.mutate({ id: d.id, classification: v as Classification })}>
                        <SelectTrigger className="h-7 w-40" aria-label={`Classification of ${d.name}`}><SelectValue /></SelectTrigger>
                        <SelectContent>{Object.entries(CLASSIFICATION_LABEL).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
                      </Select>
                    </td>
                    <td>
                      <Select value={d.status} onValueChange={(v) => update.mutate({ id: d.id, status: v as never })}>
                        <SelectTrigger className="h-7 w-36" aria-label={`Status of ${d.name}`}><SelectValue /></SelectTrigger>
                        <SelectContent>{Object.entries(DELIVERABLE_STATUS_LABEL).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
                      </Select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        );
      })}
    </div>
  );
}
