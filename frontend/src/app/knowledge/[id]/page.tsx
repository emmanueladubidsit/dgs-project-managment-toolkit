"use client";
import { Archive, ArchiveRestore, ArrowLeft, Pencil, RotateCcw, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { ExportMenu } from "@/components/ai";
import { PageHeader, QueryView, Section } from "@/components/common";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { KnowledgeFormDialog, VerificationBadge, VerificationNotice } from "@/components/knowledge";
import { useOpenTask } from "@/components/task-sheet";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDateTime, LINK_ROLE_LABEL, RELATION_LABEL } from "@/lib/format";
import { useProjects, useTasks } from "@/lib/queries";
import {
  useDeleteKnowledge, useDeleteRelation, useKnowledge, useKnowledgeAction, useKnowledgeList, useKnowledgeTemplates,
  useKnowledgeVersions,
} from "@/lib/queries-library";
import type { KnowledgeDetail } from "@/lib/types";

export default function KnowledgeItemPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const q = useKnowledge(id);
  return <QueryView query={q} rows={8}>{(k) => <Item item={k} />}</QueryView>;
}

function Item({ item: k }: { item: KnowledgeDetail }) {
  const templates = useKnowledgeTemplates();
  const act = useKnowledgeAction(k.id);
  const del = useDeleteKnowledge();
  const router = useRouter();
  const template = templates.data?.find((t) => t.category === k.category);
  const fieldRows = (template?.fields ?? []).filter((f) => k.fields[f.key]);
  return (
    <>
      <Link href="/knowledge" className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="size-4" /> Knowledge & Research</Link>
      <PageHeader title={k.title}
        description={<span className="flex flex-wrap items-center gap-2">{template?.label} · version {k.version} <VerificationBadge value={k.verification} /></span>}
        actions={<>
          <ExportMenu items={[
            { label: "Word document", href: `/api/export/knowledge/${k.id}?format=docx` },
            { label: "PDF", href: `/api/export/knowledge/${k.id}?format=pdf` },
          ]} />
          <KnowledgeFormDialog item={k} trigger={<Button variant="outline"><Pencil /> Edit</Button>} />
          <Button variant="outline" onClick={() => act.mutate({ path: k.archived_at ? "/restore" : "/archive" })}>
            {k.archived_at ? <><ArchiveRestore /> Restore</> : <><Archive /> Archive</>}
          </Button>
          <ConfirmDialog trigger={<Button variant="destructive" aria-label="Delete knowledge item"><Trash2 /></Button>}
            title="Delete this knowledge item?" description="This permanently removes it and its version history. Archiving keeps it but hides it."
            onConfirm={() => del.mutate(k.id, { onSuccess: () => router.push("/knowledge") })} />
        </>} />
      <div className="mb-4"><VerificationNotice value={k.verification} /></div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {k.summary && <Section title="Summary"><p className="text-sm whitespace-pre-wrap">{k.summary}</p></Section>}
          {fieldRows.length > 0 && (
            <Section title={template?.label ?? "Details"}>
              <dl className="space-y-3">
                {fieldRows.map((f) => (
                  <div key={f.key}>
                    <dt className="text-xs font-medium text-muted-foreground">{f.label}</dt>
                    <dd className="text-sm whitespace-pre-wrap">{k.fields[f.key]}</dd>
                  </div>
                ))}
              </dl>
            </Section>
          )}
          {k.content && <Section title={fieldRows.length ? "Additional notes" : "Content"}><div className="text-sm whitespace-pre-wrap">{k.content}</div></Section>}
          {(k.sources || k.limitations || k.reuse_notes) && (
            <Section title="Sources, limitations and reuse">
              <dl className="space-y-3 text-sm">
                {k.sources && <div><dt className="text-xs font-medium text-muted-foreground">Sources and references</dt><dd className="break-words whitespace-pre-wrap">{k.sources}</dd></div>}
                {k.limitations && <div><dt className="text-xs font-medium text-muted-foreground">Limitations</dt><dd className="whitespace-pre-wrap">{k.limitations}</dd></div>}
                {k.reuse_notes && <div><dt className="text-xs font-medium text-muted-foreground">Before reusing</dt><dd className="whitespace-pre-wrap">{k.reuse_notes}</dd></div>}
              </dl>
            </Section>
          )}
          <Versions id={k.id} current={k.version} />
        </div>
        <div className="space-y-4">
          <Projects item={k} />
          <Tasks item={k} />
          <Relations item={k} />
          {k.tags.length > 0 && <Section title="Tags"><div className="flex flex-wrap gap-1.5">{k.tags.map((t) => <span key={t} className="rounded bg-muted px-1.5 py-0.5 text-xs">{t}</span>)}</div></Section>}
        </div>
      </div>
    </>
  );
}

