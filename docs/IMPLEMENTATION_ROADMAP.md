# Implementation roadmap

Last updated: **21 November 2026**. Update this file at the end of every working session.

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | Inspection, foundation, core documentation | ✅ Done |
| 1 | Design system and application shell | ✅ Done |
| 2 | Project management | ✅ Done |
| 3 | Tasks, milestones, workstreams, Kanban, list | ✅ Done |
| 4 | Daily, weekly, monthly planning | ✅ Done (auto-distribution pending) |
| 5 | Activity, work logs and reporting | ✅ Done |
| 6 | Knowledge and research | ⏳ Next |
| 7 | Methodologies, playbooks, artefacts, documents | Planned |
| 8 | AI-assisted productivity (provider-independent, suggestions only) | Planned |
| 9 | Voice and Claude Code integration | Planned |
| 10 | Administration, polish, release | Partly done (health, diagnostics, backup guidance) |

## Session log

### 21 November 2026 — Phases 0–5

Environment found: empty folder containing only the brief (`prompt.md`). Node 26, uv with
Python 3.12–3.15, Docker 29, a password-protected local PostgreSQL 18 on 5432, and other local
projects occupying ports 3000 and 8000.

Delivered:
- Monorepo structure, Docker Compose PostgreSQL 17 (port 5433, persistent volume, localhost-only).
- Backend: FastAPI + SQLAlchemy 2 + Alembic; 11 tables; 52 endpoints; weighted, explained
  progress; task rules (status/progress independence, no auto-completion, cycle-safe hierarchy
  and dependencies, history); planner; plan checks; work logs; deterministic reports; dashboard;
  health and admin.
- Frontend: Next.js 16 (Cache Components) + Tailwind 4 + shadcn/ui (Radix) + TanStack Query;
  design tokens; app shell; dashboard; projects; project workspace (overview, board, backlog,
  milestones, workstreams, plan check, decisions and updates, activity, reports); My Tasks
  (list/board); planner (day/week/month with drag-and-drop scheduling); milestones; reports;
  administration; honest placeholders for later modules.
- Tests: 41 backend, 15 frontend component, 2 Playwright end-to-end — all passing.
- Security hardening: all services bound to localhost after finding the web server and database
  exposed on the LAN by default.

## Next steps (Phase 6 — Knowledge and research)

1. Models + migration: `KnowledgeItem` (category, title, content, verification status, version,
   provenance), `ResearchRecord` (question, objective, sources, findings, options, conclusions,
   recommendations, limitations, outstanding questions, reuse suitability), many-to-many links to
   projects and tasks, `DecisionRecord` with evidence links.
2. Troubleshooting-guide template (problem, symptoms, environment, root cause, steps, commands,
   resolution, verification, prevention).
3. Global search across projects, tasks, knowledge and work logs (PostgreSQL full-text search).
4. “Promote to knowledge” from a research/decision work log.
5. Complete step 10 of the end-to-end journey.

## Backlog and known limitations

- Delivery planning: automatic distribution of tasks across a project's target period (manual
  scheduling and checks work today).
- Configurable task statuses (fixed six today; stages are already configurable).
- Workstream reordering in the UI (positions exist in the API).
- Task dependencies across projects are allowed by the API but only same-project tasks are
  offered in the UI.
- Recurring tasks, time tracking per session, calendar/timeline (Gantt) view.
- Automated accessibility (axe) and responsive-layout tests; CI pipeline; dependency scanning.
- Claude Code integration: research the supported hooks and local data mechanisms before
  designing capture (do not assume APIs).
