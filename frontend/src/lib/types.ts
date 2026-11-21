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

// ---------------------------------------------------------------- knowledge
export type KnowledgeCategory =
  | "research" | "troubleshooting" | "runbook" | "playbook" | "technical_standard" | "design_standard"
  | "architecture_pattern" | "decision" | "lesson_learned" | "template" | "reusable_component"
  | "setup_guide" | "checklist" | "project_documentation";
export type Verification =
  | "verified_tested" | "verified_docs" | "applied_in_project" | "research_unimplemented" | "ai_suggestion" | "outdated";
export type LinkRole = "origin" | "reused" | "related";
export type RelationKind = "evidence_for" | "supersedes" | "related";

export interface CategoryTemplate {
  category: KnowledgeCategory;
  label: string;
  fields: { key: string; label: string; hint: string }[];
}

export interface KnowledgeItem {
  id: string;
  category: KnowledgeCategory;
  title: string;
  summary: string | null;
  content: string | null;
  fields: Record<string, string>;
  verification: Verification;
  tags: string[];
  sources: string | null;
  limitations: string | null;
  reuse_notes: string | null;
  version: number;
  source_work_log_id: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  projects: { project_id: string; project_name: string; role: LinkRole; note: string | null; created_at: string }[];
}

export interface KnowledgeDetail extends KnowledgeItem {
  tasks: { task_id: string; task_title: string; project_name: string }[];
  relations: {
    id: string; kind: RelationKind; direction: "outgoing" | "incoming"; other_id: string; other_title: string;
    other_category: KnowledgeCategory; other_verification: Verification;
  }[];
}

export interface KnowledgeVersion { version: number; snapshot: Record<string, unknown>; change_note: string | null; created_at: string }

export interface SearchHit {
  type: "project" | "task" | "knowledge" | "methodology" | "document" | "work_log" | "voice_note";
  id: string;
  title: string;
  snippet: string | null;
  project_id: string | null;
  project_name: string | null;
  meta: string | null;
}

// ---------------------------------------------------------------- methodologies
export type MethodologyKind = "methodology" | "playbook" | "starter_kit";
export type MethodologyStatus = "draft" | "published" | "deprecated";
export type Classification = "mandatory" | "recommended" | "optional" | "not_applicable";
export type DeliverableStatus = "pending" | "in_progress" | "done" | "not_applicable";

export interface MethodologySummary {
  id: string;
  slug: string;
  name: string;
  kind: MethodologyKind;
  status: MethodologyStatus;
  purpose: string | null;
  when_to_use: string | null;
  version: number;
  origin_project_id: string | null;
  origin_project_name: string | null;
  archived_at: string | null;
  updated_at: string;
  stage_count: number;
  activity_count: number;
  deliverable_count: number;
  adoption_count: number;
}

export interface MethodologyActivity { id: string; position: number; title: string; instructions: string | null; expected_output: string | null }
export interface MethodologyStage {
  id: string; position: number; name: string; description: string | null; validation_criteria: string | null;
  activities: MethodologyActivity[];
}
export interface DeliverableDefinition {
  id: string; stage_id: string | null; position: number; name: string; description: string | null;
  classification: Classification; template_id: string | null;
}

export interface MethodologyDetail extends MethodologySummary {
  prerequisites: string | null;
  tools: string | null;
  dependencies: string | null;
  common_risks: string | null;
  completion_criteria: string | null;
  limitations: string | null;
  stages: MethodologyStage[];
  deliverables: DeliverableDefinition[];
  adoptions: { id: string; project_id: string; project_name: string; methodology_version: number; adopted_at: string }[];
}

export interface ProjectDeliverable {
  id: string; definition_id: string | null; name: string; classification: Classification; status: DeliverableStatus;
  document_id: string | null; milestone_id: string | null; notes: string | null;
}

export interface Adoption {
  id: string; project_id: string; project_name: string; methodology_id: string; methodology_name: string;
  methodology_version: number; current_version: number; stage_ids: string[]; notes: string | null; adopted_at: string;
  deliverables: ProjectDeliverable[]; milestones_created: number; tasks_created: number;
}

// ---------------------------------------------------------------- documents
export type DocumentCategory =
  | "brief" | "requirements" | "architecture" | "adr" | "design" | "diagram" | "research" | "report"
  | "prototype" | "specification" | "testing" | "release_notes" | "meeting_notes" | "presentation" | "other";
export type DocumentStatus = "draft" | "final" | "superseded";

export interface DocumentRoot {
  id: string; name: string; path: string; project_id: string | null; project_name: string | null;
  last_scanned_at: string | null; document_count: number; available: boolean;
}

export interface ScannedFile {
  relative_path: string; size_bytes: number; modified_at: string; suggested_category: DocumentCategory; document_id: string | null;
}

export interface ProjectDocument {
  id: string; title: string; category: DocumentCategory; status: DocumentStatus; description: string | null;
  project_id: string | null; project_name: string | null; root_id: string | null; root_name: string | null;
  relative_path: string | null; url: string | null; content: string | null; tags: string[]; size_bytes: number | null;
  file_modified_at: string | null; archived_at: string | null; created_at: string; updated_at: string;
  source: "file" | "link" | "note"; file_available: boolean | null; tasks: { task_id: string; task_title: string }[];
}

// ---------------------------------------------------------------- voice
export interface VoiceStatus {
  provider: string; available: boolean; message: string; retention: "delete" | "keep"; retention_message: string;
  outputs: { key: string; label: string; needs_ai: boolean }[];
}

export interface VoiceNote {
  id: string; title: string; project_id: string | null; project_name: string | null; source: "recording" | "text";
  duration_seconds: number | null; has_audio: boolean; audio_deleted_at: string | null; transcript_raw: string | null;
  transcript_edited: string | null; transcription_provider: string | null; created_at: string; updated_at: string;
  pending_suggestions: number;
}

export type SuggestionKind = "task" | "task_update" | "blocker" | "decision" | "progress";
export interface Suggestion {
  id: string; kind: SuggestionKind; status: "pending" | "approved" | "rejected" | "deferred"; source_type: string;
  source_id: string | null; project_id: string | null; project_name: string | null; generator: string;
  payload: { title?: string; priority?: Priority; estimate_hours?: number; acceptance_criteria?: string; parent_id?: string; task_id?: string; status?: TaskStatus }; evidence: string | null; duplicate_of_task_id: string | null;
  duplicate_of_title: string | null; created_task_id: string | null; created_work_log_id: string | null;
}

// ---------------------------------------------------------------- connected codebases
export interface Connection {
  id: string; project_id: string; project_name: string; path: string; available: boolean; is_git: boolean;
  accept_claude: boolean; auto_sync: boolean; branch: string | null; head: string | null; uncommitted_changes: number;
  last_synced_at: string | null; last_activity_at: string | null; last_error: string | null;
  progress_patterns: string[]; progress_files_tracked: number;
}
export interface CodeEvent {
  id: string; kind: "commit" | "claude_session" | "claude_task" | "files" | "progress_file"; ref: string; title: string;
  summary: string | null; detail: { files?: string[]; file_count?: number; branch?: string; turns?: number; ended?: boolean; status?: string; file?: string; status_changes?: string[]; checked?: string[] }; occurred_at: string;
}
export interface ClaudeSetup { token: string; hook_settings: Record<string, unknown>; mcp_command: string; claude_md: string }
