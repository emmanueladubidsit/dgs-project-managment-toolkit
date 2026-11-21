"use client";
import { BookOpen, Copy, FileDown, FolderPlus, ListChecks, MessageSquare, PenLine, Send, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { AIBadge, AIOffNotice, downloadPost, Sources, useAICall, useAIStatus, type Source } from "@/components/ai";
import { PageHeader, Section } from "@/components/common";
import { SelectField, TextAreaField, TextField } from "@/components/form-fields";
import { ProjectFormDialog, type ProjectDraft } from "@/components/project-form-dialog";
import { SuggestionCard } from "@/components/suggestions";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useProjects } from "@/lib/queries";
import { useCreateKnowledge, useSuggestions } from "@/lib/queries-library";
import type { Suggestion } from "@/lib/types";

const copy = (t: string) => navigator.clipboard.writeText(t).then(() => toast.success("Copied."), () => toast.error("Copy blocked by the browser."));

function ProjectPicker({ value, onChange, noneLabel = "Whole workspace" }: { value: string | null; onChange: (v: string | null) => void; noneLabel?: string }) {
  const projects = useProjects();
  return <SelectField label="Project" value={value} onChange={onChange} noneLabel={noneLabel} options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />;
}

export default function AssistantPage() {
  const status = useAIStatus();
  const [tab, setTab] = useState("ask");
  const ready = status.data?.ready;
  return (
    <>
      <PageHeader title="Assistant" description="Ask about your projects, write with project context, and turn notes and ideas into plans — using your workspace data, with everything reviewed before it is saved."
        actions={status.data && <span className="text-xs text-muted-foreground">{status.data.provider === "manual" ? "Copy-and-paste mode" : status.data.provider === "openai_compatible" ? `Using ${status.data.model}${status.data.is_local ? " (on this computer)" : ""}` : "Off"}</span>} />
      {status.data && !ready && <div className="mb-4"><AIOffNotice /></div>}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="mb-4 flex h-auto flex-wrap justify-start">
          <TabsTrigger value="ask"><MessageSquare /> Ask</TabsTrigger>
          <TabsTrigger value="write"><PenLine /> Write</TabsTrigger>
          <TabsTrigger value="tasks"><ListChecks /> Notes → tasks</TabsTrigger>
          <TabsTrigger value="project"><FolderPlus /> New project from an idea</TabsTrigger>
          <TabsTrigger value="research"><BookOpen /> Research draft</TabsTrigger>
        </TabsList>
        <TabsContent value="ask"><Ask disabled={!ready} /></TabsContent>
        <TabsContent value="write"><Write disabled={!ready} /></TabsContent>
        <TabsContent value="tasks"><NotesToTasks disabled={!ready} /></TabsContent>
        <TabsContent value="project"><IdeaToProject disabled={!ready} /></TabsContent>
        <TabsContent value="research"><Research disabled={!ready} /></TabsContent>
      </Tabs>
    </>
  );
}

const QUICK = ["What needs my attention this week?", "What is blocked or overdue, and why?", "Summarise progress for a stakeholder update.", "What are the main risks right now?", "What should I work on next?"];

function Ask({ disabled }: { disabled: boolean }) {
  const { call, busy } = useAICall();
  const [project, setProject] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [thread, setThread] = useState<{ q: string; a: string; sources: Source[] }[]>([]);
  async function ask(question: string) {
    if (!question.trim()) return;
    const r = await call<{ answer: string; sources: Source[] }>("/ai/ask", { question, project_id: project });
    if (r) { setThread((t) => [{ q: question, a: r.answer, sources: r.sources }, ...t]); setQ(""); }
  }
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Section title="Ask a question" className="lg:col-span-1">
        <div className="space-y-3">
          <ProjectPicker value={project} onChange={setProject} />
          <TextAreaField label="Question" value={q} onChange={setQ} rows={4} placeholder="e.g. What is left before the Alpha milestone?" />
          <Button onClick={() => ask(q)} disabled={disabled || busy || !q.trim()}><Send /> {busy ? "Thinking…" : "Ask"}</Button>
          <div className="space-y-1 pt-2">
            <p className="text-xs font-medium text-muted-foreground">Quick questions</p>
            {QUICK.map((x) => <button key={x} disabled={disabled || busy} className="block text-left text-sm text-primary hover:underline disabled:opacity-50" onClick={() => ask(x)}>{x}</button>)}
          </div>
        </div>
      </Section>
      <div className="space-y-3 lg:col-span-2">
        {thread.length === 0 && <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">Answers use only your workspace data — projects, tasks, milestones, recent updates and linked knowledge. If something is not recorded, the assistant says so.</p>}
        {thread.map((t, i) => (
          <Section key={i} title={t.q} actions={<AIBadge />}>
            <div className="text-sm whitespace-pre-wrap">{t.a}</div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Button size="xs" variant="outline" onClick={() => copy(t.a)}><Copy /> Copy</Button>
              <Button size="xs" variant="outline" onClick={() => downloadPost(t.q, t.a, "docx", "AI-assisted answer — check before sharing")}><FileDown /> Word</Button>
              <Button size="xs" variant="outline" onClick={() => downloadPost(t.q, t.a, "pdf", "AI-assisted answer — check before sharing")}><FileDown /> PDF</Button>
            </div>
            <div className="mt-2"><Sources sources={t.sources} /></div>
          </Section>
        ))}
      </div>
    </div>
  );
}

