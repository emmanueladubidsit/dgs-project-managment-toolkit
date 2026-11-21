# DGS Project & Engineering Intelligence Workspace

A local-first workspace for managing projects from idea to maintenance: projects, workstreams,
milestones, tasks and subtasks; daily, weekly and monthly planning; work logs; and reports
generated only from what you have actually recorded.

It works fully **without any AI service or API key**. AI, voice and Claude Code integrations are
planned as optional add-ons (see [the roadmap](docs/IMPLEMENTATION_ROADMAP.md)).

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
