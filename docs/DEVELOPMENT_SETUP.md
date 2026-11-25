# Development setup

## Prerequisites

| Tool | Version used | Purpose |
| --- | --- | --- |
| Docker Desktop | 29.x | Runs PostgreSQL 17 (optional — see below) |
| uv | 0.13+ | Python 3.13 environment for the backend (`backend/.venv`) |
| Node.js | 20+ (tested on 26) | Frontend |

You never need to activate the Python virtual environment: run backend commands through
`uv run …` (or `make …`). Activating `backend/.venv/bin/activate` also works if you prefer.

## First run

```bash
make setup       # starts the database, creates backend/.env, installs dependencies, migrates
make api         # http://localhost:8010  (OpenAPI docs at /docs)
make web         # http://localhost:3010
```

### Ports

| Service | Port | Change it with |
| --- | --- | --- |
| Web app | 3010 | `frontend/package.json` scripts |
| API | 8010 | `make api` / `uvicorn --port`, plus `API_ORIGIN` for the frontend and `CORS_ORIGINS` for the backend |
| PostgreSQL | 5433 | `POSTGRES_PORT` in `.env` and `DATABASE_URL` in `backend/.env` |

These deliberately avoid the common 3000/8000/5432, which other local projects often use.

### Optional: local voice transcription

```bash
make voice        # installs faster-whisper into backend/.venv
```

The first transcription downloads the Whisper “base” model (~150 MB) from Hugging Face; after that it
runs offline. Settings in `backend/.env`: `TRANSCRIPTION_PROVIDER` (`auto` / `none`),
`WHISPER_MODEL` (`tiny`, `base`, `small`…; larger is more accurate and slower), `VOICE_RETENTION`
(`delete` — default — or `keep`).

### Optional: AI assistant (no new cost)

Choose a mode in **Administration → AI assistant**:

- **Free local model (recommended):** install [Ollama](https://ollama.com), then
  `ollama pull llama3.1:8b` (≈ 5 GB; larger models such as `qwen3:14b` answer better and fit in
  48 GB RAM). Pick the *Ollama* preset, **Save**, then **Test connection**. Private and offline.
- **Organisation AI service:** pick *Organisation AI gateway / Azure OpenAI*, enter its
  OpenAI-compatible address and model, and put the key in `backend/.env` as `AI_API_KEY=…`
  (restart the API). Use only services your organisation approves for this data.
- **Copy and paste:** works with any chat you already use, including a free ChatGPT account (which
  has no API). The app shows the prompt; you paste the answer back.

### Optional: Claude Code sync

Connect each project's folder on its Codebase tab — that is all. Sync reads git and the progress
files Claude Code keeps in the folder (PROGRESS.md, `.claude/issues`, worklogs, backlogs) locally;
no Claude Code configuration is changed (ADR 0009). Direct Claude tools (MCP command and hooks) are
optional under **Administration → Claude Code**; use them only if your organisation allows it. `SYNC_INTERVAL_SECONDS` (default 180, `0` to disable) controls background git sync.

### Seeding your own projects

`make seed-projects` loads project specs from `backend/data/seed/projects/*.json` — milestones,
tasks (completed work keeps its real completion date), decisions, knowledge and read-only document
indexes. The folder is git-ignored because it describes your own work. Re-running is safe: projects
that already exist are skipped. The format is documented at the top of `backend/app/seed_projects.py`.

## Configuration

- `backend/.env` (from `backend/.env.example`): `DATABASE_URL`, `TEST_DATABASE_URL`,
  `CORS_ORIGINS`, `LOG_LEVEL`, `PROJECTS_ROOT` (the recommended projects folder, default
  `~/Projects`; changeable in Administration → Projects folder).
- `frontend/.env.local` (optional, from `frontend/.env.example`): `API_ORIGIN`.
- Root `.env` (optional, from `.env.example`): Docker Compose database credentials and port.

The defaults are local-only development credentials. Never commit `.env` files (they are git-ignored).

## Running without Docker

Use any PostgreSQL 14+ you already have:

```sql
CREATE USER dgs WITH PASSWORD 'choose-a-password';
CREATE DATABASE dgs_workspace OWNER dgs;
CREATE DATABASE dgs_workspace_test OWNER dgs;
```

Then set `DATABASE_URL` and `TEST_DATABASE_URL` in `backend/.env` to point at it (for example
`postgresql+psycopg://dgs:choose-a-password@localhost:5432/dgs_workspace`) and run `make migrate`.

## Backups and restore

```bash
make backup                                    # writes backups/workspace-YYYY-MM-DD-HHMM.dump
docker exec -i dgs-workspace-db pg_restore -U dgs -d dgs_workspace --clean --if-exists < backups/<file>.dump
```

Restoring with `--clean` **replaces** current data — take a fresh backup first. The database
lives in the Docker volume `dgs_pgdata`; `docker compose down` keeps it, `docker compose down -v`
**deletes it permanently**.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| App shows “Server unavailable” | The API is not running. Start it with `make api`, then check `http://localhost:8010/api/health`. |
| `address already in use` | Another program holds the port. `lsof -nP -iTCP:<port> -sTCP:LISTEN` shows which; stop it or change the port (see Ports). |
| `next dev`: “Another next dev server is already running” | A previous dev server for this folder is still running. Stop it (it prints the PID), or use `make web-prod`. |
| Docker: `mkdir /host_mnt/...: operation not permitted` | macOS blocks Docker from folders on the Desktop. The Compose file deliberately uses no bind mounts; do not add any here. |
| Dev overlay: “Could not validate `instant`” on every page | Expected only if `experimental.instantInsights` was removed from `next.config.ts`. Pages render in the browser only, so implicit instant validation is set to `manual-warning`. Restart `make web` after changing the config. |
| Database connection refused | `make db`, then `docker ps` should list `dgs-workspace-db`. |
| Recording says the microphone is blocked | Allow microphone access for `localhost:3010` in the browser's site settings. |
| “Transcription unavailable” | Run `make voice`, restart the API, or type/paste text instead. |
| Folder registration refused | Use a full path to a specific project folder; system folders and your whole home folder are not allowed. On macOS the terminal running the API may need Files & Folders permission. |
| Tests refuse to run | The suite only runs against a database whose name contains `test`. Check `TEST_DATABASE_URL`. |

## Working with Claude Code in this repository

Start each session by reading `README.md`, `docs/IMPLEMENTATION_ROADMAP.md` and the docs for
the module you are changing. A graphify knowledge graph of the code lives in `graphify-out/`
(git-ignored); query it with `/graphify query "…"` instead of re-reading files, and refresh it
with `/graphify . --update` after a change.
