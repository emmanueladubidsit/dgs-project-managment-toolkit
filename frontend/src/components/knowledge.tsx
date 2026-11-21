"use client";
import { AlertTriangle, BadgeCheck, BookCheck, FlaskConical, History, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { VERIFICATION_LABEL } from "@/lib/format";
import { useCreateKnowledge, useKnowledgeTemplates, useUpdateKnowledge } from "@/lib/queries-library";
import { useProjects } from "@/lib/queries";
import type { KnowledgeCategory, KnowledgeDetail, Verification } from "@/lib/types";
import { cn } from "@/lib/utils";
import { orNull, SelectField, TextAreaField, TextField } from "./form-fields";

const V_STYLE: Record<Verification, { cls: string; icon: typeof BadgeCheck }> = {
  verified_tested: { cls: "bg-success/12 text-success border-success/30", icon: BadgeCheck },
  verified_docs: { cls: "bg-success/12 text-success border-success/30", icon: BookCheck },
  applied_in_project: { cls: "bg-info/12 text-info border-info/30", icon: BadgeCheck },
  research_unimplemented: { cls: "bg-muted text-muted-foreground border-border", icon: FlaskConical },
  ai_suggestion: { cls: "bg-warning/15 text-warning border-warning/40", icon: Sparkles },
  outdated: { cls: "bg-destructive/10 text-destructive border-destructive/30 line-through", icon: History },
};

export function VerificationBadge({ value }: { value: Verification }) {
  const { cls, icon: Icon } = V_STYLE[value];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs font-medium whitespace-nowrap", cls)}>
      <Icon className="size-3" aria-hidden />{VERIFICATION_LABEL[value]}
    </span>
  );
}

/** Shown on anything that is not verified, so it is never mistaken for established fact. */
export function VerificationNotice({ value }: { value: Verification }) {
  if (value === "ai_suggestion") {
    return <p className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-sm"><AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />AI-generated suggestion awaiting review. Do not rely on it until a person has verified it.</p>;
  }
  if (value === "outdated") {
    return <p className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm"><History className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden />Outdated or superseded. Check its related items for the current guidance.</p>;
  }
  if (value === "research_unimplemented") {
    return <p className="rounded-lg bg-muted/60 px-3 py-2 text-sm text-muted-foreground">Research finding, not yet applied or tested in a project.</p>;
  }
  return null;
}

type FormState = {
  category: KnowledgeCategory; title: string; summary: string; content: string; verification: Verification;
  tags: string; sources: string; limitations: string; reuse_notes: string; origin_project_id: string | null;
  change_note: string; fields: Record<string, string>;
};

function initial(item?: KnowledgeDetail, category: KnowledgeCategory = "research"): FormState {
  return {
    category: item?.category ?? category, title: item?.title ?? "", summary: item?.summary ?? "",
    content: item?.content ?? "", verification: item?.verification ?? "research_unimplemented",
    tags: (item?.tags ?? []).join(", "), sources: item?.sources ?? "", limitations: item?.limitations ?? "",
    reuse_notes: item?.reuse_notes ?? "", origin_project_id: item?.projects.find((p) => p.role === "origin")?.project_id ?? null,
    change_note: "", fields: { ...(item?.fields ?? {}) },
  };
}

export function KnowledgeFormDialog({ item, trigger, defaultCategory, defaultProjectId }: {
  item?: KnowledgeDetail; trigger: ReactNode; defaultCategory?: KnowledgeCategory; defaultProjectId?: string;
}) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>(() => initial(item, defaultCategory));
  const templates = useKnowledgeTemplates();
  const projects = useProjects();
  const create = useCreateKnowledge();
  const update = useUpdateKnowledge(item?.id ?? "");
  const router = useRouter();
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setForm((f) => ({ ...f, [k]: v }));
  const template = templates.data?.find((t) => t.category === form.category);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const keys = new Set(template?.fields.map((f) => f.key));
    const body = {
      category: form.category, title: form.title.trim(), summary: orNull(form.summary), content: orNull(form.content),
      verification: form.verification, sources: orNull(form.sources), limitations: orNull(form.limitations),
      reuse_notes: orNull(form.reuse_notes), tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
      // Only send fields that belong to the chosen category's template.
      fields: Object.fromEntries(Object.entries(form.fields).filter(([k]) => keys.has(k))),
    };
    if (item) update.mutate({ ...body, change_note: form.change_note || undefined }, { onSuccess: () => setOpen(false) });
    else create.mutate({ ...body, origin_project_id: form.origin_project_id }, { onSuccess: (k) => { setOpen(false); router.push(`/knowledge/${k.id}`); } });
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) setForm({ ...initial(item, defaultCategory), ...(!item && defaultProjectId ? { origin_project_id: defaultProjectId } : {}) }); setOpen(o); }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{item ? "Edit knowledge" : "New knowledge item"}</DialogTitle>
          <DialogDescription>{item ? "Saving creates a new version; earlier versions stay in the history." : "Pick a category to get a structured template. Every field is optional except the title."}</DialogDescription>
        </DialogHeader>
        <form id="knowledge-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <SelectField label="Category" value={form.category} onChange={(v) => set("category", (v ?? "research") as KnowledgeCategory)}
            options={(templates.data ?? []).map((t) => ({ value: t.category, label: t.label }))} />
          <SelectField label="Verification status" value={form.verification} onChange={(v) => set("verification", (v ?? "research_unimplemented") as Verification)}
            options={Object.entries(VERIFICATION_LABEL).map(([value, label]) => ({ value, label }))}
            hint="Be honest — only mark verified what you have tested or checked." />
          <TextField label="Title" required value={form.title} onChange={(v) => set("title", v)} className="sm:col-span-2" autoFocus />
          <TextAreaField label="Summary" value={form.summary} onChange={(v) => set("summary", v)} rows={2} className="sm:col-span-2" />
          {template?.fields.map((f) => (
            <TextAreaField key={f.key} label={f.label} hint={f.hint || undefined} rows={f.key.includes("question") || f.key.includes("date") || f.key === "decision_status" || f.key === "researcher" ? 1 : 3}
              value={form.fields[f.key] ?? ""} onChange={(v) => setForm((s) => ({ ...s, fields: { ...s.fields, [f.key]: v } }))} className="sm:col-span-2" />
          ))}
          <TextAreaField label={template?.fields.length ? "Additional notes (Markdown)" : "Content (Markdown)"} value={form.content}
            onChange={(v) => set("content", v)} rows={template?.fields.length ? 3 : 10} className="sm:col-span-2" />
          <TextAreaField label="Sources and references" value={form.sources} onChange={(v) => set("sources", v)} rows={2} hint="Links or citations, one per line." />
          <TextAreaField label="Limitations" value={form.limitations} onChange={(v) => set("limitations", v)} rows={2} />
          <TextAreaField label="Before reusing" value={form.reuse_notes} onChange={(v) => set("reuse_notes", v)} rows={2} className="sm:col-span-2"
            hint="What someone must adapt or check — project-specific assumptions, confidential details." />
          <TextField label="Tags" value={form.tags} onChange={(v) => set("tags", v)} placeholder="design-system, tokens" hint="Separate with commas." />
          {item ? (
            <TextField label="Change note (optional)" value={form.change_note} onChange={(v) => set("change_note", v)} placeholder="What changed and why" />
          ) : (
            <SelectField label="Origin project" value={form.origin_project_id} onChange={(v) => set("origin_project_id", v)} noneLabel="None"
              options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} hint="Where this knowledge came from." />
          )}
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button type="submit" form="knowledge-form" disabled={!form.title.trim() || create.isPending || update.isPending}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
