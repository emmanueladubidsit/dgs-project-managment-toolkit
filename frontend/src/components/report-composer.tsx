"use client";
import { Copy, Download, FileText, Save, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { formatDate, todayISO } from "@/lib/format";
import { useDeleteReport, useGenerateReport, useProjects, useReports, useSaveReport, useUpdateReport } from "@/lib/queries";
import type { Report, ReportDraft, ReportKind } from "@/lib/types";
import { EmptyState, QueryView, Section } from "./common";
import { ConfirmDialog } from "./confirm-dialog";
import { SelectField, TextField } from "./form-fields";

const KIND_LABEL: Record<ReportKind, string> = { daily: "Daily report", weekly: "Weekly report", project: "Project report" };

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard.");
  } catch {
    toast.error("Your browser blocked clipboard access. Select the text and copy it manually.");
  }
}

function download(title: string, content: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${title.replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "-").toLowerCase() || "report"}.md`;
  a.click();
  URL.revokeObjectURL(a.href);
}

/** Generate a draft from stored data, edit it, then copy, download or save it. */
export function ReportComposer({ projectId }: { projectId?: string }) {
  const [kind, setKind] = useState<ReportKind>(projectId ? "project" : "weekly");
  const [date, setDate] = useState(todayISO());
  const [project, setProject] = useState<string | null>(projectId ?? null);
  const [audience, setAudience] = useState("stakeholder");
  const [draft, setDraft] = useState<(ReportDraft & { id?: string }) | null>(null);
  const projects = useProjects();
  const generate = useGenerateReport();
  const save = useSaveReport();
  const update = useUpdateReport();

  return (
    <div className="space-y-4">
      <Section title="Generate a report">
        <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 lg:items-end" onSubmit={(e) => {
          e.preventDefault();
          generate.mutate({ kind, date, project_id: project, audience }, { onSuccess: (d) => setDraft(d) });
        }}>
          <SelectField label="Report" value={kind} onChange={(v) => setKind((v ?? "weekly") as ReportKind)}
            options={Object.entries(KIND_LABEL).map(([value, label]) => ({ value, label }))} />
          <TextField label={kind === "weekly" ? "Any day in the week" : kind === "project" ? "As at" : "Day"} type="date" value={date} onChange={setDate} />
          <SelectField label="Project" value={project} onChange={setProject} noneLabel={kind === "project" ? "Choose a project" : "All projects"}
            disabled={!!projectId} options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
          <SelectField label="Format" value={audience} onChange={(v) => setAudience(v ?? "stakeholder")}
            options={[{ value: "stakeholder", label: "Stakeholder (concise)" }, { value: "technical", label: "Technical (detailed)" }]} />
          <Button type="submit" disabled={generate.isPending || (kind === "project" && !project)}>
            <FileText /> {generate.isPending ? "Generating…" : "Generate"}
          </Button>
        </form>
        <p className="mt-2 text-xs text-muted-foreground">Reports are built only from tasks, activity and updates stored in the workspace. Empty sections say “None recorded” rather than inventing content.</p>
      </Section>

      {draft && (
        <Section title={draft.id ? "Editing saved report" : "Draft — review and edit before sharing"}
          actions={<Button size="sm" variant="ghost" onClick={() => setDraft(null)}>Close</Button>}>
          <div className="space-y-3">
            <Input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} aria-label="Report title" />
            <Textarea value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })} rows={24}
              className="font-mono text-sm" aria-label="Report content (Markdown)" />
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => {
                if (draft.id) update.mutate({ id: draft.id, title: draft.title, content: draft.content });
                else save.mutate(draft, { onSuccess: (r) => setDraft(r) });
              }} disabled={save.isPending || update.isPending || !draft.title.trim() || !draft.content.trim()}>
                <Save /> {draft.id ? "Save changes" : "Save report"}
              </Button>
              <Button variant="outline" onClick={() => copy(draft.content)}><Copy /> Copy</Button>
              <Button variant="outline" onClick={() => download(draft.title, draft.content)}><Download /> Download .md</Button>
            </div>
          </div>
        </Section>
      )}

      <SavedReports projectId={projectId} onOpen={(r) => setDraft(r)} />
    </div>
  );
}

function SavedReports({ projectId, onOpen }: { projectId?: string; onOpen: (r: Report) => void }) {
  const q = useReports();
  const del = useDeleteReport();
  return (
    <Section title="Saved reports">
      <QueryView query={q}>
        {(reports) => {
          const list = projectId ? reports.filter((r) => r.project_id === projectId) : reports;
          if (!list.length) return <EmptyState title="No saved reports" description="Generate a report above and save it to keep an editable copy." />;
          return (
            <ul className="divide-y">
              {list.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-2 py-2">
                  <button className="min-w-0 text-left" onClick={() => onOpen(r)}>
                    <span className="block truncate text-sm font-medium hover:underline">{r.title}</span>
                    <span className="text-xs text-muted-foreground">{KIND_LABEL[r.kind]} · {formatDate(r.period_start)} – {formatDate(r.period_end)}</span>
                  </button>
                  <div className="flex shrink-0 gap-1">
                    <Button size="icon-sm" variant="ghost" aria-label={`Copy ${r.title}`} onClick={() => copy(r.content)}><Copy /></Button>
                    <ConfirmDialog trigger={<Button size="icon-sm" variant="ghost" aria-label={`Delete ${r.title}`}><Trash2 /></Button>}
                      title="Delete this saved report?" description="The underlying tasks and updates are not affected; only this saved copy is removed."
                      onConfirm={() => del.mutate(r.id)} />
                  </div>
                </li>
              ))}
            </ul>
          );
        }}
      </QueryView>
    </Section>
  );
}
