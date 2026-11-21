"use client";
// Data hooks. Every view reads the same server records; any mutation invalidates all cached
// queries so the board, list, planner, dashboard and reports never drift apart.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errorMessage } from "./api";
import type {
  Activity, Comment, Dashboard, DayPlan, Milestone, MonthPlan, PlanCheck, PlanNote, Project,
  ProjectFields, Report, ReportDraft, ReportKind, Stage, Task, TaskDetail, TaskInput, WeekPlan,
  WorkLog, Workstream,
} from "./types";

export type TaskFilters = {
  project_id?: string;
  workstream_id?: string;
  milestone_id?: string;
  status?: string[];
  priority?: string[];
  q?: string;
  overdue?: boolean;
  blocked?: boolean;
  top_level?: boolean;
  include_archived?: boolean;
  sort?: string;
  scheduled_from?: string;
  scheduled_to?: string;
  unscheduled?: boolean;
};

// ---------- queries
export const useDashboard = () => useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dashboard>("/dashboard") });
export const useStages = () => useQuery({ queryKey: ["stages"], queryFn: () => api<Stage[]>("/stages"), staleTime: 60_000 });
export const useProjects = (query: { q?: string; status?: string; include_archived?: boolean } = {}) =>
  useQuery({ queryKey: ["projects", query], queryFn: () => api<Project[]>("/projects", { query }) });
export const useProject = (id: string) =>
  useQuery({ queryKey: ["project", id], queryFn: () => api<Project>(`/projects/${id}`) });
export const useWorkstreams = (projectId?: string) =>
  useQuery({
    queryKey: ["workstreams", projectId],
    queryFn: () => api<Workstream[]>(`/projects/${projectId}/workstreams`),
    enabled: !!projectId,
  });
export const useMilestones = (projectId?: string) =>
  useQuery({
    queryKey: ["milestones", projectId ?? "all"],
    queryFn: () => api<Milestone[]>("/milestones", { query: { project_id: projectId } }),
  });
export const useTasks = (filters: TaskFilters) =>
  useQuery({ queryKey: ["tasks", filters], queryFn: () => api<Task[]>("/tasks", { query: filters }) });
export const useTask = (id: string | null) =>
  useQuery({ queryKey: ["task", id], queryFn: () => api<TaskDetail>(`/tasks/${id}`), enabled: !!id });
export const useComments = (id: string) =>
  useQuery({ queryKey: ["comments", id], queryFn: () => api<Comment[]>(`/tasks/${id}/comments`) });
export const useTaskActivity = (id: string) =>
  useQuery({ queryKey: ["task-activity", id], queryFn: () => api<Activity[]>(`/tasks/${id}/activity`) });
export const useActivity = (projectId?: string, limit = 30) =>
  useQuery({ queryKey: ["activity", projectId, limit], queryFn: () => api<Activity[]>("/activity", { query: { project_id: projectId, limit } }) });
export const useDayPlan = (date: string) =>
  useQuery({ queryKey: ["planner", "day", date], queryFn: () => api<DayPlan>("/planner/day", { query: { date } }) });
export const useWeekPlan = (start: string) =>
  useQuery({ queryKey: ["planner", "week", start], queryFn: () => api<WeekPlan>("/planner/week", { query: { start } }) });
export const useMonthPlan = (month: string) =>
  useQuery({ queryKey: ["planner", "month", month], queryFn: () => api<MonthPlan>("/planner/month", { query: { month } }) });
export const usePlanCheck = (projectId: string) =>
  useQuery({ queryKey: ["plan-check", projectId], queryFn: () => api<PlanCheck[]>(`/projects/${projectId}/plan-check`) });
export const useWorkLogs = (query: { date_from?: string; date_to?: string; project_id?: string }) =>
  useQuery({ queryKey: ["work-logs", query], queryFn: () => api<WorkLog[]>("/work-logs", { query }) });
export const useReports = () => useQuery({ queryKey: ["reports"], queryFn: () => api<Report[]>("/reports") });
export const useSystemInfo = () =>
  useQuery({ queryKey: ["admin"], queryFn: () => api<Record<string, unknown>>("/admin/system") });
export const useHealth = () =>
  useQuery({ queryKey: ["health"], queryFn: () => api<{ status: string; version: string; database: string }>("/health"), refetchInterval: 30_000 });

// ---------- mutations
function useAction<TVars, TResult>(
  fn: (vars: TVars) => Promise<TResult>,
  opts: { success?: string | ((r: TResult) => string); silent?: boolean } = {},
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (result) => {
      qc.invalidateQueries();
      if (opts.success) toast.success(typeof opts.success === "function" ? opts.success(result) : opts.success);
    },
    onError: (e) => {
      if (!opts.silent) toast.error(errorMessage(e));
    },
  });
}

type ProjectInput = Partial<ProjectFields> & { status?: string; workstreams?: string[] };

export const useCreateProject = () =>
  useAction((body: ProjectInput) => api<Project>("/projects", { method: "POST", body }), { success: "Project created." });
export const useUpdateProject = (id: string) =>
  useAction((body: ProjectInput) => api<Project>(`/projects/${id}`, { method: "PATCH", body }), { success: "Project saved." });
