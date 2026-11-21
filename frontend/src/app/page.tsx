"use client";
import { BookOpen, CalendarDays, FolderPlus, MessageSquarePlus, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { EmptyState, ExplainedProgress, PageHeader, QueryView, Section } from "@/components/common";
import { ProjectFormDialog } from "@/components/project-form-dialog";
import { describeActivity } from "@/components/task-sheet";
import { TaskFormDialog } from "@/components/task-form-dialog";
import { TaskRow } from "@/components/task-views";
import { Button } from "@/components/ui/button";
import { WorkLogDialog } from "@/components/work-log-dialog";
import { formatDateTime, formatShort, formatLong } from "@/lib/format";
import { useDashboard } from "@/lib/queries";
import type { Task } from "@/lib/types";

function TaskList({ tasks, empty }: { tasks: Task[]; empty: string }) {
  if (!tasks.length) return <p className="text-sm text-muted-foreground">{empty}</p>;
  return <ul className="divide-y">{tasks.slice(0, 8).map((t) => <TaskRow key={t.id} task={t} />)}</ul>;
}

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function DashboardPage() {
  const q = useDashboard();
  const [newTask, setNewTask] = useState(false);
  return (
    <>
      <PageHeader title={greeting()} description={formatLong(new Date().toISOString())} />
      <div className="mb-6 flex flex-wrap gap-2" aria-label="Quick actions">
        <ProjectFormDialog trigger={<Button variant="outline"><FolderPlus /> New project</Button>} />
        <Button variant="outline" onClick={() => setNewTask(true)}><Plus /> New task</Button>
        <WorkLogDialog trigger={<Button variant="outline"><MessageSquarePlus /> Add daily update</Button>} />
        <WorkLogDialog defaults={{ kind: "research" }} trigger={<Button variant="outline"><Search /> Capture research</Button>} />
        <Button variant="outline" asChild><Link href="/knowledge"><BookOpen /> Create knowledge item</Link></Button>
        <Button variant="outline" asChild><Link href="/planner"><CalendarDays /> Start a planning session</Link></Button>
      </div>
      <TaskFormDialog open={newTask} onOpenChange={setNewTask} />

      <QueryView query={q} rows={8}>
        {(d) => d.projects.length === 0 ? (
          <EmptyState title="Welcome to your workspace" description="Start by creating a project. Break it into workstreams, milestones and tasks, then plan your week."
            action={<ProjectFormDialog trigger={<Button><FolderPlus /> Create your first project</Button>} />} />
        ) : (
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:col-span-3">
              <Stat label="Active projects" value={d.projects.length} />
              <Stat label="Due or planned today" value={d.due_today.length} />
              <Stat label="Overdue" value={d.overdue.length} tone={d.overdue.length ? "bad" : undefined} />
              <Stat label="This week" value={`${d.week_completed}/${d.week_planned}`} hint="planned tasks completed" />
            </div>

            <Section title="Today" className="lg:col-span-2" actions={<Link href="/planner" className="text-xs text-primary hover:underline">Open planner</Link>}>
              <TaskList tasks={d.due_today} empty="Nothing is due or planned for today." />
            </Section>
            <Section title="Blocked">
              <TaskList tasks={d.blocked} empty="No blocked tasks." />
            </Section>
            <Section title="Overdue" className="lg:col-span-2">
              <TaskList tasks={d.overdue} empty="Nothing is overdue." />
            </Section>
            <Section title="Due in the next 7 days">
              <TaskList tasks={d.upcoming} empty="No upcoming deadlines." />
            </Section>

            <Section title="Active projects" className="lg:col-span-2" actions={<Link href="/projects" className="text-xs text-primary hover:underline">All projects</Link>}>
              <ul className="divide-y">
                {d.projects.slice(0, 6).map((p) => (
                  <li key={p.id} className="grid grid-cols-[1fr_8rem] items-center gap-4 py-2.5 sm:grid-cols-[1fr_6rem_10rem]">
                    <div className="min-w-0">
                      <Link href={`/projects/${p.id}`} className="block truncate text-sm font-medium hover:underline">{p.name}</Link>
                      <p className="text-xs text-muted-foreground">
                        {p.stage?.name ?? "No stage"}
                        {p.overdue_count > 0 && <span className="text-destructive"> · {p.overdue_count} overdue</span>}
                        {p.blocked_count > 0 && <span className="text-status-blocked"> · {p.blocked_count} blocked</span>}
                      </p>
                    </div>
                    <span className="hidden text-xs text-muted-foreground sm:block">{p.target_date ? `Target ${formatShort(p.target_date)}` : ""}</span>
                    <ExplainedProgress progress={p.progress} />
                  </li>
                ))}
              </ul>
            </Section>
            <Section title="Current milestones" actions={<Link href="/milestones" className="text-xs text-primary hover:underline">All milestones</Link>}>
              {d.milestones.length === 0 ? <p className="text-sm text-muted-foreground">No open milestones.</p> : (
                <ul className="space-y-3">
                  {d.milestones.map((m) => (
                    <li key={m.id}>
                      <div className="flex justify-between gap-2 text-sm"><span className="truncate font-medium">{m.title}</span><span className="shrink-0 text-xs text-muted-foreground">{formatShort(m.due_date)}</span></div>
                      <p className="mb-1 text-xs text-muted-foreground">{m.project_name}</p>
                      <ExplainedProgress progress={m.progress} />
                    </li>
                  ))}
                </ul>
              )}
            </Section>

            <Section title="Recent activity" className="lg:col-span-3">
              {d.recent_activity.length === 0 ? <p className="text-sm text-muted-foreground">No activity yet.</p> : (
                <ul className="grid gap-x-6 gap-y-1.5 text-sm md:grid-cols-2">
                  {d.recent_activity.map((a) => (
                    <li key={a.id} className="truncate">
                      <span className="font-medium">{a.task_title}</span>
                      <span className="text-muted-foreground">: {describeActivity(a)} · {formatDateTime(a.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          </div>
        )}
      </QueryView>
    </>
  );
}

function Stat({ label, value, hint, tone }: { label: string; value: number | string; hint?: string; tone?: "bad" }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${tone === "bad" ? "text-destructive" : ""}`}>{value}</p>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
