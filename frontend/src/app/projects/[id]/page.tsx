"use client";
import { AlertTriangle, Archive, ArchiveRestore, ArrowLeft, Info, MessageSquarePlus, Pencil, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { EmptyState, ExplainedProgress, PageHeader, PriorityBadge, QueryView, Section } from "@/components/common";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { MilestoneFormDialog, MilestoneList, WorkstreamManager } from "@/components/milestones";
import { ProjectFormDialog } from "@/components/project-form-dialog";
import { ReportComposer } from "@/components/report-composer";
import { describeActivity } from "@/components/task-sheet";
import { TaskFormDialog } from "@/components/task-form-dialog";
import { KanbanBoard, TaskFilterBar, TaskRow, TaskTable } from "@/components/task-views";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { WorkLogDialog } from "@/components/work-log-dialog";
import { formatDate, formatDateTime, PROJECT_STATUS_LABEL, STATUS_LABEL, WORKLOG_KIND_LABEL } from "@/lib/format";
import {
  useActivity, useArchiveProject, useDeleteProject, useMilestones, usePlanCheck, useProject, useTasks, useWorkLogs,
  useWorkstreams, type TaskFilters,
} from "@/lib/queries";
import type { Project, TaskStatus } from "@/lib/types";

export default function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const q = useProject(id);
  return <QueryView query={q} rows={8}>{(p) => <Workspace project={p} />}</QueryView>;
}

function Workspace({ project: p }: { project: Project }) {
  const router = useRouter();
  const archive = useArchiveProject();
  const del = useDeleteProject();
  const [newTask, setNewTask] = useState(false);
  const [tab, setTab] = useState("overview");
  return (
    <>
      <Link href="/projects" className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="size-4" /> Projects</Link>
      <PageHeader
        title={p.name}
        description={<>
          {PROJECT_STATUS_LABEL[p.status]}{p.stage && <> · Stage: {p.stage.name}</>}
          {p.target_date && <> · Target {formatDate(p.target_date)}</>}
        </>}
        actions={<>
          <Button onClick={() => setNewTask(true)}><Plus /> New task</Button>
          <WorkLogDialog defaults={{ project_id: p.id }} trigger={<Button variant="outline"><MessageSquarePlus /> Add update</Button>} />
          <ProjectFormDialog project={p} trigger={<Button variant="outline"><Pencil /> Edit</Button>} />
          <Button variant="outline" onClick={() => archive.mutate({ id: p.id, restore: p.status === "archived" })}>
            {p.status === "archived" ? <><ArchiveRestore /> Restore</> : <><Archive /> Archive</>}
          </Button>
          <ConfirmDialog
            trigger={<Button variant="destructive" aria-label="Delete project"><Trash2 /></Button>}
            title="Delete this project permanently?"
            description={<>This deletes the project with <strong>all its workstreams, milestones, tasks and history</strong>. It cannot be undone. Archiving keeps everything and hides it from day-to-day views.</>}
            typeToConfirm={p.name}
            onConfirm={(typed) => del.mutate({ id: p.id, confirm: typed }, { onSuccess: () => router.push("/projects") })}
          />
        </>}
      />
      {p.status === "archived" && <p className="mb-4 rounded-lg bg-warning/15 px-3 py-2 text-sm text-warning">This project is archived. Its tasks are hidden from My Tasks, the planner and the dashboard.</p>}
      <TaskFormDialog open={newTask} onOpenChange={setNewTask} defaults={{ project_id: p.id }} />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="mb-4 flex h-auto flex-wrap justify-start">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="board">Board</TabsTrigger>
          <TabsTrigger value="backlog">Backlog</TabsTrigger>
          <TabsTrigger value="milestones">Milestones</TabsTrigger>
          <TabsTrigger value="workstreams">Workstreams</TabsTrigger>
          <TabsTrigger value="plan">Plan check</TabsTrigger>
          <TabsTrigger value="decisions">Decisions &amp; updates</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
        </TabsList>
        <TabsContent value="overview"><Overview project={p} onTab={setTab} /></TabsContent>
        <TabsContent value="board"><ProjectTasks projectId={p.id} mode="board" /></TabsContent>
        <TabsContent value="backlog"><ProjectTasks projectId={p.id} mode="list" /></TabsContent>
        <TabsContent value="milestones"><ProjectMilestones projectId={p.id} /></TabsContent>
        <TabsContent value="workstreams"><Section title="Workstreams"><WorkstreamManager projectId={p.id} /></Section></TabsContent>
        <TabsContent value="plan"><PlanCheckView projectId={p.id} /></TabsContent>
        <TabsContent value="decisions"><Updates projectId={p.id} /></TabsContent>
        <TabsContent value="activity"><ActivityFeed projectId={p.id} /></TabsContent>
        <TabsContent value="reports"><ReportComposer projectId={p.id} /></TabsContent>
      </Tabs>
    </>
  );
}

