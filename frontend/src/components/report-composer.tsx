"use client";
import { Copy, Download, FileDown, FileText, Presentation, Save, Sparkles, Trash2 } from "lucide-react";
import { downloadPost, ExportMenu, useAICall, useAIStatus } from "./ai";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { MarkdownView } from "./markdown-view";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  const ai = useAIStatus();
  const { call, busy } = useAICall();
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
        <p className="mt-2 text-xs text-muted-foreground">Reports are built only from tasks, activity and updates stored in the workspace. Sections with nothing recorded are left out and listed in one closing line, so nothing is invented. Edit the text on the Edit tab; Word, PDF and slides use the same content.</p>
      </Section>

      {draft && (
        <Section title={draft.id ? "Editing saved report" : "Draft — review and edit before sharing"}
          actions={<Button size="sm" variant="ghost" onClick={() => setDraft(null)}>Close</Button>}>
          <div className="space-y-3">
            <Input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} aria-label="Report title" />
            <Tabs defaultValue="preview">
              <TabsList>
                <TabsTrigger value="preview">Preview</TabsTrigger>
                <TabsTrigger value="edit">Edit</TabsTrigger>
              </TabsList>
              <TabsContent value="preview">
                <MarkdownView source={draft.content} className="max-h-[70vh] overflow-y-auto rounded-lg border bg-card px-5 py-4 text-sm leading-relaxed" />
              </TabsContent>
              <TabsContent value="edit">
                <Textarea value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })} rows={24}
                  className="font-mono text-sm" aria-label="Report content (Markdown)" />
              </TabsContent>
            </Tabs>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => {
                if (draft.id) update.mutate({ id: draft.id, title: draft.title, content: draft.content });
                else save.mutate(draft, { onSuccess: (r) => setDraft(r) });
              }} disabled={save.isPending || update.isPending || !draft.title.trim() || !draft.content.trim()}>
                <Save /> {draft.id ? "Save changes" : "Save report"}
              </Button>
              <Button variant="outline" onClick={() => copy(draft.content)}><Copy /> Copy</Button>
              <Button variant="outline" onClick={() => download(draft.title, draft.content)}><Download /> Markdown</Button>
              <Button variant="outline" onClick={() => downloadPost(draft.title, draft.content, "docx")}><FileDown /> Word</Button>
              <Button variant="outline" onClick={() => downloadPost(draft.title, draft.content, "pdf")}><FileDown /> PDF</Button>
              <Button variant="outline" onClick={() => downloadPost(draft.title, draft.content, "pptx")}><Presentation /> Slides</Button>
              {ai.data?.ready && !draft.content.includes("## Executive summary") && (
                <Button variant="outline" disabled={busy} onClick={async () => {
                  const r = await call<{ text: string }>("/ai/report-summary", { content: draft.content });
                  if (r) {
                    const lines = draft.content.split("\n");
                    const at = lines.findIndex((l, i) => i > 0 && l.startsWith("## "));
                    const block = ["## Executive summary", "", "_AI-assisted summary of the sections below — check before sharing._", "", r.text, ""];
                    lines.splice(at === -1 ? lines.length : at, 0, ...block);
                    setDraft({ ...draft, content: lines.join("\n") });
                  }
                }}><Sparkles /> {busy ? "Summarising…" : "Add AI executive summary"}</Button>
              )}
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
                    <ExportMenu label="" items={[
                      { label: "Word document", href: `/api/export/report/${r.id}?format=docx` },
                      { label: "PDF", href: `/api/export/report/${r.id}?format=pdf` },
                      { label: "Slides (PowerPoint)", href: `/api/export/report/${r.id}?format=pptx` },
                    ]} />
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