function Projects({ item: k }: { item: KnowledgeDetail }) {
  const projects = useProjects();
  const act = useKnowledgeAction(k.id);
  const [role, setRole] = useState("reused");
  const linked = new Set(k.projects.map((p) => p.project_id));
  return (
    <Section title="Projects">
      {k.projects.length === 0 ? <p className="mb-2 text-sm text-muted-foreground">Not linked to any project.</p> : (
        <ul className="mb-3 space-y-1.5">
          {k.projects.map((p) => (
            <li key={p.project_id} className="flex items-center justify-between gap-2 text-sm">
              <span><span className="text-xs text-muted-foreground">{LINK_ROLE_LABEL[p.role]}: </span><Link className="hover:underline" href={`/projects/${p.project_id}`}>{p.project_name}</Link></span>
              <Button size="icon-xs" variant="ghost" aria-label={`Unlink ${p.project_name}`} onClick={() => act.mutate({ path: `/projects/${p.project_id}`, method: "DELETE" })}><X /></Button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger className="w-28" aria-label="Link role"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="reused">Reused in</SelectItem>
            <SelectItem value="related">Related</SelectItem>
            {!k.projects.some((p) => p.role === "origin") && <SelectItem value="origin">Origin</SelectItem>}
          </SelectContent>
        </Select>
        <Select value="" onValueChange={(pid) => act.mutate({ path: "/projects", body: { project_id: pid, role } })}>
          <SelectTrigger className="flex-1" aria-label="Link a project"><SelectValue placeholder="Link a project…" /></SelectTrigger>
          <SelectContent>{(projects.data ?? []).filter((p) => !linked.has(p.id)).map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      {role === "reused" && k.reuse_notes && <p className="mt-2 text-xs text-warning">Before reusing: {k.reuse_notes}</p>}
    </Section>
  );
}

function Tasks({ item: k }: { item: KnowledgeDetail }) {
  const tasks = useTasks({ sort: "updated" });
  const act = useKnowledgeAction(k.id);
  const openTask = useOpenTask();
  const linked = new Set(k.tasks.map((t) => t.task_id));
  return (
    <Section title="Tasks">
      {k.tasks.length === 0 ? <p className="mb-2 text-sm text-muted-foreground">Not linked to any task.</p> : (
        <ul className="mb-3 space-y-1.5">
          {k.tasks.map((t) => (
            <li key={t.task_id} className="flex items-center justify-between gap-2 text-sm">
              <button className="truncate text-left hover:underline" onClick={() => openTask(t.task_id)}>{t.task_title} <span className="text-xs text-muted-foreground">· {t.project_name}</span></button>
              <Button size="icon-xs" variant="ghost" aria-label={`Unlink ${t.task_title}`} onClick={() => act.mutate({ path: `/tasks/${t.task_id}`, method: "DELETE" })}><X /></Button>
            </li>
          ))}
        </ul>
      )}
      <Select value="" onValueChange={(tid) => act.mutate({ path: "/tasks", body: { task_id: tid } })}>
        <SelectTrigger className="w-full" aria-label="Link a task"><SelectValue placeholder="Link a task…" /></SelectTrigger>
        <SelectContent>{(tasks.data ?? []).filter((t) => !linked.has(t.id)).slice(0, 100).map((t) => <SelectItem key={t.id} value={t.id}>{t.title} — {t.project_name}</SelectItem>)}</SelectContent>
      </Select>
    </Section>
  );
}

function Relations({ item: k }: { item: KnowledgeDetail }) {
  const all = useKnowledgeList({});
  const act = useKnowledgeAction(k.id);
  const del = useDeleteRelation();
  const [kind, setKind] = useState("evidence_for");
  return (
    <Section title="Related knowledge">
      {k.relations.length === 0 ? <p className="mb-2 text-sm text-muted-foreground">No relationships yet. Link research as evidence for a decision, or mark what this supersedes.</p> : (
        <ul className="mb-3 space-y-1.5">
          {k.relations.map((r) => (
            <li key={r.id} className="flex items-center justify-between gap-2 text-sm">
              <span className="min-w-0">
                <span className="text-xs text-muted-foreground">{r.direction === "outgoing" ? RELATION_LABEL[r.kind] : r.kind === "evidence_for" ? "Supported by" : r.kind === "supersedes" ? "Superseded by" : "Related to"}: </span>
                <Link className="hover:underline" href={`/knowledge/${r.other_id}`}>{r.other_title}</Link>
              </span>
              <Button size="icon-xs" variant="ghost" aria-label="Remove relationship" onClick={() => del.mutate(r.id)}><X /></Button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <Select value={kind} onValueChange={setKind}>
          <SelectTrigger className="w-32" aria-label="Relationship"><SelectValue /></SelectTrigger>
          <SelectContent>{Object.entries(RELATION_LABEL).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
        </Select>
        <Select value="" onValueChange={(to) => act.mutate({ path: "/relations", body: { to_id: to, kind } })}>
          <SelectTrigger className="flex-1" aria-label="Choose related item"><SelectValue placeholder="Choose an item…" /></SelectTrigger>
          <SelectContent>{(all.data ?? []).filter((x) => x.id !== k.id).map((x) => <SelectItem key={x.id} value={x.id}>{x.title}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      {kind === "supersedes" && <p className="mt-2 text-xs text-muted-foreground">The superseded item will be marked “Outdated”.</p>}
    </Section>
  );
}

function Versions({ id, current }: { id: string; current: number }) {
  const q = useKnowledgeVersions(id);
  const act = useKnowledgeAction(id);
  return (
    <Section title={`Version history (current: v${current})`}>
      {(q.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No earlier versions.</p> : (
        <ul className="divide-y">
          {(q.data ?? []).map((v) => (
            <li key={v.version} className="flex items-center justify-between gap-2 py-2 text-sm">
              <span>
                <strong>v{v.version}</strong> · {String(v.snapshot.title)}
                <span className="block text-xs text-muted-foreground">Replaced {formatDateTime(v.created_at)}{v.change_note && ` — ${v.change_note}`}</span>
              </span>
              <ConfirmDialog trigger={<Button size="sm" variant="ghost"><RotateCcw /> Restore</Button>} confirmLabel="Restore" destructive={false}
                title={`Restore version ${v.version}?`} description="The current content is kept in the history; the restored text becomes a new version."
                onConfirm={() => act.mutate({ path: `/restore-version/${v.version}` })} />
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
