"use client";
import { FolderPlus, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { EmptyState, ExplainedProgress, PageHeader, PriorityBadge, QueryView } from "@/components/common";
import { ProjectFormDialog } from "@/components/project-form-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatShort, PROJECT_STATUS_LABEL } from "@/lib/format";
import { useProjects } from "@/lib/queries";
import type { ProjectStatus } from "@/lib/types";

export default function ProjectsPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string>("open");
  const query = useProjects({
    q: q || undefined,
    status: status === "open" || status === "all" ? undefined : status,
    include_archived: status === "all",
  });
  return (
    <>
      <PageHeader title="Projects" description="Every project, its stage and how far it has progressed."
        actions={<ProjectFormDialog trigger={<Button><FolderPlus /> New project</Button>} />} />
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input className="pl-8" placeholder="Search projects…" aria-label="Search projects" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-48" aria-label="Filter by status"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="open">All except archived</SelectItem>
            {(Object.keys(PROJECT_STATUS_LABEL) as ProjectStatus[]).map((s) => <SelectItem key={s} value={s}>{PROJECT_STATUS_LABEL[s]}</SelectItem>)}
            <SelectItem value="all">Everything</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <QueryView query={query}>
        {(projects) => projects.length === 0 ? (
          q || status !== "open"
            ? <EmptyState title="No projects match" description="Try a different search or status filter." />
            : <EmptyState title="No projects yet" description="A project holds its objectives, workstreams, milestones, tasks and history."
              action={<ProjectFormDialog trigger={<Button><FolderPlus /> Create a project</Button>} />} />
        ) : (
          <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {projects.map((p) => {
              const total = Object.values(p.task_counts).reduce((a, b) => a + (b ?? 0), 0);
              return (
                <li key={p.id} className="flex flex-col rounded-xl border bg-card p-4 transition hover:border-primary/40">
                  <div className="mb-1 flex items-start justify-between gap-2">
                    <Link href={`/projects/${p.id}`} className="font-semibold hover:underline">{p.name}</Link>
                    <PriorityBadge priority={p.priority} />
                  </div>
                  <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">{p.description || "No description yet."}</p>
                  <div className="mt-auto space-y-2">
                    <div className="flex flex-wrap gap-1.5 text-xs">
                      <span className="rounded bg-muted px-1.5 py-0.5">{PROJECT_STATUS_LABEL[p.status]}</span>
                      {p.stage && <span className="rounded bg-primary/10 px-1.5 py-0.5 text-primary">{p.stage.name}</span>}
                      {p.target_date && <span className="rounded bg-muted px-1.5 py-0.5">Target {formatShort(p.target_date)}</span>}
                    </div>
                    <ExplainedProgress progress={p.progress} />
                    <p className="text-xs text-muted-foreground">
                      {total} task(s) · {p.task_counts.completed ?? 0} completed
                      {p.overdue_count > 0 && <span className="text-destructive"> · {p.overdue_count} overdue</span>}
                      {p.blocked_count > 0 && <span className="text-status-blocked"> · {p.blocked_count} blocked</span>}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </QueryView>
    </>
  );
}
