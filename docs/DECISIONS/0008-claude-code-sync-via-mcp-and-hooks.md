# ADR 0008 — Claude Code sync through MCP and hooks; codebases connected read-only

- **Status:** Accepted · 21 November 2026

## Context

The workspace should pick up progress made with Claude Code in each project, notice changes to
the codebase, and let Claude see what is planned — without parsing private data or changing the
user's projects.

## Investigation (what Claude Code actually supports)

- Session transcripts live in `~/.claude/projects/<path-with-non-alphanumerics-as-dashes>/<id>.jsonl`.
  The official docs state the format is **internal and changes between versions; scripts that
  parse it can break**. The installed versions contain no structured to-do/task records.
- **MCP servers** (stdio or HTTP) are the supported way for Claude to call external tools;
  `claude mcp add --scope user …` registers one for all projects, and Claude Code sets
  `CLAUDE_PROJECT_DIR` for the server process. Server `instructions` tell Claude when to use it.
- **Hooks** run commands at documented events (`Stop`, `SessionEnd`, `TaskCompleted`, …) with
  JSON on stdin (`session_id`, `cwd`, `hook_event_name`, `last_assistant_message` on Stop);
  `CLAUDE_PROJECT_DIR` is exported. The `TaskCompleted` payload schema is not fully documented.

## Decision

1. **Do not parse transcripts.** Use only MCP and hooks.
2. **Connected folder per project** (`project_connections`), validated like document folders.
   A background loop (`SYNC_INTERVAL_SECONDS`, default 180) and “Sync now” run read-only git
   (`rev-parse`, `status`, `log`) with fixed arguments, a timeout and no shell. Commits are stored
   as events with message and changed file names only — **no author names, no code**. Non-git
   folders use file modification times.
3. **MCP server** (`backend/app/mcp_server.py`, tools `list_open_tasks`, `report_task_progress`,
   `record_update`) calls the running workspace API; the project is resolved from
   `CLAUDE_PROJECT_DIR`.
4. **Hooks** post Stop/SessionEnd/TaskCompleted payloads to `/api/claude/events` with a private
   workspace token (`X-Workspace-Token`). Session summaries are stored after secret redaction and
   name masking; subagent events are ignored; the hook never blocks Claude (`-m 3 … || true`).
   `TaskCompleted` is read defensively.
5. **Every status change is a suggestion.** Commits or Claude reports that reference a task ID
   (e.g. ISSUE-0001) or match a task title create `task_update` suggestions; unmatched work becomes
   a progress suggestion. Approval applies the change through normal task history.
6. **The user installs the integration** (one `claude mcp add` command and an optional hooks
   snippet shown in Administration). The workspace never edits Claude Code settings or project files.

## Consequences

- Works across Claude Code versions because it relies only on documented interfaces.
- Claude reports what it did only if it uses the tools (helped by MCP instructions and an optional
  CLAUDE.md note) or if hooks are installed; commit-based matching covers work done without either.
- The first sync imports history without suggestions, so old commits do not flood the review queue.
