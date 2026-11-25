# DGS Project & Engineering Intelligence Workspace

A local-first workspace for managing projects from idea to maintenance: projects, workstreams,
milestones, tasks and subtasks; daily, weekly and monthly planning; work logs; and reports
generated only from what you have actually recorded.

It works fully **without any AI service or API key**. An optional, built-in AI assistant can use a
free local model, your organisation's AI service, or copy-and-paste with any AI chat you already
have — so it adds no new cost ([ADR 0007](docs/DECISIONS/0007-ai-assistant-without-new-costs.md)).

## Quick start

Prerequisites: Docker (for PostgreSQL), [uv](https://docs.astral.sh/uv/) and Node.js 20+.
No Docker? See [DEVELOPMENT_SETUP.md](docs/DEVELOPMENT_SETUP.md#running-without-docker).

```bash
make setup     # first time only: start the database, install dependencies, apply migrations
make api       # terminal 1 — API on http://localhost:8010 (docs at /docs)
make web       # terminal 2 — app on http://localhost:3010
```

Then open **http://localhost:3010**.

| Command | What it does |
| --- | --- |
| `make db` | Start PostgreSQL (Docker, port 5433, persistent volume) |
| `make migrate` | Apply database migrations |
| `make seed` | Load the 13 starter methodologies (safe to re-run; never overwrites) |
| `make voice` | Optional: install local Whisper transcription |
| `make test` | Backend + frontend unit/component tests |
| `make e2e` | Browser end-to-end journey (needs `make api` and `make web-prod` running) |
| `make check` | Lint and type-check everything |
| `make backup` | Write a database backup to `backups/` |

## What works today

- **Projects** — create, edit, archive/restore, delete (type-the-name confirmation), lifecycle
  stages, full project context (problem, objectives, users, scope, risks…), search and filter.
- **Workstreams, milestones, tasks, subtasks** — priorities, statuses, separate progress %,
  estimates, actual effort, weights, acceptance criteria, deliverables, labels, dependencies
  (cycle-safe), comments, full change history, archive and safe delete.
- **Views on the same records** — Kanban board (drag and drop or keyboard menu), task list with
  filters, sorting and bulk update, daily/weekly/monthly planner, dashboard.
- **Transparent progress** — weighted by explicit weight, else estimate, else equal; every
  progress bar explains its calculation. Nothing is ever auto-completed.
- **Planning** — schedule and reschedule tasks, carry-over, capacity against working hours *you*
  enter (never assumed), plan notes and objectives, and a deterministic **plan check**
  (missing acceptance criteria, estimates or deliverables, dependency clashes, bottlenecks, late
  work, over-capacity days).
- **Work logs and reports** — progress updates, decisions, blockers, research and unplanned work;
  daily, weekly and project reports (stakeholder or technical) that you can edit, copy, download
  and save.
- **Knowledge & Research** — research, troubleshooting guides, runbooks, decisions, lessons learned,
  templates and more, with structured templates, explicit verification status, version history and
  restore, provenance (origin project) and reuse links, task links, evidence/supersedes
  relationships, and one-click promotion of a recorded decision or research update.
- **Methodologies & Playbooks** — a library of 13 starter methodologies (stages, activities,
  expected outputs, deliverables classed mandatory/recommended/optional/not applicable), with
  versions, publish/deprecate, duplicate-to-adapt, **create a playbook from a past project**, and
  adoption into a project (whole or selected stages) that creates milestones and tasks without
  duplicates and tracks deliverables.
- **Documents & Artefacts** — register project folders (read-only), scan and index files where they
  live, previews of text files, links and short notes, categories, project and task links. Paths
  are confined to registered folders and secret files are never listed or read.
- **Voice & Writing** — record/pause/resume/stop/play back in the browser; local Whisper
  transcription with audio deleted after transcription by default; editable transcripts;
  rule-based cleaning, structuring, meeting/research notes, daily updates and task breakdowns;
  suggested tasks, blockers and decisions that you approve, reject or defer, with duplicate checks.
- **AI assistant (optional)** — ask questions about one project or the whole portfolio; draft emails,
  updates, requirements and summaries with project context; turn notes into reviewed tasks; break
  tasks into subtasks; turn an idea into a project brief; draft research; add an executive summary
  to reports. Answers show the workspace records used; everything is a draft or suggestion you
  approve.
- **Stakeholder exports** — Word, PDF and PowerPoint for reports, project status updates, project
  briefs, full project reports and knowledge items.
- **Project tracker** — each project's `docs/project-management/PROGRESS-AND-PLAN-YYYY-MM-DD.md`
  (kept by Claude Code) is read on the **Tracker** tab: work done per working day (Mon–Fri; weekend
  work counts on Monday), milestone status and the plan become edit-then-approve suggestions,
  with **Approve all** ([ADR 0010](docs/DECISIONS/0010-tracker-import-and-project-discovery.md)).
- **Projects folder and discovery** — one recommended folder for technical projects; **Discover
  projects** adds new folders found there, and **Start a new project** creates one with a tracker
  and CLAUDE.md.
- **Connected codebases and Claude Code sync** — connect each project's folder (read-only):
  commits, changed files and uncommitted changes appear on the project's Codebase tab; commits
  that mention a task suggest marking it done. Claude Code can list a project's open tasks and
  report progress through the workspace MCP server, and optional hooks record session summaries.
  Every status change waits for your approval ([ADR 0008](docs/DECISIONS/0008-claude-code-sync-via-mcp-and-hooks.md)). Claude progress is read
  locally from progress files in the folder — no Claude Code configuration changes
  ([ADR 0009](docs/DECISIONS/0009-local-progress-file-sync.md)).
- **Privacy** — named individuals are masked as roles and secrets redacted in Claude reports,
  commit messages, AI prompts and exports.
- **Global search** (⌘K / Ctrl+K) across projects, tasks, knowledge, methodologies, documents,
  updates and notes.
- **Administration** — health, database and record diagnostics, backup guidance.

## Documentation

| Document | Purpose |
| --- | --- |
| [PRODUCT_REQUIREMENTS](docs/PRODUCT_REQUIREMENTS.md) | Vision, MVP scope, acceptance criteria status |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | System design and key rules |
| [DATABASE_DESIGN](docs/DATABASE_DESIGN.md) | Schema and relationships |
| [API_DESIGN](docs/API_DESIGN.md) | REST conventions and endpoint list |
| [DESIGN_SYSTEM](docs/DESIGN_SYSTEM.md) | Tokens, components, accessibility |
| [IMPLEMENTATION_ROADMAP](docs/IMPLEMENTATION_ROADMAP.md) | Phase status and next steps |
| [DEVELOPMENT_SETUP](docs/DEVELOPMENT_SETUP.md) | Setup, running, backups, troubleshooting |
| [USER_GUIDE](docs/USER_GUIDE.md) | How to use the workspace day to day |
| [TESTING_STRATEGY](docs/TESTING_STRATEGY.md) | What is tested and how |
| [SECURITY_AND_PRIVACY](docs/SECURITY_AND_PRIVACY.md) | Safeguards and known gaps |
| [DECISIONS/](docs/DECISIONS/) | Architecture decision records |

## Repository layout

```
backend/    FastAPI + SQLAlchemy + Alembic (Python 3.13, managed by uv)
frontend/   Next.js 16 + TypeScript + Tailwind + shadcn/ui + TanStack Query
docs/       Product and technical documentation (the project's source of truth)
docker-compose.yml   PostgreSQL 17 for local development
prompt.md   The original product brief
```