export const useArchiveProject = () =>
  useAction(({ id, restore }: { id: string; restore?: boolean }) =>
    api<Project>(`/projects/${id}/${restore ? "restore" : "archive"}`, { method: "POST" }),
    { success: (p) => (p.status === "archived" ? "Project archived." : "Project restored.") });
export const useDeleteProject = () =>
  useAction(({ id, confirm }: { id: string; confirm: string }) =>
    api<void>(`/projects/${id}`, { method: "DELETE", query: { confirm } }), { success: "Project deleted." });

export const useCreateWorkstream = (projectId: string) =>
  useAction((body: { name: string; description?: string }) =>
    api<Workstream>(`/projects/${projectId}/workstreams`, { method: "POST", body }), { success: "Workstream added." });
export const useUpdateWorkstream = () =>
  useAction(({ id, ...body }: { id: string; name?: string; description?: string | null }) =>
    api<Workstream>(`/workstreams/${id}`, { method: "PATCH", body }));
export const useDeleteWorkstream = () =>
  useAction((id: string) => api<void>(`/workstreams/${id}`, { method: "DELETE" }), { success: "Workstream removed. Its tasks were kept." });

type MilestoneInput = { title?: string; description?: string | null; deliverables?: string | null; due_date?: string | null; status?: string; workstream_id?: string | null };
export const useCreateMilestone = (projectId: string) =>
  useAction((body: MilestoneInput) => api<Milestone>(`/projects/${projectId}/milestones`, { method: "POST", body }), { success: "Milestone created." });
export const useUpdateMilestone = () =>
  useAction(({ id, ...body }: MilestoneInput & { id: string }) => api<Milestone>(`/milestones/${id}`, { method: "PATCH", body }), { success: "Milestone saved." });
export const useDeleteMilestone = () =>
  useAction((id: string) => api<void>(`/milestones/${id}`, { method: "DELETE" }), { success: "Milestone deleted. Its tasks were kept." });

export const useCreateTask = () =>
  useAction((body: TaskInput & { project_id: string; title: string }) => api<TaskDetail>("/tasks", { method: "POST", body }), { success: "Task created." });
export const useUpdateTask = (opts: { success?: string } = {}) =>
  useAction(({ id, ...body }: TaskInput & { id: string }) => api<TaskDetail>(`/tasks/${id}`, { method: "PATCH", body }), opts);
export const useBulkUpdate = () =>
  useAction((body: { task_ids: string[]; changes: TaskInput }) => api<Task[]>("/tasks/bulk", { method: "POST", body }),
    { success: (r) => `${r.length} task(s) updated.` });
export const useArchiveTask = () =>
  useAction(({ id, restore }: { id: string; restore?: boolean }) =>
    api<TaskDetail>(`/tasks/${id}/${restore ? "restore" : "archive"}`, { method: "POST" }),
    { success: (t) => (t.archived_at ? "Task archived." : "Task restored.") });
export const useDeleteTask = () =>
  useAction((id: string) => api<void>(`/tasks/${id}`, { method: "DELETE", query: { confirm: true } }), { success: "Task deleted." });
export const useAddDependency = (taskId: string) =>
  useAction((depends_on_id: string) => api<TaskDetail>(`/tasks/${taskId}/dependencies`, { method: "POST", body: { depends_on_id } }), { success: "Dependency added." });
export const useRemoveDependency = (taskId: string) =>
  useAction((dependsOnId: string) => api<TaskDetail>(`/tasks/${taskId}/dependencies/${dependsOnId}`, { method: "DELETE" }));
export const useAddComment = (taskId: string) =>
  useAction((body: string) => api<Comment>(`/tasks/${taskId}/comments`, { method: "POST", body: { body } }));

export const useSavePlanNote = () =>
  useAction((body: Omit<PlanNote, "available_hours"> & { available_hours: number | null }) =>
    api<PlanNote>("/planner/notes", { method: "PUT", body }), { success: "Plan saved." });
export const useCarryForward = () =>
  useAction((body: { to_date: string; task_ids?: string[] }) => api<Task[]>("/planner/carry-forward", { method: "POST", body }),
    { success: (r) => `${r.length} task(s) moved.` });

type WorkLogInput = { entry_date: string; kind: string; summary: string; hours?: number | null; project_id?: string | null; task_id?: string | null };
export const useCreateWorkLog = () =>
  useAction((body: WorkLogInput) => api<WorkLog>("/work-logs", { method: "POST", body }), { success: "Update recorded." });
export const useDeleteWorkLog = () =>
  useAction((id: string) => api<void>(`/work-logs/${id}`, { method: "DELETE" }), { success: "Entry deleted." });

export const useGenerateReport = () =>
  useMutation({
    mutationFn: (body: { kind: ReportKind; date: string; project_id?: string | null; audience: string }) =>
      api<ReportDraft>("/reports/generate", { method: "POST", body }),
    onError: (e) => toast.error(errorMessage(e)),
  });
export const useSaveReport = () =>
  useAction((body: ReportDraft) => api<Report>("/reports", { method: "POST", body }), { success: "Report saved." });
export const useUpdateReport = () =>
  useAction(({ id, ...body }: { id: string; title?: string; content?: string }) => api<Report>(`/reports/${id}`, { method: "PATCH", body }), { success: "Report saved." });
export const useDeleteReport = () =>
  useAction((id: string) => api<void>(`/reports/${id}`, { method: "DELETE" }), { success: "Report deleted." });
