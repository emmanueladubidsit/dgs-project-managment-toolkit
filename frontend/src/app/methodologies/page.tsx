"use client";
import { FolderInput, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { EmptyState, PageHeader, QueryView } from "@/components/common";
import { FromProjectDialog, NewMethodologyDialog, STATUS_STYLE } from "@/components/methodology";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { METHODOLOGY_KIND_LABEL } from "@/lib/format";
import { useMethodologies } from "@/lib/queries-library";
import { cn } from "@/lib/utils";

export default function MethodologiesPage() {
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("all");
  const list = useMethodologies({ q: q || undefined, kind: kind === "all" ? undefined : kind });
  return (
    <>
      <PageHeader title="Methodologies & Playbooks" description="Reusable ways of working: stages, activities and expected deliverables you can adopt into any project."
        actions={<>
          <FromProjectDialog trigger={<Button variant="outline"><FolderInput /> Create from a project</Button>} />
          <NewMethodologyDialog trigger={<Button><Plus /> New methodology</Button>} />
        </>} />
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input className="pl-8" placeholder="Search the library…" aria-label="Search methodologies" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <Select value={kind} onValueChange={setKind}>
          <SelectTrigger className="w-44" aria-label="Type"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {Object.entries(METHODOLOGY_KIND_LABEL).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <QueryView query={list}>
        {(items) => items.length === 0 ? (
          <EmptyState title={q || kind !== "all" ? "Nothing matches" : "The library is empty"}
            description={q || kind !== "all" ? "Try a different search." : "Run `uv run python -m app.seed` in backend/ to load the starter library, or create your own."} />
        ) : (
          <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {items.map((m) => (
              <li key={m.id} className="flex flex-col rounded-xl border bg-card p-4 transition hover:border-primary/40">
                <div className="mb-1 flex items-center justify-between gap-2 text-xs">
                  <span className="font-medium tracking-wide text-primary uppercase">{METHODOLOGY_KIND_LABEL[m.kind]}</span>
                  <span className={cn("rounded px-1.5 py-0.5 font-medium capitalize", STATUS_STYLE[m.status])}>{m.status}</span>
                </div>
                <Link href={`/methodologies/${m.id}`} className="font-semibold hover:underline">{m.name}</Link>
                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{m.purpose ?? "No purpose written yet."}</p>
                <p className="mt-auto pt-3 text-xs text-muted-foreground">
                  {m.stage_count} stage(s) · {m.activity_count} activities · {m.deliverable_count} deliverable(s) · v{m.version}
                  {m.adoption_count > 0 && <> · used in {m.adoption_count} project(s)</>}
                  {m.origin_project_name && <> · from {m.origin_project_name}</>}
                </p>
              </li>
            ))}
          </ul>
        )}
      </QueryView>
    </>
  );
}
