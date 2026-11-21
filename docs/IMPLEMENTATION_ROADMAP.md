# Implementation roadmap

Last updated: **21 November 2026** (second session). Update this file at the end of every working session.

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | Inspection, foundation, core documentation | ✅ Done |
| 1 | Design system and application shell | ✅ Done |
| 2 | Project management | ✅ Done |
| 3 | Tasks, milestones, workstreams, Kanban, list | ✅ Done |
| 4 | Daily, weekly, monthly planning | ✅ Done (auto-distribution pending) |
| 5 | Activity, work logs and reporting | ✅ Done |
| 6 | Knowledge and research | ✅ Done |
| 7 | Methodologies, playbooks, artefacts, documents | ✅ Done |
| 8 | AI-assisted productivity (provider-independent, suggestions only) | ⏳ Next — review workflow and output slots already exist |
| 9 | Voice and Claude Code integration | Voice ✅ · Claude Code planned |
| 10 | Administration, polish, release | Partly done (health, diagnostics, backup guidance) |

## Session log

### 21 November 2026 (second session) — Phases 6, 7 and voice (9)

Delivered:
- 17 new tables (migration 0002) and 35 new endpoint paths (87 in total).
- **Knowledge & Research**: one table with category templates (ADR 0004), verification status,
  versions and restore, origin/reuse/related project links, task links, evidence/supersedes
  relations, promotion from work logs, global search across all record types (⌘K).
- **Methodologies & Playbooks**: stages/activities/deliverables with classifications, versions,
  publish/deprecate/duplicate/archive, adoption (whole or selected stages) that creates milestones
  and tasks without duplicates, per-project deliverable tracking, create-from-project, and 13
  seeded starter methodologies (`make seed`).
- **Documents & Artefacts**: registered folders, read-only scanning and indexing, text previews,
  links and notes, task links; strict path confinement and secret filtering (ADR 0005).
- **Voice & Writing**: in-browser recorder, optional local Whisper (verified with real speech),
  delete-after-transcription retention, deterministic writing tools, rule-based suggestions with
  duplicate detection and approve/reject/defer review; AI-only outputs refused, not faked (ADR 0006).
- Task panel shows linked knowledge and documents; project workspace gains Methodology and
  Library tabs; “Save to knowledge” on recorded decisions and research.
- Tests: 75 backend, 21 frontend component, 5 end-to-end — all passing.
- Fixed along the way: speech sentence splitting for lower-case transcripts; PyAV/faster-whisper
  incompatibility (pinned `av<16`); a Next.js page-export mistake caught before the build.

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

## Next steps

**Phase 8 — AI-assisted productivity (optional, provider-independent)**
1. `AIProvider` interface (`backend/app/services/ai/`) with a disabled default; configuration via
   environment; no core feature depends on it.
2. Implement the six “needs AI” writing outputs, each showing the context and sources used.
3. AI suggestion generators that write to the existing `suggestions` table (`generator` = provider
   name) so the same review/approve/duplicate workflow applies; AI knowledge drafts saved with
   verification “AI suggestion — awaiting review”.

**Phase 9 — Claude Code activity capture**
1. Research the supported Claude Code hook and session mechanisms first (do not assume APIs).
2. Opt-in capture of summaries only (no raw transcripts by default), secret filtering, and
   suggestions for task updates and troubleshooting guides — all reviewed before saving.

## Backlog and known limitations

- Delivery planning: automatic distribution of tasks across a project's target period (manual
  scheduling and checks work today).
- Configurable task statuses (fixed six today; stages are already configurable).
- Workstream reordering in the UI (positions exist in the API).
- Task dependencies across projects are allowed by the API but only same-project tasks are
  offered in the UI.
- Recurring tasks, time tracking per session, calendar/timeline (Gantt) view.
- Automated accessibility (axe) and responsive-layout tests; CI pipeline; dependency scanning.
- Knowledge: Markdown rendering (content is shown as plain text today); attachments.
- Documents: automatic re-scan; full-text search inside indexed files.
- Voice: speaker labels; more British-spelling rules; streaming transcription.
