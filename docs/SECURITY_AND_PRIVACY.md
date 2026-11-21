# Security and privacy

The workspace is single-user and local-first. It has **no authentication**: anyone who can reach
ports 3010/8010 can read and change data. Every service is therefore bound to **localhost
only**: the web server (`--hostname 127.0.0.1`), the API (uvicorn's default `127.0.0.1`) and
PostgreSQL (`127.0.0.1:5433` in `docker-compose.yml`). Verified: the app is not reachable from
the local network. Do not change these bindings until authentication exists.

## Safeguards in place

| Area | Measure |
| --- | --- |
| Input validation | Pydantic schemas for every request (lengths, ranges, date order); database CHECK constraints as a second line. |
| SQL injection | SQLAlchemy parameterised queries only; no string-built SQL with user input. |
| Cross-site scripting | React escapes all rendered text; no `dangerouslySetInnerHTML`; reports are edited as plain text. |
| Error handling | One error shape; unexpected exceptions are logged server-side and returned as a generic message. |
| Secrets | None in source. Configuration via `.env` files, which are git-ignored; `.env.example` files contain local-only defaults. |
| Destructive actions | Confirmation dialogs; task deletion needs `confirm=true`; project deletion needs the exact name; archive offered instead. |
| Data integrity | Foreign keys with explicit delete behaviour; cycles prevented in hierarchies and dependencies. |
| Diagnostics | The admin endpoint reports versions, sizes and counts only — never credentials or connection strings (tested). |
| Repository hygiene | `.gitignore` excludes `.env*`, database dumps, `backups/`, `recordings/`, build output and `graphify-out/`. |
| CORS | Restricted to the configured frontend origin. |
| File access | Read-only, confined to folders you register (resolved paths, no traversal or symlink escapes); system folders and the whole home folder cannot be registered; secret-looking files are never listed or read; deleting records never touches files ([ADR 0005](DECISIONS/0005-read-only-document-indexing.md)). |
| Links | Only `http(s)://` document links are accepted (no `javascript:`/`file:`); opened with `rel="noopener noreferrer"`. |
| Voice | Local transcription keeps audio on this machine; recordings are deleted immediately after transcription by default and can be deleted at any time; uploads are type- and size-limited; failed uploads are not kept. |
| AI data flow | Off by default. With a local model (Ollama/LM Studio) data never leaves the machine; with a remote service, each request's workspace context is sent to it (the settings page warns). Copy-and-paste mode shows exactly what would be shared. |
| AI secrets | `AI_API_KEY` is read only from `backend/.env` — never stored in the database, logged, or sent to the browser. |
| AI logging | `ai_interactions` stores metadata only (feature, model, sizes, duration, error) — never prompts or answers. |
| Exports | Generated on demand from stored data and streamed to the browser; nothing is written to disk on the server. |
| Connected codebases | Read-only: fixed-argument git commands (`rev-parse`, `status`, `log`) with a timeout and no shell; nothing in the folder is changed (tested). Stores commit messages and changed file names only — never source code or author names. |
| Claude Code progress (default) | Read locally and read-only from progress files in the connected folder (ADR 0009); no Claude Code configuration is changed and nothing is sent anywhere. Secret files skipped, symlinks not followed, size and depth limited. |
| Claude Code tools (optional) | Off unless the user registers them and their organisation allows it. Task data to Claude (`/api/claude/context`) is disabled by default and privacy-cleaned when enabled. Hook and MCP endpoints require a private workspace token; summaries are secret-redacted and name-masked before storage; subagent events ignored; Claude's session transcripts are never read. Every task change from Claude or git is a suggestion awaiting approval. |
| Named individuals | Administration → Privacy lists names to replace with roles in Claude reports, commit messages, AI prompts and exports. Seeded project data uses roles, not names. |
| AI honesty | Unverified knowledge is labelled; AI-only writing outputs are refused rather than faked; voice/text suggestions change nothing until approved. |

## Data and retention

- All data stays in the local PostgreSQL volume `dgs_pgdata`. Nothing is sent to any external service.
- Backups (`make backup`) are written to `backups/`, which must never be committed.
- No telemetry is collected by the app. (Next.js telemetry can be disabled with
  `NEXT_TELEMETRY_DISABLED=1`.)

## Principles for later phases

- AI output is **untrusted until reviewed**: it will only ever create suggestions or drafts, shown
  with their sources, and never be presented as verified fact.
- Claude Code capture is local by default (progress files); direct tools are opt-in, transcripts
  are never read, and secrets, tokens and names are filtered.

## Known gaps

- No authentication or authorisation (by design for the single-user MVP).
- The Whisper model is downloaded once from Hugging Face on first use (a network request);
  after that transcription is fully offline.
- No automated dependency-vulnerability scan yet — run `npm audit` and `uv pip list --outdated`
  periodically; add to CI in Phase 10.
- Database credentials in the example files are development defaults; change them if the
  database is reachable by anything other than your machine.
