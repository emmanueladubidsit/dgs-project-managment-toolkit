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
| AI honesty | Unverified knowledge is labelled; AI-only writing outputs are refused rather than faked; voice/text suggestions change nothing until approved. |

## Data and retention

- All data stays in the local PostgreSQL volume `dgs_pgdata`. Nothing is sent to any external service.
- Backups (`make backup`) are written to `backups/`, which must never be committed.
- No telemetry is collected by the app. (Next.js telemetry can be disabled with
  `NEXT_TELEMETRY_DISABLED=1`.)

## Principles for later phases

- AI output is **untrusted until reviewed**: it will only ever create suggestions or drafts, shown
  with their sources, and never be presented as verified fact.
- Claude Code capture will be opt-in, will not store full transcripts by default, and will filter
  secrets, tokens and environment variables.

## Known gaps

- No authentication or authorisation (by design for the single-user MVP).
- The Whisper model is downloaded once from Hugging Face on first use (a network request);
  after that transcription is fully offline.
- No automated dependency-vulnerability scan yet — run `npm audit` and `uv pip list --outdated`
  periodically; add to CI in Phase 10.
- Database credentials in the example files are development defaults; change them if the
  database is reachable by anything other than your machine.
