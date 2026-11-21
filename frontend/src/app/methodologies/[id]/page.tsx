"use client";
import { Archive, ArchiveRestore, ArrowLeft, Ban, Copy, ListTree, Pencil, Rocket, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use } from "react";
import { PageHeader, QueryView, Section } from "@/components/common";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { AdoptDialog, ClassificationBadge, MetaDialog, STATUS_STYLE, StructureDialog } from "@/components/methodology";
import { Button } from "@/components/ui/button";
import { formatDate, formatDateTime, METHODOLOGY_KIND_LABEL } from "@/lib/format";
import { useMethodology, useMethodologyAction, useMethodologyVersions } from "@/lib/queries-library";
import type { MethodologyDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function MethodologyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const q = useMethodology(id);
  return <QueryView query={q} rows={8}>{(m) => <Detail m={m} />}</QueryView>;
}

const INFO: [keyof MethodologyDetail, string][] = [
  ["purpose", "Purpose"], ["when_to_use", "When to use it"], ["prerequisites", "Prerequisites"], ["tools", "Tools"],
  ["dependencies", "Dependencies"], ["common_risks", "Common risks"], ["completion_criteria", "Completion criteria"], ["limitations", "Limitations"],
];

function Detail({ m }: { m: MethodologyDetail }) {
  const act = useMethodologyAction(m.id);
  const router = useRouter();
  const general = m.deliverables.filter((d) => !d.stage_id);
  return (
    <>
      <Link href="/methodologies" className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="size-4" /> Methodologies & Playbooks</Link>
      <PageHeader title={m.name}
        description={<span className="flex flex-wrap items-center gap-2">{METHODOLOGY_KIND_LABEL[m.kind]} · version {m.version}
          <span className={cn("rounded px-1.5 py-0.5 text-xs font-medium capitalize", STATUS_STYLE[m.status])}>{m.status}</span>
          {m.origin_project_name && <>· derived from <Link className="underline" href={`/projects/${m.origin_project_id}`}>{m.origin_project_name}</Link></>}</span>}
        actions={<>
          <AdoptDialog methodology={m} trigger={<Button disabled={!!m.archived_at || m.stages.length === 0}><Rocket /> Adopt into a project</Button>} />
          <MetaDialog m={m} trigger={<Button variant="outline"><Pencil /> Details</Button>} />
          <StructureDialog m={m} trigger={<Button variant="outline"><ListTree /> Stages</Button>} />
          {m.status === "draft" && <Button variant="outline" onClick={() => act.mutate({ path: "/publish", body: {}, success: "Published." })}><Upload /> Publish</Button>}
          {m.status === "published" && <Button variant="outline" onClick={() => act.mutate({ path: "/deprecate", success: "Marked as deprecated." })}><Ban /> Deprecate</Button>}
          <Button variant="outline" onClick={() => act.mutate({ path: "/duplicate", body: { name: `${m.name} (adapted)` }, success: "Copied as a new draft." }, { onSuccess: (c) => router.push(`/methodologies/${c.id}`) })}><Copy /> Duplicate</Button>
          <Button variant="outline" aria-label={m.archived_at ? "Restore" : "Archive"} onClick={() => act.mutate({ path: m.archived_at ? "/restore" : "/archive" })}>{m.archived_at ? <ArchiveRestore /> : <Archive />}</Button>
          {m.adoption_count === 0 && <ConfirmDialog trigger={<Button variant="destructive" aria-label="Delete methodology"><Trash2 /></Button>}
            title="Delete this methodology?" description="It has not been adopted by any project. This cannot be undone."
            onConfirm={() => act.mutate({ method: "DELETE", query: { confirm: true } as never, success: "Deleted." }, { onSuccess: () => router.push("/methodologies") })} />}
        </>} />
      {m.status === "draft" && <p className="mb-4 rounded-lg bg-warning/10 px-3 py-2 text-sm">Draft — review it before relying on it. {m.origin_project_name && "It was generated from a project, so check for project-specific or confidential details."}</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {m.stages.length === 0 ? (
            <Section title="Stages"><p className="text-sm text-muted-foreground">No stages yet. Use “Stages” above to add them.</p></Section>
          ) : m.stages.map((s, i) => {
            const ds = m.deliverables.filter((d) => d.stage_id === s.id);
            return (
              <Section key={s.id} title={`${i + 1}. ${s.name}`}>
                {s.description && <p className="mb-2 text-sm text-muted-foreground">{s.description}</p>}
                <ol className="space-y-2">
                  {s.activities.map((a) => (
                    <li key={a.id} className="rounded-lg border px-3 py-2 text-sm">
                      <p className="font-medium">{a.title}</p>
                      {a.instructions && <p className="text-muted-foreground whitespace-pre-wrap">{a.instructions}</p>}
                      {a.expected_output && <p className="text-xs"><span className="text-muted-foreground">Expected output: </span>{a.expected_output}</p>}
                    </li>
                  ))}
                </ol>
                {s.validation_criteria && <p className="mt-2 text-xs"><span className="text-muted-foreground">Validation: </span>{s.validation_criteria}</p>}
                {ds.length > 0 && <div className="mt-3 flex flex-wrap gap-2 text-sm">{ds.map((d) => <span key={d.id} className="flex items-center gap-1.5 rounded-md border px-2 py-1">{d.name} <ClassificationBadge value={d.classification} /></span>)}</div>}
              </Section>
            );
          })}
          {general.length > 0 && (
            <Section title="Deliverables for the whole methodology">
              <div className="flex flex-wrap gap-2 text-sm">{general.map((d) => <span key={d.id} className="flex items-center gap-1.5 rounded-md border px-2 py-1">{d.name} <ClassificationBadge value={d.classification} /></span>)}</div>
            </Section>
          )}
        </div>
        <div className="space-y-4">
          <Section title="About">
            <dl className="space-y-3 text-sm">
              {INFO.filter(([k]) => m[k]).map(([k, label]) => <div key={k}><dt className="text-xs font-medium text-muted-foreground">{label}</dt><dd className="whitespace-pre-wrap">{String(m[k])}</dd></div>)}
              {INFO.every(([k]) => !m[k]) && <p className="text-muted-foreground">No details yet.</p>}
            </dl>
          </Section>
          <Section title={`Used in ${m.adoptions.length} project(s)`}>
            {m.adoptions.length === 0 ? <p className="text-sm text-muted-foreground">Not adopted yet.</p> : (
              <ul className="space-y-1.5 text-sm">{m.adoptions.map((a) => <li key={a.id}><Link className="hover:underline" href={`/projects/${a.project_id}`}>{a.project_name}</Link> <span className="text-xs text-muted-foreground">· v{a.methodology_version}, {formatDate(a.adopted_at.slice(0, 10))}</span></li>)}</ul>
            )}
          </Section>
          <Versions id={m.id} />
        </div>
      </div>
    </>
  );
}

function Versions({ id }: { id: string }) {
  const q = useMethodologyVersions(id);
  return (
    <Section title="Version history">
      {(q.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No earlier versions.</p> : (
        <ul className="space-y-1.5 text-sm">
          {(q.data ?? []).map((v) => <li key={v.version}><strong>v{v.version}</strong> <span className="text-xs text-muted-foreground">replaced {formatDateTime(v.created_at)}{v.change_note && ` — ${v.change_note}`}</span></li>)}
        </ul>
      )}
    </Section>
  );
}
