"use client";
import { Plus, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { EmptyState, PageHeader, QueryView } from "@/components/common";
import { KnowledgeFormDialog, VerificationBadge } from "@/components/knowledge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDate, VERIFICATION_LABEL } from "@/lib/format";
import { useProjects } from "@/lib/queries";
import { useKnowledgeList, useKnowledgeTemplates } from "@/lib/queries-library";

const ALL = "all";

export default function KnowledgePage() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState(ALL);
  const [verification, setVerification] = useState(ALL);
  const [project, setProject] = useState(ALL);
  const templates = useKnowledgeTemplates();
  const projects = useProjects();
  const list = useKnowledgeList({
    q: q || undefined,
    category: category === ALL ? undefined : [category],
    verification: verification === ALL ? undefined : [verification],
    project_id: project === ALL ? undefined : project,
  });
  const label = (c: string) => templates.data?.find((t) => t.category === c)?.label ?? c;
  const filtered = !!q || category !== ALL || verification !== ALL || project !== ALL;
  return (
    <>
      <PageHeader title="Knowledge & Research" description="Research, guides, decisions and lessons you can reuse across projects — with clear verification status."
        actions={<KnowledgeFormDialog trigger={<Button><Plus /> New item</Button>} />} />
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input className="pl-8" placeholder="Search titles, content and fields…" aria-label="Search knowledge" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-52" aria-label="Category"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All categories</SelectItem>
            {(templates.data ?? []).map((t) => <SelectItem key={t.category} value={t.category}>{t.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={verification} onValueChange={setVerification}>
          <SelectTrigger className="w-60" aria-label="Verification status"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Any verification status</SelectItem>
            {Object.entries(VERIFICATION_LABEL).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={project} onValueChange={setProject}>
          <SelectTrigger className="w-48" aria-label="Project"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All projects</SelectItem>
            {(projects.data ?? []).map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <QueryView query={list}>
        {(items) => items.length === 0 ? (
          filtered ? <EmptyState title="Nothing matches" description="Try a different search or filter." />
            : <EmptyState title="No knowledge yet" description="Capture research, troubleshooting guides, decisions and lessons learned. You can also promote any recorded update from a project’s “Decisions & updates” tab."
              action={<KnowledgeFormDialog trigger={<Button><Plus /> Create the first item</Button>} />} />
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {items.map((k) => (
              <li key={k.id} className="flex flex-col rounded-xl border bg-card p-4 transition hover:border-primary/40">
                <p className="mb-1 text-xs font-medium tracking-wide text-primary uppercase">{label(k.category)}</p>
                <Link href={`/knowledge/${k.id}`} className="font-semibold hover:underline">{k.title}</Link>
                {k.summary && <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{k.summary}</p>}
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  <VerificationBadge value={k.verification} />
                  {k.tags.map((t) => <span key={t} className="rounded bg-muted px-1.5 py-0.5 text-xs">{t}</span>)}
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  {k.projects.length > 0 ? k.projects.map((p) => `${p.role === "origin" ? "From" : p.role === "reused" ? "Reused in" : "Related to"} ${p.project_name}`).join(" · ") + " · " : ""}
                  v{k.version} · updated {formatDate(k.updated_at.slice(0, 10))}
                </p>
              </li>
            ))}
          </ul>
        )}
      </QueryView>
    </>
  );
}
