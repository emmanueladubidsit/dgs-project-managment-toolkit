# ADR 0001 — Modular monolith on Next.js, FastAPI and PostgreSQL

- **Status:** Accepted · 21 November 2026

## Context

A single-user, local-first MVP that must later deploy to the cloud without a rewrite. The brief
recommends Next.js/TypeScript/Tailwind/shadcn, FastAPI/Pydantic, PostgreSQL/SQLAlchemy/Alembic.

## Decision

- One FastAPI backend organised by module (`api/`, `services/`, `models/`, `schemas/`), one
  Next.js frontend, one PostgreSQL database. No microservices.
- The frontend calls `/api/*` on its own origin; Next.js rewrites to the backend.
- Python managed by **uv** (Python 3.13 — 3.15 is installed but too new for some wheels).
- PostgreSQL 17 in Docker on port **5433** (the host already runs a password-protected
  PostgreSQL 18 on 5432 that we should not depend on), with a named volume and no bind mounts
  (macOS blocks Docker bind mounts from the Desktop folder).
- App ports **3010/8010** because 3000/8000 are used by other local projects.

## Consequences

- Simple to run, test and reason about; module boundaries keep later extraction possible.
- The rewrite means CORS is rarely needed, and the API host can change via `API_ORIGIN`.
- Docker is convenient but not required (see DEVELOPMENT_SETUP → Running without Docker).
