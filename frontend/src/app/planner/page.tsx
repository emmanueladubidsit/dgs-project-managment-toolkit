"use client";
import { ArrowRight, CalendarCheck, ChevronLeft, ChevronRight, MessageSquarePlus, Plus, X } from "lucide-react";
import { useState } from "react";
import { EmptyState, ExplainedProgress, PageHeader, QueryView, Section } from "@/components/common";
import { TextAreaField, TextField } from "@/components/form-fields";
import { useOpenTask } from "@/components/task-sheet";
import { TaskRow } from "@/components/task-views";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { WorkLogDialog } from "@/components/work-log-dialog";
import {
  addDays, formatDate, formatLong, formatShort, hours, parseDate, toISODate, todayISO, WORKLOG_KIND_LABEL,
} from "@/lib/format";
import { useCarryForward, useDayPlan, useMonthPlan, useSavePlanNote, useTasks, useUpdateTask, useWeekPlan } from "@/lib/queries";
import type { PlanNote, Task } from "@/lib/types";
import { cn } from "@/lib/utils";

const mondayOf = (iso: string) => { const d = parseDate(iso); const wd = (d.getDay() + 6) % 7; d.setDate(d.getDate() - wd); return toISODate(d); };
const monthOf = (iso: string) => iso.slice(0, 8) + "01";
const shiftMonth = (iso: string, n: number) => { const d = parseDate(monthOf(iso)); d.setMonth(d.getMonth() + n); return toISODate(d); };

export default function PlannerPage() {
  const [tab, setTab] = useState("day");
  const [day, setDay] = useState(todayISO());
  return (
    <>
      <PageHeader title="Planner" description="Plan your day, week and month. Planning uses the same tasks as the board and lists." />
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="day">Day</TabsTrigger>
          <TabsTrigger value="week">Week</TabsTrigger>
          <TabsTrigger value="month">Month</TabsTrigger>
        </TabsList>
        <TabsContent value="day"><DayView day={day} setDay={setDay} /></TabsContent>
        <TabsContent value="week"><WeekView day={day} setDay={setDay} onOpenDay={(d) => { setDay(d); setTab("day"); }} /></TabsContent>
        <TabsContent value="month"><MonthView day={day} setDay={setDay} /></TabsContent>
      </Tabs>
    </>
  );
}

function Nav({ label, onPrev, onNext, onToday }: { label: string; onPrev: () => void; onNext: () => void; onToday: () => void }) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <Button size="icon-sm" variant="outline" aria-label="Previous" onClick={onPrev}><ChevronLeft /></Button>
      <Button size="icon-sm" variant="outline" aria-label="Next" onClick={onNext}><ChevronRight /></Button>
      <Button size="sm" variant="outline" onClick={onToday}>Today</Button>
      <h2 className="ml-2 text-lg font-semibold">{label}</h2>
    </div>
  );
}

function NoteEditor({ period, start, note, withHours, title }: { period: PlanNote["period"]; start: string; note: PlanNote | null; withHours?: boolean; title: string }) {
  const save = useSavePlanNote();
  const [objectives, setObjectives] = useState(note?.objectives ?? "");
  const [notes, setNotes] = useState(note?.notes ?? "");
  const [avail, setAvail] = useState(note?.available_hours != null ? String(Number(note.available_hours)) : "");
  return (
    <Section title={title}>
      <form className="space-y-3" onSubmit={(e) => {
        e.preventDefault();
        save.mutate({ period, period_start: start, objectives: objectives.trim() || null, notes: notes.trim() || null,
          available_hours: avail.trim() === "" ? null : Number(avail) });
      }}>
        <TextAreaField label="Objectives" value={objectives} onChange={setObjectives} rows={3} placeholder="What must be achieved?" />
        <TextAreaField label="Notes" value={notes} onChange={setNotes} rows={2} />
        {withHours && <TextField label="Available working hours" type="number" min={0} max={24} step="0.5" value={avail} onChange={setAvail}
          hint="Leave blank if not known — the planner never assumes working hours." />}
        <Button size="sm" type="submit" disabled={save.isPending}>Save</Button>
      </form>
    </Section>
  );
}

