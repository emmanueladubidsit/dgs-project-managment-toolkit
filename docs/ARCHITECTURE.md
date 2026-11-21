# Architecture

## Overview

A **modular monolith**: one FastAPI backend, one Next.js frontend, one PostgreSQL database. No
microservices (see [ADR 0001](DECISIONS/0001-modular-monolith-and-stack.md)).

```
Browser ──► Next.js (port 3010) ──/api/* rewrite──► FastAPI (port 8010) ──► PostgreSQL (port 5433)
            client-rendered pages                    REST + OpenAPI            Docker volume dgs_pgdata
            TanStack Query cache                     SQLAlchemy 2 + Alembic
```

The browser only talks to its own origin; Next.js proxies `/api/*` to the backend
(`frontend/next.config.ts`, `API_ORIGIN`). This avoids CORS in normal use and lets the backend
move to another host later without changing the frontend.

## Backend (`backend/app`)

| Module | Responsibility |
| --- | --- |
| `config.py` | Environment-based settings (`backend/.env`), no secrets in code |
| `db.py` | Engine, session, declarative base, UUID + timestamp mixins, naming convention |
| `models/` | SQLAlchemy models: `project.py`, `task.py`, `planning.py`, `enums.py` |
| `schemas/` | Pydantic request/response models (validation lives here) |
| `services/progress.py` | Weighted progress calculation with a human-readable explanation |
| `services/tasks.py` | Task rules: reference validation, status transitions, cycle checks, history, batched serialisation |
| `services/reports.py` | Deterministic Markdown report generation |
| `services/knowledge_templates.py` | Structured-field templates per knowledge category ([ADR 0004](DECISIONS/0004-single-knowledge-table-with-templates.md)) |
| `services/files.py` | Read-only, root-confined, secret-filtering file access ([ADR 0005](DECISIONS/0005-read-only-document-indexing.md)) |
| `services/transcription.py` | Speech-to-text provider interface; local faster-whisper ([ADR 0006](DECISIONS/0006-voice-providers-and-no-faked-ai.md)) |
| `services/text_tools.py` | Deterministic cleaning, structuring and suggestion extraction |
| `seed.py`, `seed_data.py` | Idempotent starter methodology library |
| `api/` | Routers: `projects`, `tasks`, `planning`, `reports`, `system` (dashboard, health, admin), `knowledge` (+ global search), `methodologies`, `documents`, `voice` (+ suggestions) |
| `errors.py` | One error shape: `{"error": {"code", "message", "details"}}`; unexpected errors are logged, never leaked |

### Core business rules

- **Status and progress are independent.** A task may be In Progress at 40%. Moving a task to
  Completed stamps `completed_at` and sets progress to 100%; reopening clears the completion date
  and keeps the recorded progress.
- **Nothing completes automatically.** Completing every subtask never completes the parent;
  milestones are only Achieved when you say so; projects are never auto-completed.
- **Weighted, explained progress** (`services/progress.py`): each counted task's weight is its
  explicit `weight`, else `estimate_hours`, else 1; completed tasks count 100%, others their
  recorded %; cancelled tasks are excluded. Project progress counts **top-level tasks only** so
  subtasks are not double-counted. Every progress value ships with an `explanation`.
- **Blocked** means status Blocked *or* waiting on an unfinished dependency.
- **Dependencies** cannot be self-referential, duplicated or circular (graph walk on insert).
  Parent/child hierarchies are checked for cycles the same way.
- **References stay inside a project**: a task's workstream, milestone and parent must belong to
  the task's project.
- **One source of truth for planning**: the day a task is planned for is `Task.scheduled_date`.
  The board, list, planner, dashboard and reports all read the same rows.
- **Working hours are never invented.** Capacity is checked only against hours you record for a day.
- **Destructive operations need confirmation**: deleting a task requires `confirm=true`; deleting a
  project requires the exact project name. Archive is offered as the safer alternative.

## Frontend (`frontend/src`)

- **Client-rendered pages** under `app/`. Pages depend on today's date and live local data, so the
  shell renders them browser-only via React 19.3 `use(browser())` inside a Suspense boundary
  (per the Next.js 16 SPA guide). The sidebar's `usePathname` is also wrapped in Suspense because
  `/projects/[id]` has a dynamic param under Cache Components.
- **Data layer** `lib/queries.ts`: TanStack Query hooks. Every mutation invalidates all queries, so
  every view stays consistent (simple and correct for a single-user local app).
- **Task detail** opens anywhere through `TaskSheetProvider` (`useOpenTask()`).
- **Components**: `common.tsx` (page header, badges, progress, empty/error/loading states),
  `task-views.tsx` (Kanban, table, filters), `task-sheet.tsx`, dialogs for projects, tasks,
  milestones and work logs, `report-composer.tsx`, `planned-module.tsx`.

### Library rules

- **Nothing is verified by default**: knowledge starts as *Research — not yet applied*; AI
  suggestions have their own status and warning; superseded items are marked *Outdated*.
- **Reuse keeps provenance**: one immutable origin project per item; reuse is recorded per project;
  methodologies record the project they were derived from and the version each project adopted.
- **Adoption never duplicates**: re-adopting a stage is refused; tasks with an existing title are
  skipped; removing an adoption keeps the milestones and tasks it created.
- **Files are read-only and confined** to registered folders; secrets are never listed or read.
- **Suggestions need approval**: voice/text never changes the backlog directly.

## Extension points (later phases)

- **AI** will sit behind a provider interface in `backend/app/services/ai/` and only ever produce
  *suggestions* that a person approves (Phase 8). The core never imports it.
- **AI writing outputs** (rewrite, summary, email drafts) are already listed in Voice & Writing and
  return `needs_ai` until a provider is configured.
- **Multi-user**: `assignee` exists as free text; roles and ownership can be added without
  restructuring (admin endpoints are already separated under `/api/admin`).
