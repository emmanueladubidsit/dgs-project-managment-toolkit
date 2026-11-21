"use client";
import { AlertTriangle, ArrowLeft, Check, Clock, Copy, Lightbulb, Save, Sparkles, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { toast } from "sonner";
import { PageHeader, QueryView, Section } from "@/components/common";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { SelectField, TextField } from "@/components/form-fields";
import { useOpenTask } from "@/components/task-sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime, PRIORITIES, PRIORITY_LABEL, todayISO, WORKLOG_KIND_LABEL } from "@/lib/format";
import { useProjects } from "@/lib/queries";
import {
  useDeleteAudio, useDeleteVoiceNote, useExtractSuggestions, useSaveAsUpdate, useSuggestionAction, useSuggestions,
  useTransform, useUpdateVoiceNote, useVoiceNote, useVoiceStatus,
} from "@/lib/queries-library";
import type { Suggestion, VoiceNote } from "@/lib/types";

const KIND_LABEL = { task: "Task", blocker: "Blocker", decision: "Decision", progress: "Progress" };

export default function VoiceNotePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const q = useVoiceNote(id);
  return <QueryView query={q} rows={8}>{(n) => <Note key={n.updated_at} note={n} />}</QueryView>;
}

function Note({ note: n }: { note: VoiceNote }) {
  const projects = useProjects();
  const save = useUpdateVoiceNote(n.id);
  const delAudio = useDeleteAudio(n.id);
  const del = useDeleteVoiceNote();
  const router = useRouter();
  const [title, setTitle] = useState(n.title);
  const [text, setText] = useState(n.transcript_edited ?? n.transcript_raw ?? "");
  const dirty = title !== n.title || text !== (n.transcript_edited ?? n.transcript_raw ?? "");
  return (
    <>
      <Link href="/voice" className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="size-4" /> Voice & Writing</Link>
      <PageHeader title={n.title} description={<>{n.source === "recording" ? `Recording${n.duration_seconds ? ` · ${Math.round(n.duration_seconds)}s` : ""} · transcribed by ${n.transcription_provider}` : "Typed or pasted text"} · {formatDateTime(n.created_at)}</>}
        actions={<ConfirmDialog trigger={<Button variant="destructive"><Trash2 /> Delete note</Button>} title="Delete this note?"
          description="The note, its recording (if kept) and its pending suggestions are deleted. Tasks and updates already approved are kept."
          onConfirm={() => del.mutate(n.id, { onSuccess: () => router.push("/voice") })} />} />
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          <Section title="Transcript">
            <div className="mb-3 grid gap-3 sm:grid-cols-2">
              <TextField label="Title" value={title} onChange={setTitle} />
              <SelectField label="Project" value={n.project_id} onChange={(v) => save.mutate({ project_id: v })} noneLabel="No project"
                options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
            </div>
            <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={12} aria-label="Transcript" />
            <div className="mt-2 flex flex-wrap gap-2">
              <Button size="sm" disabled={!dirty || save.isPending} onClick={() => save.mutate({ title: title.trim() || n.title, transcript_edited: text })}><Save /> Save edits</Button>
              {n.transcript_edited !== null && n.transcript_raw && <Button size="sm" variant="ghost" onClick={() => setText(n.transcript_raw ?? "")}>Revert to original</Button>}
            </div>
          </Section>
          {n.source === "recording" && (
            <Section title="Recording">
              {n.has_audio ? (
                <div className="space-y-2">
                  { }
                  <audio controls src={`/api/voice/notes/${n.id}/audio`} className="w-full" aria-label="Play recording" />
                  <Button size="sm" variant="outline" onClick={() => delAudio.mutate(undefined)}><Trash2 /> Delete recording, keep transcript</Button>
                </div>
              ) : <p className="text-sm text-muted-foreground">The audio was deleted {n.audio_deleted_at ? formatDateTime(n.audio_deleted_at) : ""}. Only the transcript is stored.</p>}
            </Section>
          )}
        </div>
        <div className="space-y-4">
          <WritingTools note={n} text={text} />
          <Suggestions note={n} />
        </div>
      </div>
    </>
  );
}

