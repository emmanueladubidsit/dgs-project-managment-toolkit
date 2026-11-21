"use client";
import { ArrowLeft, Copy, Lightbulb, Save, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { toast } from "sonner";
import { PageHeader, QueryView, Section } from "@/components/common";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { SelectField, TextField } from "@/components/form-fields";
import { useAICall, useAIStatus } from "@/components/ai";
import { SuggestionCard } from "@/components/suggestions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime, todayISO, WORKLOG_KIND_LABEL } from "@/lib/format";
import { useProjects } from "@/lib/queries";
import {
  useDeleteAudio, useDeleteVoiceNote, useExtractSuggestions, useSaveAsUpdate, useSuggestions,
  useTransform, useUpdateVoiceNote, useVoiceNote, useVoiceStatus,
} from "@/lib/queries-library";
import type { VoiceNote } from "@/lib/types";

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
  const ai = useAIStatus();
  const { call, busy } = useAICall();
  const aiReady = !!ai.data?.ready;
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
            {outputs.filter((o) => o.needs_ai).map((o) => <SelectItem key={o.key} value={o.key}>{o.label} ({aiReady ? "AI" : "needs AI"})</SelectItem>)}
          </SelectContent>
        </Select>
        <Button disabled={!text.trim() || transform.isPending || busy || (chosen?.needs_ai && !aiReady)} onClick={async () => {
          if (chosen?.needs_ai) {
            const r = await call<{ text: string }>("/ai/write", { output, text, project_id: note.project_id });
            if (r) setResult(r.text);
          } else transform.mutate({ output, text }, { onSuccess: (r) => setResult(r.text ?? "") });
        }}>{busy ? "Writing…" : "Generate"}</Button>
      </div>
      {chosen?.needs_ai && aiReady ? (
        <p className="mt-2 text-xs text-muted-foreground"><Sparkles className="mr-1 inline size-3" aria-hidden />Written by your AI assistant{note.project_id ? " using this note’s project context" : ""}. It is told not to invent facts or commitments — check the draft before using it.</p>
      ) : chosen?.needs_ai ? (
        <p className="mt-3 flex items-start gap-2 rounded-lg bg-muted/60 px-3 py-2 text-sm"><Sparkles className="mt-0.5 size-4 shrink-0" aria-hidden />
          {chosen.label} needs the AI assistant, which is off. It is never faked: the workspace does not invent wording, commitments or facts. <Link href="/admin" className="underline">Turn the assistant on</Link>, or use the other outputs, which work without AI.</p>
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
  const ai = useAIStatus();
  const { call, busy } = useAICall();
  const pending = useSuggestions({ source_id: note.id, status: "pending" });
  const deferred = useSuggestions({ source_id: note.id, status: "deferred" });
  const extract = useExtractSuggestions(note.id);
  const items = [...(pending.data ?? []), ...(deferred.data ?? [])];
  return (
    <Section title="Suggested tasks and updates" actions={<div className="flex gap-2">
      <Button size="sm" variant={ai.data?.ready ? "outline" : "default"} onClick={() => extract.mutate(undefined)} disabled={extract.isPending}><Lightbulb /> Find suggestions</Button>
      {ai.data?.ready && <Button size="sm" disabled={busy} onClick={async () => {
        const r = await call<unknown[]>("/ai/suggest", { voice_note_id: note.id });
        if (r && !r.length) toast.info("No new suggestions found.");
      }}><Sparkles /> {busy ? "Reading…" : "Find with AI"}</Button>}
    </div>}>
      <p className="mb-3 text-xs text-muted-foreground">“Find suggestions” uses simple phrase rules (“we need to…”, “we decided…”){ai.data?.ready ? "; “Find with AI” reads the whole note and adds priorities and estimates" : ""}. Nothing is added until you approve it, and likely duplicates of existing tasks are flagged.</p>
      {items.length === 0 ? <p className="text-sm text-muted-foreground">No suggestions waiting for review.</p> : (
        <ul className="space-y-3">{items.map((s) => <SuggestionCard key={s.id} s={s} noteProjectId={note.project_id} />)}</ul>
      )}
    </Section>
  );
}
