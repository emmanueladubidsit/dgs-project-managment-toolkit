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
| 8 | AI-assisted productivity (provider-independent, suggestions only) | ✅ Done (+ stakeholder exports) |
| 9 | Voice and Claude Code integration | ✅ Done (MCP + hooks, read-only codebase sync) |
| 10 | Administration, polish, release | Partly done (health, diagnostics, backup guidance) |

## Session log

### 23 November 2026 — dev overlay fix

- Fixed: every page showed a dev-only “Could not validate `instant`” overlay. Pages deliberately
  render in the browser only (`BrowserOnly` in `app-shell.tsx`), which Next 16's implicit
  instant-navigation check cannot prerender. `next.config.ts` now sets
  `experimental.instantInsights.validationLevel: "manual-warning"`, so only segments that export
  `instant` are validated. Production builds were never affected.
- Verified: all ten main routes load in `next dev` with no errors; type-check passes.

### 21 November 2026 (fifth session) — policy-safe local Claude sync

- Claude Code progress now comes from progress files already in each connected folder, read
  locally and read-only (ADR 0009). No Claude Code configuration is touched and nothing is sent
  anywhere; the MCP/hooks route is optional, behind a policy warning, with task sharing off.
- Git sync scoped to the connected subfolder (it previously showed the whole repository).
- Fixed: “not started” read as progress; README prose changing a status; duplicate-event error
  when re-reading files.
- Real folders: 38 progress files (AI Risk Assessment Toolkit), 86 (Agent Evaluation Harness).
- Tests: 102 backend, 21 frontend, 9 end-to-end — all passing.

### 21 November 2026 (fourth session) — seeded projects, privacy and Claude Code sync

- Seeded three real projects from their own records (git-ignored specs, `make seed-projects`);
  individuals' names masked as roles, with your later edits preserved.
- Claude Code integration researched against the official docs (ADR 0008): MCP server and hooks,
  no transcript parsing; read-only connected folders with git sync and auto-sync.
- Privacy rules (names → roles) applied to Claude reports, commits, AI prompts and exports.
- Tests: 99 backend, 21 frontend, 9 end-to-end; MCP server verified over stdio; hook command
  verified with a Stop payload.

### 21 November 2026 (third session) — Phase 8 AI assistant and stakeholder exports

- AI provider layer with three no-new-cost modes (off / OpenAI-compatible service / copy-and-paste)
  and presets for Ollama, LM Studio, organisation/Azure, Gemini, Groq and OpenRouter (ADR 0007).
- Assistant page (Ask, Write, Notes → tasks, New project from an idea, Research draft) and AI in
  context: subtask suggestions, voice-note AI outputs and suggestions, report executive summaries.
- Exports to Word, PDF and PowerPoint for reports, project status updates, briefs, full project
  reports and knowledge items (visually checked).
- Tests: 90 backend (AI against a fake OpenAI-compatible server), 21 frontend, 8 end-to-end.
- Fixed along the way: 4:3 slide layout on 16:9 decks; assistant suggestions not disappearing
  after approval; a render-time mutation flagged by the React lint rules.

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

**Set up a model** — install Ollama and pull a model (or configure the organisation service),
then use *Test connection* in Administration.

**Claude Code progress** — nothing to set up: keep working with Claude in a connected folder and
review the suggestions. Direct Claude tools stay optional, subject to organisational policy.

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
- AI: streaming answers; saving Assistant conversations; AI-assisted delivery planning (distribute
  tasks over the target period); semantic search over knowledge (embeddings).
- Exports: branded templates (logo, organisation colours); charts in status decks.
