# Database design

PostgreSQL 17 (Docker, port 5433). Schema managed by Alembic in `backend/migrations/`.
All primary keys are UUIDs; all tables carry `created_at`/`updated_at` (activity is append-only).
Enumerations are stored as strings with CHECK constraints rather than native PG enums so new
values need only a simple migration.

## Entities (implemented)

```
project_stages ─┐
                ▼
            projects ──┬──< workstreams
                       ├──< milestones >── (optional) workstream
                       ├──< tasks ──┬── workstream (SET NULL on delete)
                       │            ├── milestone  (SET NULL on delete)
                       │            ├── parent task (CASCADE) — subtasks
                       │            ├──< task_dependencies >── task   (task waits for depends_on)
                       │            ├──< task_comments
                       │            └──< task_activity (append-only history, JSONB diff)
                       ├──< work_logs (SET NULL on project/task delete)
                       └──< reports   (SET NULL)
plan_notes (period = day | week | month, period_start) — objectives, notes, available hours
```

| Table | Notes |
| --- | --- |
| `project_stages` | Configurable lifecycle stages, seeded with Discovery → Maintenance. `is_active` hides a stage without deleting history. |
| `projects` | Full project context (problem, objectives, users, scope/out of scope, outcomes, stakeholders, dependencies, risks, stack, repository and docs locations, notes), dates, status, priority, stage, `archived_at`. |
| `workstreams` | Per-project, ordered by `position`. Deleting one keeps its tasks. |
| `milestones` | Due date, deliverables, status, `achieved_at` (set only by an explicit status change). |
| `tasks` | Status, priority, start/due/**scheduled** dates, estimate/actual hours, `progress` 0–100, optional `weight` 1–100, acceptance criteria, deliverables, assignee, `labels text[]`, float `position` for ordering, `completed_at`, `archived_at`. |
| `task_dependencies` | Unique `(task_id, depends_on_id)`; CHECK no self-dependency; cycles rejected in the service layer. |
| `task_comments` | Updates and comments on a task. |
| `task_activity` | `action` + `changes` JSONB (`{field: [old, new]}`), indexed by time. |
| `plan_notes` | Unique per `(period, period_start)`; weeks start Monday, months on the 1st. |
| `work_logs` | Dated entries of kind progress / decision / blocker / research / unplanned / note, optional hours, project and task. |
| `reports` | Saved, editable report Markdown with its kind, period and generation time. |

### Library (migration 0002)

| Table | Notes |
| --- | --- |
| `knowledge_items` | Category, title, summary, Markdown content, JSONB `fields` (validated per category template), verification, tags, sources, limitations, reuse notes, version, optional source work log, `archived_at`. |
| `knowledge_versions` | Snapshot of the previous state per version (`item_id`, `version` unique). |
| `knowledge_project_links` | Item ↔ project with role origin / reused / related (unique pair). |
| `knowledge_task_links` | Item ↔ task. |
| `knowledge_relations` | Directed item → item: evidence_for / supersedes / related (no self links). |
| `methodologies` | Slug (unique), kind (methodology / playbook / starter kit), status (draft / published / deprecated), purpose, when to use, prerequisites, tools, dependencies, risks, completion criteria, limitations, version, origin project. |
| `methodology_stages`, `methodology_activities` | Ordered stages and activities (instructions, expected output). |
| `deliverable_definitions` | Name, classification (mandatory / recommended / optional / not applicable), optional stage and template (knowledge item). |
| `methodology_versions` | Full JSON snapshot per version. |
| `project_methodologies` | A project's adoption: methodology, version adopted, stage ids adopted, notes. |
| `project_deliverables` | Per-adoption deliverable tracking: classification override, status, linked document and milestone. |
| `document_roots` | Registered folders (resolved real path, unique), optional project, last scan time. |
| `project_documents` | Title, category, status, description, project, root + relative path **or** URL **or** in-app content, tags, size and modified time from disk; unique (root, path). |
| `document_task_links` | Document ↔ task. |
| `voice_notes` | Recording or text: transcript (raw and edited), provider, duration, audio path only while retained, audio deletion time. |
| `suggestions` | Kind (task / blocker / decision / progress), status (pending / approved / rejected / deferred), source note, project, generator (`rules`), payload, evidence sentence, possible duplicate task, created task or work log. |

## Constraints and indexes

- CHECKs: progress range, weight range, task is not its own parent, dependency is not self.
- Indexes on every foreign key, `tasks(project_id, status)`, `tasks.due_date`,
  `tasks.scheduled_date`, `milestones.due_date`, `work_logs.entry_date`, `task_activity.created_at`.
- Deterministic constraint names via a naming convention (`db.py`).

## Deliberately deferred

The brief's ResearchRecord, DecisionRecord, Template and EvidenceReference are represented by
`knowledge_items` categories and `knowledge_relations` (ADR 0004); Playbook and StarterKit are
methodology kinds; Artefact is a `project_documents` record; Transcript lives on `voice_notes`.
Still deferred: `ClaudeSession` (Phase 9, after researching supported Claude Code mechanisms) and
`SystemSetting`, `AuditEvent` (Phase 10).

## Migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"   # review the file before applying
uv run alembic upgrade head
```

Review autogenerated migrations before applying, and never write a destructive migration
(dropping columns or tables holding data) without a backup and an explicit decision record.
