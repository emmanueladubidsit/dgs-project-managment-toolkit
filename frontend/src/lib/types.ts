// Types mirroring the FastAPI schemas (backend/app/schemas). Dates are ISO strings.

export type Priority = "critical" | "high" | "medium" | "low";
export type TaskStatus = "todo" | "in_progress" | "blocked" | "in_review" | "completed" | "cancelled";
export type ProjectStatus = "active" | "on_hold" | "completed" | "archived";
export type MilestoneStatus = "planned" | "in_progress" | "achieved" | "missed" | "cancelled";
export type WorkLogKind = "progress" | "decision" | "blocker" | "research" | "unplanned" | "note";
export type ReportKind = "daily" | "weekly" | "project";

export interface Stage {
  id: string;
  name: string;
  description: string | null;
  position: number;
  is_active: boolean;
}

export interface Progress {
  percent: number;
  method: "none" | "equal" | "weighted";
  explanation: string;
  tasks_counted: number;
  tasks_completed: number;
  tasks_excluded: number;
  total_weight: number;
}

export interface ProjectFields {
  name: string;
  description: string | null;
  problem_statement: string | null;
  objectives: string | null;
  target_users: string | null;
  business_context: string | null;
  scope: string | null;
  out_of_scope: string | null;
  expected_outcomes: string | null;
  stakeholders: string | null;
  dependencies: string | null;
  risks_assumptions: string | null;
  tech_stack: string | null;
  repository_url: string | null;
  docs_location: string | null;
  notes: string | null;
  start_date: string | null;
  target_date: string | null;
  priority: Priority;
  stage_id: string | null;
}

export interface Project extends ProjectFields {
  id: string;
  status: ProjectStatus;
  stage: Stage | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  progress: Progress;
  task_counts: Partial<Record<TaskStatus, number>>;
  overdue_count: number;
  blocked_count: number;
}

export interface Workstream {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  position: number;
}

export interface Milestone {
  id: string;
  project_id: string;
  project_name: string;
  workstream_id: string | null;
  title: string;
  description: string | null;
  deliverables: string | null;
  due_date: string | null;
  status: MilestoneStatus;
  achieved_at: string | null;
  created_at: string;
  progress: Progress;
  warnings: string[];
}

export interface DependencyRef {
  id: string;
  title: string;
  status: TaskStatus;
}

export interface Task {
  id: string;
  project_id: string;
  project_name: string;
  workstream_id: string | null;
  workstream_name: string | null;
  milestone_id: string | null;
  milestone_title: string | null;
  parent_id: string | null;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: Priority;
  start_date: string | null;
  due_date: string | null;
  scheduled_date: string | null;
  estimate_hours: string | null;
  actual_hours: string | null;
  progress: number;
  weight: number | null;
  acceptance_criteria: string | null;
  deliverables: string | null;
  assignee: string | null;
  labels: string[];
  notes: string | null;
  position: number;
  completed_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
  subtask_count: number;
  subtasks_completed: number;
  open_dependencies: DependencyRef[];
}

export interface TaskDetail extends Task {
  subtasks: Task[];
  dependencies: DependencyRef[];
  dependents: DependencyRef[];
}

export type TaskInput = Partial<
  Omit<Task, "id" | "project_name" | "workstream_name" | "milestone_title" | "is_overdue" |
    "subtask_count" | "subtasks_completed" | "open_dependencies" | "created_at" | "updated_at" |
    "completed_at" | "archived_at" | "estimate_hours" | "actual_hours">
> & { estimate_hours?: number | null; actual_hours?: number | null };

export interface Comment {
  id: string;
  task_id: string;
  body: string;
  created_at: string;
}

export interface Activity {
  id: string;
  task_id: string;
  project_id: string;
  action: string;
  changes: Record<string, [unknown, unknown]>;
  created_at: string;
  task_title: string | null;
}

export interface PlanNote {
  period: "day" | "week" | "month";
  period_start: string;
  objectives: string | null;
  notes: string | null;
  available_hours: string | null;
}

export interface WorkLog {
  id: string;
  entry_date: string;
  kind: WorkLogKind;
  summary: string;
  hours: string | null;
  project_id: string | null;
  task_id: string | null;
  project_name: string | null;
  task_title: string | null;
  created_at: string;
}

export interface DayPlan {
  date: string;
  note: PlanNote | null;
  scheduled: Task[];
  carried_over: Task[];
  due_unscheduled: Task[];
  completed: Task[];
  blockers: Task[];
  work_logs: WorkLog[];
  capacity: {
    planned_hours: number;
    available_hours: number | null;
    unestimated_tasks: number;
    over_capacity: boolean;
    message: string;
  };
}

export interface WeekPlan {
  week_start: string;
  week_end: string;
  note: PlanNote | null;
  days: { date: string; tasks: Task[]; planned_hours: number; available_hours: number | null }[];
  carried_over: Task[];
  deadlines: Task[];
  milestones: Milestone[];
  planned_count: number;
  completed_count: number;
  completed_unplanned_count: number;
}

export interface MonthPlan {
  month_start: string;
  month_end: string;
  note: PlanNote | null;
  milestones: Milestone[];
  deadlines: Task[];
  weeks: { week_start: string; planned: number; completed: number }[];
  completed_count: number;
  planned_count: number;
}

export interface PlanCheck {
  severity: "warning" | "info";
  category: string;
  message: string;
  task_ids: string[];
  milestone_ids: string[];
}

export interface Dashboard {
  today: string;
  projects: Project[];
  due_today: Task[];
  overdue: Task[];
  upcoming: Task[];
  blocked: Task[];
  milestones: Milestone[];
  recent_activity: Activity[];
  week_planned: number;
  week_completed: number;
}

export interface ReportDraft {
  kind: ReportKind;
  title: string;
  period_start: string;
  period_end: string;
  project_id: string | null;
  content: string;
  generated_at: string;
}

export interface Report extends ReportDraft {
  id: string;
  created_at: string;
  updated_at: string;
}
