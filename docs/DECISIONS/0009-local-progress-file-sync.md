# ADR 0009 — Local progress-file sync is the default; Claude Code integration is optional

- **Status:** Accepted · 21 November 2026 · amends ADR 0008 · amended by ADR 0010 (project trackers)

## Context

ADR 0008 relied on registering an MCP server and adding hooks, which changes Claude Code's
configuration (`~/.claude.json`, `~/.claude/settings.json`) and sends workspace task data into
Claude conversations. Organisational policies may forbid either. The workspace must still pick up
progress made with Claude Code without touching its configuration or sending data anywhere.

## Decision

1. **Default: local, read-only progress files.** Each connected folder has `progress_patterns`
   (defaults: `**/PROGRESS.md`, `STATUS.md`, `TODO.md`, `CHANGELOG.md`, `WORKPLAN.md`,
   `.claude/issues/*.md`, `.claude/history/worklog/*.md`, `.claude/history/timeline.md`,
   backlogs and `issues/*.md`). Sync reads them alongside git: no symlinks followed, dependency
   and hidden folders skipped (except `.claude`), secret files skipped, at most 150 files of
   512 KB, depth 7. Patterns must be relative; absolute paths and `..` are rejected.
2. **What counts as a status.** Task IDs (e.g. `AEH-002`, `ISSUE-0004`) in table rows, at the start
   of a line, or in a per-ID file's `Status:` line, plus `- [x]` checklist items. Negative phrases
   (“not started”, “not done”) are read first so they never count as progress. README and template
   files are skipped, so prose explaining a convention cannot change a status.
3. **Only changes are suggested, for approval.** A file's hash and parsed state are stored in
   `file_state`. The first read suggests only items marked done; later reads also suggest
   in-progress items and newly ticked checklist items. New worklogs and updated files appear as
   `progress_file` activity (text secret-redacted and name-masked).
4. **Git scoped to the folder.** When the connected folder is a subfolder of a repository, `git
   status` and `git log` are limited to it (`-- .`).
5. **Direct Claude Code tools are optional and gated.** The MCP server and hooks from ADR 0008
   remain available under *Administration → Claude Code → Optional*, with a warning to check
   organisational policy. `/api/claude/context` (task data out to Claude) is **off by default**
   (`allow_outbound`), returns 403 until enabled, and its output is privacy-cleaned.

## Consequences

- Works with no installation and no Claude Code configuration change; nothing leaves the computer.
- Depends on Claude (or people) keeping progress files in the repo; commits still cover the rest.
- The free-text heuristics can miss unusual formats; patterns are editable per project.