function Write({ disabled }: { disabled: boolean }) {
  const status = useAIStatus();
  const { call, busy } = useAICall();
  const [output, setOutput] = useState("email_draft");
  const [project, setProject] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [instructions, setInstructions] = useState("");
  const [result, setResult] = useState<{ text: string; sources: Source[]; label: string } | null>(null);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Section title="What do you need?">
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <SelectField label="Output" value={output} onChange={(v) => setOutput(v ?? "email_draft")} options={(status.data?.writing_outputs ?? []).map((o) => ({ value: o.key, label: o.label }))} />
            <ProjectPicker value={project} onChange={setProject} noneLabel="No project context" />
          </div>
          <TextAreaField label={output === "email_draft" ? "Paste the email you need to reply to" : "Your text or notes"} value={text} onChange={setText} rows={10} />
          <TextField label="Instructions (optional)" value={instructions} onChange={setInstructions} placeholder="e.g. Keep it short and friendly" />
          <Button disabled={disabled || busy || !text.trim()} onClick={async () => {
            const r = await call<{ text: string; sources: Source[]; label: string }>("/ai/write", { output, text, project_id: project, instructions: instructions || null });
            if (r) setResult(r);
          }}><Sparkles /> {busy ? "Writing…" : "Draft it"}</Button>
          {output === "email_draft" && <p className="text-xs text-muted-foreground">The assistant leaves [placeholders] instead of promising dates or decisions that are not in the workspace. Nothing is ever sent.</p>}
        </div>
      </Section>
      <Section title={result?.label ?? "Draft"} actions={result && <AIBadge />}>
        {!result ? <p className="text-sm text-muted-foreground">Your draft will appear here for you to edit.</p> : (
          <div className="space-y-2">
            <Textarea value={result.text} onChange={(e) => setResult({ ...result, text: e.target.value })} rows={16} aria-label="Draft" />
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => copy(result.text)}><Copy /> Copy</Button>
              <Button size="sm" variant="outline" onClick={() => downloadPost(result.label, result.text, "docx")}><FileDown /> Word</Button>
              <Button size="sm" variant="outline" onClick={() => downloadPost(result.label, result.text, "pdf")}><FileDown /> PDF</Button>
            </div>
            <Sources sources={result.sources} />
          </div>
        )}
      </Section>
    </div>
  );
}

function NotesToTasks({ disabled }: { disabled: boolean }) {
  const { call, busy } = useAICall();
  const [project, setProject] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [created, setCreated] = useState<string[] | null>(null);
  // Read the live pending list so approved, rejected or deferred items disappear.
  const pending = useSuggestions({ status: "pending", project_id: project ?? undefined });
  const items = created === null ? null : (pending.data ?? []).filter((s) => created.includes(s.id));
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Section title="Notes, meeting minutes or a brain dump">
        <div className="space-y-3">
          <ProjectPicker value={project} onChange={setProject} noneLabel="Choose a project" />
          <TextAreaField label="Text" value={text} onChange={setText} rows={12} />
          <Button disabled={disabled || busy || !text.trim() || !project} onClick={async () => {
            const r = await call<Suggestion[]>("/ai/suggest", { text, project_id: project });
            if (r) { setCreated(r.map((x) => x.id)); if (!r.length) toast.info("No new tasks or updates were found."); }
          }}><Sparkles /> {busy ? "Reading…" : "Suggest tasks and updates"}</Button>
          <p className="text-xs text-muted-foreground">Suggestions include priorities, estimates and acceptance criteria where the text supports them. Likely duplicates of existing tasks are flagged.</p>
        </div>
      </Section>
      <Section title="Review suggestions">
        {!items ? <p className="text-sm text-muted-foreground">Nothing is added until you approve it.</p> : items.length === 0 ? <p className="text-sm text-muted-foreground">All suggestions reviewed.</p> : (
          <ul className="space-y-3">{items.map((s) => <SuggestionCard key={s.id} s={s} noteProjectId={project} />)}</ul>
        )}
      </Section>
    </div>
  );
}

