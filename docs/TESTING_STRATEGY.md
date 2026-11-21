# Testing strategy

Testing is part of every increment. Current status: **all suites passing**.

| Suite | Tool | Command | Count |
| --- | --- | --- | --- |
| Backend API, rules and calculations | pytest + FastAPI TestClient | `cd backend && uv run pytest` | 41 |
| Frontend components and helpers | Vitest + Testing Library (jsdom) | `cd frontend && npm test` | 15 |
| End-to-end user journey | Playwright (Chromium) | `cd frontend && npx playwright test` | 2 |

## Backend (`backend/tests`)

- Runs against the separate `dgs_workspace_test` database; the suite **refuses to start** if the
  database name does not contain `test`. Real Alembic migrations are applied, so migrations are
  tested too; data is truncated after every test.
- Covers: project CRUD, validation, search, archive/restore, name-confirmed deletion; stage
  seeding; milestone lifecycle and warnings; workstream deletion keeping tasks; task defaults,
  history, no-op updates, status/progress independence, completion and reopening; subtasks never
  auto-completing parents; parent and dependency cycle rejection; cross-project reference
  rejection; blocked detection; filters and sorting; comments; bulk update; archive and confirmed
  deletion; Kanban reordering; weighted progress rules; day/week/month planning, capacity and
  carry-forward; plan checks; work logs; reports containing only real data; dashboard; admin info
  without secrets; consistent error bodies.

## Frontend (`frontend/src/**/*.test.tsx`)

British date formatting and local-date parsing; status/priority badges and their accessible
names; progress bars (ARIA, clamping, explanation); error state with retry; task table empty
state, overdue and dependency flags, and a bulk update that sends the right API request; Kanban
column placement and ordering; filter bar behaviour; activity-history wording.

## End-to-end (`frontend/e2e/journey.spec.ts`)

Runs against the running app (`make api` and `make web-prod`). Data is uniquely named and deleted
afterwards. The journey: create a project → workstream → milestone → task (linked, estimated, with
acceptance criteria) → subtask → schedule for today → move to In Progress (verified on the board
and in the daily planner) → record a progress update and a research note → generate a weekly report
containing that data → open a fresh browser session and confirm everything persisted. A second
test covers failure handling (unknown project, type-the-name delete confirmation).

**Restart persistence** was additionally verified manually: a record created via the API survived
stopping the API and restarting the PostgreSQL container.

## Not yet covered (known gaps)

- Step 10 of the brief's journey (“create a reusable knowledge item”) awaits Phase 6.
- Drag and drop is exercised by unit logic and manually, not by Playwright.
- No automated responsive-layout or accessibility audit (axe) yet — planned for Phase 10.
- No load or performance testing (single-user local app).
