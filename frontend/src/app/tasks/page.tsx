"use client";
import { LayoutList, Plus, SquareKanban } from "lucide-react";
import { useState } from "react";
import { EmptyState, PageHeader, QueryView } from "@/components/common";
import { TaskFormDialog } from "@/components/task-form-dialog";
import { KanbanBoard, TaskFilterBar, TaskTable } from "@/components/task-views";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useProjects, useTasks, type TaskFilters } from "@/lib/queries";

export default function MyTasksPage() {
  const [view, setView] = useState<"list" | "board">("list");
  const [filters, setFilters] = useState<TaskFilters>({ sort: "priority", status: ["todo", "in_progress", "blocked", "in_review"] });
  const [newTask, setNewTask] = useState(false);
  const projects = useProjects();
  const q = useTasks({ ...filters, status: view === "board" ? filters.status?.filter((s) => s !== "cancelled") : filters.status });
  return (
    <>
      <PageHeader title="My Tasks" description="Every task across all active projects."
        actions={<>
          <div className="flex rounded-lg border p-0.5" role="group" aria-label="View">
            <Button size="sm" variant={view === "list" ? "secondary" : "ghost"} aria-pressed={view === "list"} onClick={() => setView("list")}><LayoutList /> List</Button>
            <Button size="sm" variant={view === "board" ? "secondary" : "ghost"} aria-pressed={view === "board"} onClick={() => setView("board")}><SquareKanban /> Board</Button>
          </div>
          <Button onClick={() => setNewTask(true)}><Plus /> New task</Button>
        </>} />
      <TaskFilterBar filters={filters} onChange={setFilters} extra={
        <Select value={filters.project_id ?? "all"} onValueChange={(v) => setFilters({ ...filters, project_id: v === "all" ? undefined : v })}>
          <SelectTrigger className="w-48" aria-label="Project"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All projects</SelectItem>
            {(projects.data ?? []).map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
          </SelectContent>
        </Select>
      } />
      <QueryView query={q}>
        {(tasks) => (projects.data?.length === 0 ? (
          <EmptyState title="No projects yet" description="Tasks belong to projects. Create a project first." />
        ) : view === "board" ? <KanbanBoard tasks={tasks} showProject /> : <TaskTable tasks={tasks} showProject />)}
      </QueryView>
      <p className="mt-2 text-xs text-muted-foreground">By default completed and cancelled tasks are hidden — use the Status filter to show them.</p>
      <TaskFormDialog open={newTask} onOpenChange={setNewTask} />
    </>
  );
}
