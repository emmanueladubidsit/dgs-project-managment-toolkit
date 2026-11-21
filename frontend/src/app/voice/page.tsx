"use client";
import { FileAudio, ShieldCheck, Type } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { EmptyState, PageHeader, QueryView, Section } from "@/components/common";
import { SelectField, TextAreaField, TextField } from "@/components/form-fields";
import { Recorder } from "@/components/recorder";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/format";
import { useProjects } from "@/lib/queries";
import { useCreateTextNote, useUploadRecording, useVoiceNotes, useVoiceStatus } from "@/lib/queries-library";

export default function VoicePage() {
  const status = useVoiceStatus();
  const notes = useVoiceNotes();
  const projects = useProjects();
  const upload = useUploadRecording();
  const createText = useCreateTextNote();
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [project, setProject] = useState<string | null>(null);
  const [text, setText] = useState("");
  const projectOptions = (projects.data ?? []).map((p) => ({ value: p.id, label: p.name }));
  const s = status.data;
  return (
    <>
      <PageHeader title="Voice & Writing" description="Speak or paste, then clean it up, structure it, and turn it into updates and suggested tasks — reviewed by you before anything changes." />
      {s && (
        <div className="mb-4 flex flex-wrap gap-x-6 gap-y-1 rounded-xl border bg-muted/40 px-4 py-3 text-sm" role="status">
          <span className="flex items-center gap-1.5"><FileAudio className="size-4" aria-hidden />{s.available ? s.message : `Transcription unavailable — ${s.message}`}</span>
          <span className="flex items-center gap-1.5"><ShieldCheck className="size-4" aria-hidden />{s.retention_message}</span>
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Record">
          <div className="mb-3 grid gap-3 sm:grid-cols-2">
            <TextField label="Title" value={title} onChange={setTitle} placeholder="e.g. Monday stand-up" />
            <SelectField label="Project" value={project} onChange={setProject} noneLabel="No project" options={projectOptions} />
          </div>
          <Recorder busy={upload.isPending} disabledReason={s && !s.available ? "Recording needs a transcription provider. You can still type or paste text." : undefined}
            onTranscribe={(blob) => upload.mutate({ blob, title: title.trim() || "Voice note", projectId: project }, { onSuccess: (n) => router.push(`/voice/${n.id}`) })} />
        </Section>
        <Section title={<span className="flex items-center gap-1.5"><Type className="size-4" aria-hidden /> Type or paste</span>}>
          <form className="space-y-3" onSubmit={(e) => {
            e.preventDefault();
            createText.mutate({ title: title.trim() || "Text note", text, project_id: project }, { onSuccess: (n) => router.push(`/voice/${n.id}`) });
          }}>
            <TextAreaField label="Text" value={text} onChange={setText} rows={7} placeholder="Notes, a rough update, or an email you need to respond to…" />
            <Button type="submit" disabled={!text.trim() || createText.isPending}>Continue</Button>
          </form>
          <p className="mt-2 text-xs text-muted-foreground">Uses the title and project from the left.</p>
        </Section>
      </div>
      <Section title="Recent notes" className="mt-4">
        <QueryView query={notes}>
          {(list) => list.length === 0 ? <EmptyState title="No notes yet" description="Record something or paste some text to get started." /> : (
            <ul className="divide-y">
              {list.map((n) => (
                <li key={n.id} className="flex items-center justify-between gap-2 py-2">
                  <div className="min-w-0">
                    <Link href={`/voice/${n.id}`} className="block truncate text-sm font-medium hover:underline">{n.title}</Link>
                    <p className="truncate text-xs text-muted-foreground">
                      {n.source === "recording" ? "Recording" : "Text"}{n.project_name && ` · ${n.project_name}`} · {formatDateTime(n.created_at)} · {(n.transcript_edited ?? n.transcript_raw ?? "").slice(0, 80)}
                    </p>
                  </div>
                  {n.pending_suggestions > 0 && <span className="shrink-0 rounded bg-warning/15 px-1.5 py-0.5 text-xs text-warning">{n.pending_suggestions} to review</span>}
                </li>
              ))}
            </ul>
          )}
        </QueryView>
      </Section>
    </>
  );
}