function ContextField({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="text-sm whitespace-pre-wrap">{value || <span className="text-muted-foreground italic">Not yet defined</span>}</dd>
    </div>
  );
}

function Overview({ project: p, onTab }: { project: Project; onTab: (t: string) => void }) {
  const upcoming = useTasks({ project_id: p.id, sort: "due_date", status: ["todo", "in_progress", "blocked", "in_review"] });
  const blocked = useTasks({ project_id: p.id, blocked: true });
  const milestones = useMilestones(p.id);
  const workstreams = useWorkstreams(p.id);
  const counts = Object.entries(p.task_counts) as [TaskStatus, number][];
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Section title="Progress" className="lg:col-span-2">
        <ExplainedProgress progress={p.progress} />
        <p className="mt-2 text-xs text-muted-foreground"><Info className="mr-1 inline size-3.5" aria-hidden />{p.progress.explanation}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          {counts.length === 0 ? <span className="text-muted-foreground">No tasks yet.</span> : counts.map(([s, n]) => (
            <span key={s} className="rounded bg-muted px-2 py-1">{STATUS_LABEL[s]}: <strong>{n}</strong></span>
          ))}
          {p.overdue_count > 0 && <span className="rounded bg-destructive/10 px-2 py-1 text-destructive">Overdue: <strong>{p.overdue_count}</strong></span>}
        </div>
      </Section>
      <Section title="Details">
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between"><dt className="text-muted-foreground">Priority</dt><dd><PriorityBadge priority={p.priority} /></dd></div>
          <div className="flex justify-between"><dt className="text-muted-foreground">Start</dt><dd>{formatDate(p.start_date)}</dd></div>
          <div className="flex justify-between"><dt className="text-muted-foreground">Target</dt><dd>{formatDate(p.target_date)}</dd></div>
          <div className="flex justify-between"><dt className="text-muted-foreground">Workstreams</dt><dd>{workstreams.data?.length ?? "—"}</dd></div>
          {p.repository_url && <div><dt className="text-muted-foreground">Repository</dt><dd className="break-all">{p.repository_url}</dd></div>}
        </dl>
      </Section>
      <Section title="Upcoming work" className="lg:col-span-2" actions={<Button size="xs" variant="ghost" onClick={() => onTab("backlog")}>Backlog</Button>}>
        {(upcoming.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No open tasks.</p> : (
          <ul className="divide-y">{(upcoming.data ?? []).slice(0, 8).map((t) => <TaskRow key={t.id} task={t} showProject={false} />)}</ul>
        )}
      </Section>
      <Section title="Blockers">
        {(blocked.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No blocked tasks.</p> : (
          <ul className="divide-y">{(blocked.data ?? []).map((t) => <TaskRow key={t.id} task={t} showProject={false} />)}</ul>
        )}
      </Section>
      <Section title="Milestones" className="lg:col-span-3" actions={<Button size="xs" variant="ghost" onClick={() => onTab("milestones")}>Manage</Button>}>
        {(milestones.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No milestones yet.</p> : (
          <ul className="grid gap-3 md:grid-cols-3">
            {(milestones.data ?? []).map((m) => (
              <li key={m.id} className="rounded-lg border p-3">
                <p className="truncate text-sm font-medium">{m.title}</p>
                <p className="mb-2 text-xs text-muted-foreground">Due {formatDate(m.due_date)}</p>
                <ExplainedProgress progress={m.progress} />
              </li>
            ))}
          </ul>
        )}
      </Section>
      <Section title="Project context" className="lg:col-span-3">
        <dl className="grid gap-4 md:grid-cols-2">
          <ContextField label="Description" value={p.description} />
          <ContextField label="Problem statement" value={p.problem_statement} />
          <ContextField label="Objectives" value={p.objectives} />
          <ContextField label="Target users" value={p.target_users} />
          <ContextField label="Business context" value={p.business_context} />
          <ContextField label="Expected outcomes" value={p.expected_outcomes} />
          <ContextField label="In scope" value={p.scope} />
          <ContextField label="Out of scope" value={p.out_of_scope} />
          <ContextField label="Risks and assumptions" value={p.risks_assumptions} />
          <ContextField label="Dependencies" value={p.dependencies} />
          <ContextField label="Stakeholders" value={p.stakeholders} />
          <ContextField label="Technology stack" value={p.tech_stack} />
        </dl>
      </Section>
    </div>
  );
}

function ProjectTasks({ projectId, mode }: { projectId: string; mode: "board" | "list" }) {
  const [filters, setFilters] = useState<TaskFilters>({ project_id: projectId, sort: mode === "list" ? "priority" : "position" });
  const q = useTasks({ ...filters, top_level: mode === "board" ? true : undefined });
  return (
    <>
      <TaskFilterBar filters={filters} onChange={setFilters} />
      <QueryView query={q}>
        {(tasks) => mode === "board"
          ? (tasks.length === 0 && !filters.q ? <EmptyState title="No tasks yet" description="Create a task to start the board. Drag cards between columns to change status." /> : <KanbanBoard tasks={tasks} />)
          : <TaskTable tasks={tasks} />}
      </QueryView>
      {mode === "board" && <p className="mt-2 text-xs text-muted-foreground">The board shows top-level tasks; subtasks appear inside each task and in the Backlog. Use the ⋯ menu on a card to move it with the keyboard.</p>}
    </>
  );
}

function ProjectMilestones({ projectId }: { projectId: string }) {
  const q = useMilestones(projectId);
  return (
    <>
      <div className="mb-3 flex justify-end"><MilestoneFormDialog projectId={projectId} trigger={<Button><Plus /> Add milestone</Button>} /></div>
      <QueryView query={q}>{(ms) => <MilestoneList milestones={ms} projectId={projectId} />}</QueryView>
    </>
  );
}

function PlanCheckView({ projectId }: { projectId: string }) {
  const q = usePlanCheck(projectId);
  return (
    <Section title="Delivery plan check">
      <p className="mb-3 text-sm text-muted-foreground">Deterministic checks for gaps and risks: missing acceptance criteria, estimates and deliverables, dependency clashes, bottlenecks, late or overdue work and days that exceed recorded working hours.</p>
      <QueryView query={q}>
        {(checks) => checks.length === 0 ? <EmptyState title="No issues found" description="The plan has no detected gaps right now." /> : (
          <ul className="space-y-2">
            {checks.map((c, i) => (
              <li key={i} className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm ${c.severity === "warning" ? "border-warning/40 bg-warning/10" : "bg-muted/50"}`}>
                {c.severity === "warning" ? <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" aria-label="Warning" /> : <Info className="mt-0.5 size-4 shrink-0 text-info" aria-label="Information" />}
                {c.message}
              </li>
            ))}
          </ul>
        )}
      </QueryView>
    </Section>
  );
}

function Updates({ projectId }: { projectId: string }) {
  const q = useWorkLogs({ project_id: projectId });
  return (
    <Section title="Decisions, research and updates" actions={<WorkLogDialog defaults={{ project_id: projectId }} trigger={<Button size="sm"><Plus /> Add</Button>} />}>
      <QueryView query={q}>
        {(logs) => logs.length === 0 ? <EmptyState title="Nothing recorded yet" description="Record progress updates, decisions, blockers and research here. They feed the reports." /> : (
          <ul className="divide-y">
            {logs.map((l) => (
              <li key={l.id} className="py-2.5">
                <p className="text-xs text-muted-foreground"><strong className="text-foreground">{WORKLOG_KIND_LABEL[l.kind]}</strong> · {formatDate(l.entry_date)}{l.task_title && <> · {l.task_title}</>}{l.hours && <> · {Number(l.hours)}h</>}</p>
                <p className="text-sm whitespace-pre-wrap">{l.summary}</p>
              </li>
            ))}
          </ul>
        )}
      </QueryView>
    </Section>
  );
}

function ActivityFeed({ projectId }: { projectId: string }) {
  const q = useActivity(projectId, 100);
  return (
    <Section title="Activity history">
      <QueryView query={q}>
        {(items) => items.length === 0 ? <EmptyState title="No activity yet" /> : (
          <ol className="space-y-1.5 border-l pl-4">
            {items.map((a) => (
              <li key={a.id} className="text-sm">
                <span className="font-medium">{a.task_title}</span>: {describeActivity(a)}
                <span className="ml-2 text-xs text-muted-foreground">{formatDateTime(a.created_at)}</span>
              </li>
            ))}
          </ol>
        )}
      </QueryView>
    </Section>
  );
}