function AddToDay({ day }: { day: string }) {
  const q = useTasks({ unscheduled: true, status: ["todo", "in_progress", "in_review", "blocked"], sort: "priority" });
  const update = useUpdateTask({ success: "Task planned." });
  const options = q.data ?? [];
  if (!options.length) return null;
  return (
    <Select value="" onValueChange={(id) => update.mutate({ id, scheduled_date: day })}>
      <SelectTrigger className="w-full sm:w-72" aria-label="Plan an unscheduled task for this day"><SelectValue placeholder="Plan an unscheduled task…" /></SelectTrigger>
      <SelectContent>{options.map((t) => <SelectItem key={t.id} value={t.id}>{t.title} — {t.project_name}</SelectItem>)}</SelectContent>
    </Select>
  );
}

function DayView({ day, setDay }: { day: string; setDay: (d: string) => void }) {
  const q = useDayPlan(day);
  const update = useUpdateTask();
  const carry = useCarryForward();
  const isToday = day === todayISO();
  return (
    <>
      <Nav label={formatLong(day)} onPrev={() => setDay(addDays(day, -1))} onNext={() => setDay(addDays(day, 1))} onToday={() => setDay(todayISO())} />
      <QueryView query={q} rows={6}>
        {(p) => {
          const open = p.scheduled.filter((t) => t.status !== "completed" && t.status !== "cancelled");
          const done = p.completed;
          return (
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="space-y-4 lg:col-span-2">
                <div className={cn("rounded-xl border px-4 py-3 text-sm", p.capacity.over_capacity ? "border-destructive/40 bg-destructive/5 text-destructive" : "bg-muted/40")} role="status">
                  {p.capacity.message}
                </div>
                <Section title={`Planned (${open.length})`} actions={<AddToDay day={day} />}>
                  {open.length === 0 ? <EmptyState title="Nothing planned yet" description="Plan unscheduled tasks using the menu above, or set “Planned for” on any task." /> : (
                    <ul className="divide-y">
                      {open.map((t) => (
                        <TaskRow key={t.id} task={t} action={<span className="flex items-center gap-1">
                          <span className="w-10 text-right text-xs text-muted-foreground">{hours(t.estimate_hours)}</span>
                          <Button size="icon-xs" variant="ghost" aria-label={`Move ${t.title} to the next day`} title="Move to next day" onClick={() => update.mutate({ id: t.id, scheduled_date: addDays(day, 1) })}><ArrowRight /></Button>
                          <Button size="icon-xs" variant="ghost" aria-label={`Unplan ${t.title}`} title="Remove from this day" onClick={() => update.mutate({ id: t.id, scheduled_date: null })}><X /></Button>
                          <Button size="icon-xs" variant="ghost" aria-label={`Complete ${t.title}`} title="Mark completed" onClick={() => update.mutate({ id: t.id, status: "completed" })}><CalendarCheck /></Button>
                        </span>} />
                      ))}
                    </ul>
                  )}
                </Section>
                {p.carried_over.length > 0 && (
                  <Section title={`Carried over from earlier days (${p.carried_over.length})`}
                    actions={<Button size="sm" variant="outline" onClick={() => carry.mutate({ to_date: day })}>Move all to {isToday ? "today" : formatShort(day)}</Button>}>
                    <ul className="divide-y">
                      {p.carried_over.map((t) => (
                        <TaskRow key={t.id} task={t} action={<span className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">was {formatShort(t.scheduled_date)}</span>
                          <Button size="xs" variant="outline" onClick={() => update.mutate({ id: t.id, scheduled_date: day })}>Move here</Button>
                        </span>} />
                      ))}
                    </ul>
                  </Section>
                )}
                {p.due_unscheduled.length > 0 && (
                  <Section title="Due this day but not planned">
                    <ul className="divide-y">
                      {p.due_unscheduled.map((t) => (
                        <TaskRow key={t.id} task={t} action={<Button size="xs" variant="outline" onClick={() => update.mutate({ id: t.id, scheduled_date: day })}>Plan</Button>} />
                      ))}
                    </ul>
                  </Section>
                )}
                <Section title={`Completed (${done.length})`}>
                  {done.length === 0 ? <p className="text-sm text-muted-foreground">Nothing completed on this day yet.</p> : <ul className="divide-y">{done.map((t) => <TaskRow key={t.id} task={t} />)}</ul>}
                </Section>
              </div>
              <div className="space-y-4">
                <NoteEditor key={`day-${day}-${p.note?.objectives ?? ""}`} period="day" start={day} note={p.note} withHours title="Today’s objectives" />
                <Section title="Blockers">
                  {p.blockers.length === 0 ? <p className="text-sm text-muted-foreground">No blockers on planned work.</p> : <ul className="divide-y">{p.blockers.map((t) => <TaskRow key={t.id} task={t} />)}</ul>}
                </Section>
                <Section title="Updates and unplanned work" actions={<WorkLogDialog defaults={{ entry_date: day }} trigger={<Button size="sm" variant="outline"><MessageSquarePlus /> Add</Button>} />}>
                  {p.work_logs.length === 0 ? <p className="text-sm text-muted-foreground">No updates recorded.</p> : (
                    <ul className="space-y-2">
                      {p.work_logs.map((l) => (
                        <li key={l.id} className="text-sm">
                          <span className="text-xs font-medium text-muted-foreground">{WORKLOG_KIND_LABEL[l.kind]}{l.project_name && ` · ${l.project_name}`}</span>
                          <p className="whitespace-pre-wrap">{l.summary}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </Section>
              </div>
            </div>
          );
        }}
      </QueryView>
    </>
  );
}

function WeekView({ day, setDay, onOpenDay }: { day: string; setDay: (d: string) => void; onOpenDay: (d: string) => void }) {
  const start = mondayOf(day);
  const q = useWeekPlan(start);
  const update = useUpdateTask();
  const carry = useCarryForward();
  const openTask = useOpenTask();
  const [dragId, setDragId] = useState<string | null>(null);
  const backlog = useTasks({ unscheduled: true, status: ["todo", "in_progress", "in_review", "blocked"], sort: "priority" });

  const dropOn = (date: string | null) => {
    if (dragId) update.mutate({ id: dragId, scheduled_date: date });
    setDragId(null);
  };
  const Card = ({ t }: { t: Task }) => (
    <li draggable onDragStart={() => setDragId(t.id)} onDragEnd={() => setDragId(null)}
      className={cn("rounded-md border bg-card px-2 py-1.5 text-xs shadow-xs", t.status === "completed" && "opacity-60", dragId === t.id && "opacity-40")}>
      <button className={cn("block w-full text-left font-medium hover:underline", t.status === "completed" && "line-through")} onClick={() => openTask(t.id)}>{t.title}</button>
      <span className="text-muted-foreground">{t.project_name}{t.estimate_hours && ` · ${hours(t.estimate_hours)}`}</span>
    </li>
  );
  return (
    <>
      <Nav label={`Week commencing ${formatDate(start, { weekday: "long" })}`} onPrev={() => setDay(addDays(start, -7))} onNext={() => setDay(addDays(start, 7))} onToday={() => setDay(todayISO())} />
      <QueryView query={q} rows={6}>
        {(w) => (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Planned this week" value={w.planned_count} />
              <Stat label="Planned and completed" value={w.completed_count} />
              <Stat label="Completed, unplanned" value={w.completed_unplanned_count} />
              <Stat label="Carried over" value={w.carried_over.length} />
            </div>
            <p className="text-xs text-muted-foreground">Drag tasks between days, or from “Unscheduled” onto a day. Use a task’s “Planned for” field to do the same with the keyboard.</p>
            <div className="grid gap-2 md:grid-cols-4 xl:grid-cols-8">
              {w.days.map((d) => {
                const over = d.available_hours !== null && d.planned_hours > d.available_hours;
                return (
                  <div key={d.date} onDragOver={(e) => e.preventDefault()} onDrop={() => dropOn(d.date)}
                    className={cn("flex min-h-40 flex-col rounded-xl border bg-muted/40 p-2", d.date === todayISO() && "border-primary")}>
                    <button className="mb-1 text-left text-sm font-semibold hover:underline" onClick={() => onOpenDay(d.date)}>
                      {parseDate(d.date).toLocaleDateString("en-GB", { weekday: "short", day: "numeric" })}
                    </button>
                    <p className={cn("mb-2 text-[11px] text-muted-foreground", over && "font-medium text-destructive")}>
                      {d.planned_hours}h planned{d.available_hours !== null && ` / ${d.available_hours}h`}
                    </p>
                    <ul className="space-y-1.5">{d.tasks.map((t) => <Card key={t.id} t={t} />)}</ul>
                  </div>
                );
              })}
              <div onDragOver={(e) => e.preventDefault()} onDrop={() => dropOn(null)} className="flex min-h-40 flex-col rounded-xl border border-dashed p-2">
                <p className="mb-2 text-sm font-semibold">Unscheduled</p>
                <ul className="max-h-96 space-y-1.5 overflow-y-auto">{(backlog.data ?? []).slice(0, 30).map((t) => <Card key={t.id} t={t} />)}</ul>
              </div>
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              <NoteEditor key={`week-${w.week_start}-${w.note?.objectives ?? ""}`} period="week" start={w.week_start} note={w.note} title="Weekly objectives" />
              <Section title="Deadlines this week">
                {w.deadlines.length === 0 ? <p className="text-sm text-muted-foreground">No deadlines.</p> : <ul className="divide-y">{w.deadlines.map((t) => <TaskRow key={t.id} task={t} />)}</ul>}
              </Section>
              <Section title="Upcoming milestones">
                {w.milestones.length === 0 ? <p className="text-sm text-muted-foreground">None in the next two weeks.</p> : (
                  <ul className="space-y-3">{w.milestones.map((m) => (
                    <li key={m.id}><p className="text-sm font-medium">{m.title} <span className="font-normal text-muted-foreground">· {formatShort(m.due_date)}</span></p><ExplainedProgress progress={m.progress} /></li>
                  ))}</ul>
                )}
              </Section>
            </div>
            {w.carried_over.length > 0 && (
              <Section title="Carried over from previous weeks" actions={<Button size="sm" variant="outline" onClick={() => carry.mutate({ to_date: w.week_start < todayISO() ? todayISO() : w.week_start })}>Move all into this week</Button>}>
                <ul className="divide-y">{w.carried_over.map((t) => <TaskRow key={t.id} task={t} />)}</ul>
              </Section>
            )}
          </div>
        )}
      </QueryView>
    </>
  );
}

function MonthView({ day, setDay }: { day: string; setDay: (d: string) => void }) {
  const month = monthOf(day);
  const q = useMonthPlan(month);
  return (
    <>
      <Nav label={parseDate(month).toLocaleDateString("en-GB", { month: "long", year: "numeric" })}
        onPrev={() => setDay(shiftMonth(month, -1))} onNext={() => setDay(shiftMonth(month, 1))} onToday={() => setDay(todayISO())} />
      <QueryView query={q} rows={6}>
        {(m) => (
          <div className="grid gap-4 lg:grid-cols-3">
            <Section title="Planned versus completed, by week" className="lg:col-span-2">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs text-muted-foreground"><th className="py-1 font-medium">Week commencing</th><th className="font-medium">Planned</th><th className="font-medium">Completed</th></tr></thead>
                <tbody>{m.weeks.map((w) => (
                  <tr key={w.week_start} className="border-t"><td className="py-1.5">{formatDate(w.week_start)}</td><td className="tabular-nums">{w.planned}</td><td className="tabular-nums">{w.completed}</td></tr>
                ))}</tbody>
              </table>
              <p className="mt-2 text-xs text-muted-foreground">{m.planned_count} task(s) planned this month; {m.completed_count} completed (planned or not).</p>
            </Section>
            <NoteEditor key={`month-${m.month_start}-${m.note?.objectives ?? ""}`} period="month" start={m.month_start} note={m.note} title="Monthly objectives" />
            <Section title="Milestones due this month" className="lg:col-span-2">
              {m.milestones.length === 0 ? <p className="text-sm text-muted-foreground">No milestones due this month.</p> : (
                <ul className="space-y-3">{m.milestones.map((ms) => (
                  <li key={ms.id}>
                    <p className="text-sm font-medium">{ms.title} <span className="font-normal text-muted-foreground">· {ms.project_name} · {formatShort(ms.due_date)}</span></p>
                    <ExplainedProgress progress={ms.progress} />
                    {ms.warnings.length > 0 && <p className="text-xs text-warning">{ms.warnings.join(" ")}</p>}
                  </li>
                ))}</ul>
              )}
            </Section>
            <Section title="Open deadlines this month">
              {m.deadlines.length === 0 ? <p className="text-sm text-muted-foreground">None.</p> : <ul className="divide-y">{m.deadlines.map((t) => <TaskRow key={t.id} task={t} />)}</ul>}
            </Section>
          </div>
        )}
      </QueryView>
      <p className="mt-3 text-xs text-muted-foreground"><Plus className="inline size-3" /> Risks and dependencies for each project are listed on its Plan check tab.</p>
    </>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}