function IdeaToProject({ disabled }: { disabled: boolean }) {
  const { call, busy } = useAICall();
  const [idea, setIdea] = useState("");
  const [draft, setDraft] = useState<ProjectDraft | null>(null);
  const [open, setOpen] = useState(false);
  return (
    <Section title="Describe your idea in your own words">
      <div className="max-w-3xl space-y-3">
        <TextAreaField label="Idea" value={idea} onChange={setIdea} rows={8} placeholder="What problem are you solving, for whom, and what would success look like? Rough notes are fine." />
        <Button disabled={disabled || busy || idea.trim().length < 10} onClick={async () => {
          const r = await call<{ draft: ProjectDraft }>("/ai/structure-project", { idea });
          if (r) { setDraft(r.draft); setOpen(true); }
        }}><Sparkles /> {busy ? "Organising…" : "Draft a project brief"}</Button>
        <p className="text-xs text-muted-foreground">The assistant organises your idea into objectives, scope, risks and workstreams. Guesses are listed as assumptions and gaps as open questions. You review and edit everything before the project is created.</p>
        {draft && <Button variant="outline" onClick={() => setOpen(true)}>Review the draft again</Button>}
      </div>
      {draft && <ProjectFormDialog key={JSON.stringify(draft)} draft={draft} open={open} onOpenChange={setOpen} />}
    </Section>
  );
}

function Research({ disabled }: { disabled: boolean }) {
  const { call, busy } = useAICall();
  const create = useCreateKnowledge();
  const router = useRouter();
  const [project, setProject] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [notes, setNotes] = useState("");
  const [draft, setDraft] = useState<{ draft: { title: string; summary: string; limitations: string; fields: Record<string, string> }; sources: Source[] } | null>(null);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Section title="Research question">
        <div className="space-y-3">
          <TextField label="Question" value={question} onChange={setQuestion} placeholder="e.g. Which authentication approach suits a single-origin app?" />
          <TextAreaField label="Your notes, findings or pasted sources" value={notes} onChange={setNotes} rows={10} />
          <ProjectPicker value={project} onChange={setProject} noneLabel="No project" />
          <Button disabled={disabled || busy || question.trim().length < 3} onClick={async () => {
            const r = await call<typeof draft>("/ai/research-draft", { question, notes, project_id: project });
            if (r) setDraft(r);
          }}><Sparkles /> {busy ? "Drafting…" : "Draft research record"}</Button>
          <p className="text-xs text-muted-foreground">The assistant only uses your notes and existing knowledge. It does not browse the web or invent sources.</p>
        </div>
      </Section>
      <Section title={draft?.draft.title ?? "Draft"} actions={draft && <AIBadge />}>
        {!draft ? <p className="text-sm text-muted-foreground">The draft is saved as “AI suggestion — awaiting review” until you verify it.</p> : (
          <div className="space-y-3">
            {draft.draft.summary && <p className="text-sm">{draft.draft.summary}</p>}
            <dl className="space-y-2 text-sm">{Object.entries(draft.draft.fields).map(([k, v]) => <div key={k}><dt className="text-xs font-medium text-muted-foreground capitalize">{k.replace(/_/g, " ")}</dt><dd className="whitespace-pre-wrap">{v}</dd></div>)}</dl>
            <Button disabled={create.isPending} onClick={() => create.mutate({ category: "research", verification: "ai_suggestion", title: draft.draft.title, summary: draft.draft.summary || null,
              limitations: draft.draft.limitations || null, fields: draft.draft.fields, tags: ["ai-draft"], origin_project_id: project }, { onSuccess: (k) => router.push(`/knowledge/${k.id}`) })}>
              Save to Knowledge & Research
            </Button>
            <Sources sources={draft.sources} />
          </div>
        )}
      </Section>
    </div>
  );
}