function WritingTools({ note, text }: { note: VoiceNote; text: string }) {
  const status = useVoiceStatus();
  const transform = useTransform(note.id);
  const saveUpdate = useSaveAsUpdate(note.id);
  const [output, setOutput] = useState("clean_transcript");
  const [result, setResult] = useState("");
  const [kind, setKind] = useState("progress");
  const [date, setDate] = useState(todayISO());
  const outputs = status.data?.outputs ?? [];
  const chosen = outputs.find((o) => o.key === output);
  return (
    <Section title="Writing tools">
      <div className="flex flex-wrap gap-2">
        <Select value={output} onValueChange={(v) => { setOutput(v); setResult(""); }}>
          <SelectTrigger className="w-60" aria-label="Output type"><SelectValue /></SelectTrigger>
          <SelectContent>
            {outputs.filter((o) => !o.needs_ai).map((o) => <SelectItem key={o.key} value={o.key}>{o.label}</SelectItem>)}
            {outputs.filter((o) => o.needs_ai).map((o) => <SelectItem key={o.key} value={o.key}>{o.label} (needs AI)</SelectItem>)}
          </SelectContent>
        </Select>
        <Button disabled={!text.trim() || transform.isPending || chosen?.needs_ai} onClick={() => transform.mutate({ output, text }, { onSuccess: (r) => setResult(r.text ?? "") })}>Generate</Button>
      </div>
      {chosen?.needs_ai ? (
        <p className="mt-3 flex items-start gap-2 rounded-lg bg-muted/60 px-3 py-2 text-sm"><Sparkles className="mt-0.5 size-4 shrink-0" aria-hidden />
          {chosen.label} needs an AI writing provider, which is not configured. It is never faked: the workspace does not invent wording, commitments or facts. The other outputs work without AI.</p>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">Rule-based: removes filler words, fixes spacing and capitalisation, uses British spelling and regroups your own sentences. It does not add anything you did not say.</p>
      )}
      {result && (
        <div className="mt-3 space-y-2">
          <Textarea value={result} onChange={(e) => setResult(e.target.value)} rows={10} className="font-mono text-sm" aria-label="Generated text" />
          <div className="flex flex-wrap items-end gap-2">
            <Button size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(result).then(() => toast.success("Copied."), () => toast.error("Copy blocked by the browser."))}><Copy /> Copy</Button>
            <Select value={kind} onValueChange={setKind}>
              <SelectTrigger className="h-8 w-40" aria-label="Update type"><SelectValue /></SelectTrigger>
              <SelectContent>{Object.entries(WORKLOG_KIND_LABEL).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
            </Select>
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="h-8 w-40" aria-label="Update date" />
            <Button size="sm" onClick={() => saveUpdate.mutate({ kind, entry_date: date, text: result })} disabled={saveUpdate.isPending}><Save /> Save as update</Button>
          </div>
          {!note.project_id && <p className="text-xs text-muted-foreground">Tip: choose a project on the left so the update appears on that project.</p>}
        </div>
      )}
    </Section>
  );
}

function Suggestions({ note }: { note: VoiceNote }) {
  const pending = useSuggestions({ source_id: note.id, status: "pending" });
  const deferred = useSuggestions({ source_id: note.id, status: "deferred" });
  const extract = useExtractSuggestions(note.id);
  const items = [...(pending.data ?? []), ...(deferred.data ?? [])];
  return (
    <Section title="Suggested tasks and updates" actions={<Button size="sm" onClick={() => extract.mutate(undefined)} disabled={extract.isPending}><Lightbulb /> Find suggestions</Button>}>
      <p className="mb-3 text-xs text-muted-foreground">Found by simple rules (“we need to…”, “we decided…”, “blocked on…”). Nothing is added until you approve it, and likely duplicates of existing tasks are flagged.</p>
      {items.length === 0 ? <p className="text-sm text-muted-foreground">No suggestions waiting for review.</p> : (
        <ul className="space-y-3">{items.map((s) => <SuggestionCard key={s.id} s={s} noteProjectId={note.project_id} />)}</ul>
      )}
    </Section>
  );
}

function SuggestionCard({ s, noteProjectId }: { s: Suggestion; noteProjectId: string | null }) {
  const act = useSuggestionAction();
  const projects = useProjects();
  const openTask = useOpenTask();
  const [title, setTitle] = useState(s.payload.title ?? "");
  const [priority, setPriority] = useState(s.payload.priority ?? "medium");
  const [project, setProject] = useState<string | null>(s.project_id ?? noteProjectId);
  const approve = (allow = false) => act.mutate({ id: s.id, action: "approve", body: { title, priority, project_id: project, allow_duplicate: allow, entry_date: todayISO() } });
  return (
    <li className="rounded-lg border p-3">
      <div className="mb-2 flex items-center gap-2 text-xs">
        <span className="rounded bg-primary/10 px-1.5 py-0.5 font-medium text-primary">{KIND_LABEL[s.kind]}</span>
        {s.status === "deferred" && <span className="flex items-center gap-1 text-muted-foreground"><Clock className="size-3" /> Deferred</span>}
      </div>
      {s.kind === "task" ? (
        <div className="space-y-2">
          <Input value={title} onChange={(e) => setTitle(e.target.value)} aria-label="Task title" />
          <div className="grid grid-cols-2 gap-2">
            <Select value={priority} onValueChange={(v) => setPriority(v as never)}>
              <SelectTrigger aria-label="Priority"><SelectValue /></SelectTrigger>
              <SelectContent>{PRIORITIES.map((p) => <SelectItem key={p} value={p}>{PRIORITY_LABEL[p]}</SelectItem>)}</SelectContent>
            </Select>
            <SelectField label="Project" value={project} onChange={setProject} noneLabel="Choose a project" options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
          </div>
        </div>
      ) : <p className="text-sm">{s.evidence}</p>}
      {s.kind === "task" && s.evidence && <p className="mt-2 text-xs text-muted-foreground">From: “{s.evidence}”</p>}
      {s.duplicate_of_task_id && (
        <p className="mt-2 flex items-start gap-1.5 text-xs text-warning"><AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
          Possible duplicate of <button className="underline" onClick={() => openTask(s.duplicate_of_task_id!)}>“{s.duplicate_of_title}”</button>.</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {s.duplicate_of_task_id && s.kind === "task"
          ? <Button size="sm" variant="outline" onClick={() => approve(true)} disabled={!title.trim() || !project}><Check /> Create anyway</Button>
          : <Button size="sm" onClick={() => approve()} disabled={s.kind === "task" && (!title.trim() || !project)}><Check /> {s.kind === "task" ? "Create task" : "Record update"}</Button>}
        <Button size="sm" variant="ghost" onClick={() => act.mutate({ id: s.id, action: "reject" })}><X /> Reject</Button>
        {s.status !== "deferred" && <Button size="sm" variant="ghost" onClick={() => act.mutate({ id: s.id, action: "defer" })}><Clock /> Later</Button>}
      </div>
    </li>
  );
}
