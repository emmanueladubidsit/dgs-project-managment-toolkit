# DGS Project & Engineering Intelligence Workspace

Local-first project/task workspace. Full brief: `prompt.md` (long — do not reread it wholesale;
the docs below are the source of truth).

## Start every session by reading

1. `README.md`, 2. `docs/IMPLEMENTATION_ROADMAP.md` (status + next steps),
3. only the docs/code for the module you are changing.

Prefer `graphify-out/` for code questions (`/graphify query "…"`); refresh it with
`/graphify . --update` after changes. It is git-ignored.

## Stack and commands

- Backend `backend/`: FastAPI, SQLAlchemy 2, Alembic, Python 3.13 via **uv** (always `uv run …`).
- Frontend `frontend/`: Next.js 16 (Cache Components on — read `node_modules/next/dist/docs/`
  before using unfamiliar APIs), Tailwind 4, shadcn/ui (Radix), TanStack Query.
- DB: Docker PostgreSQL 17 on localhost:5433. Ports: API 8010, web 3010 (3000/8000 belong to
  other projects on this machine — do not use or stop them).
- `make test` · `make check` · `make e2e` (needs API + `make web-prod`).

## Rules

- British English everywhere. Never invent progress, hours, decisions or facts.
- Status and progress are independent; nothing is auto-completed (see ADR 0002).
- All services stay bound to localhost (no auth yet).
- Every increment: implement → test → update docs and the roadmap session log.
- Tests use `dgs_workspace_test` only; never point tests at the real database.
