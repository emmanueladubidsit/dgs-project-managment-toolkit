"""MCP server that lets Claude Code read a connected project's open tasks and report progress.

Register once for all projects (the workspace shows the exact command with your token):
    claude mcp add --scope user dgs-workspace -e DGS_WORKSPACE_TOKEN=<token> -- \\
        uv run --directory <backend folder> python -m app.mcp_server

The project is identified from CLAUDE_PROJECT_DIR, which Claude Code sets for MCP servers.
Reports become suggestions in the workspace; nothing changes until the user approves.
"""

import os

import httpx
from mcp.server.mcpserver import MCPServer

API = os.environ.get("DGS_WORKSPACE_URL", "http://127.0.0.1:8010").rstrip("/") + "/api"
TOKEN = os.environ.get("DGS_WORKSPACE_TOKEN", "")

server = MCPServer(
    "dgs-workspace",
    instructions=(
        "Connects this folder to the user's DGS Engineering Workspace (project and task tracker). "
        "At the start of work, call list_open_tasks to see the planned tasks for this project. "
        "Whenever you complete or make clear progress on one of those tasks, call "
        "report_task_progress with the task id (or exact title), the new status and a one-sentence "
        "note of what was done. Use record_update for notable decisions or blockers. Reports are "
        "reviewed by the user before anything changes, so report honestly and specifically."
    ),
)


def _project_dir() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _call(method: str, path: str, **kw) -> dict:
    if not TOKEN:
        return {
            "error": "DGS_WORKSPACE_TOKEN is not set for this MCP server. Re-run the setup "
            "command shown in the workspace (Administration → Claude Code)."
        }
    try:
        with httpx.Client(timeout=15) as client:
            r = client.request(method, API + path, headers={"X-Workspace-Token": TOKEN}, **kw)
    except httpx.HTTPError:
        return {"error": f"The workspace is not reachable at {API}. Is it running?"}
    try:
        data = r.json()
    except ValueError:
        return {"error": f"Unexpected response ({r.status_code})."}
    if r.status_code >= 400:
        return {"error": (data.get("error") or {}).get("message", "Request failed.")}
    return data


@server.tool()
def list_open_tasks() -> dict:
    """List the open tasks (id, title, status, priority, milestone, acceptance criteria) of the
    workspace project connected to the current folder."""
    return _call("GET", "/claude/context", params={"project_dir": _project_dir()})


@server.tool()
def report_task_progress(task: str, status: str = "completed", note: str = "") -> dict:
    """Report progress on a workspace task. `task` is the task id or its exact title. `status` is
    one of: completed, in_progress, in_review, blocked. `note` briefly says what was done. The
    report is queued for the user's approval."""
    return _call(
        "POST",
        "/claude/report",
        json={
            "project_dir": _project_dir(),
            "task": task,
            "status": status,
            "note": note or None,
            "session_id": os.environ.get("CLAUDE_SESSION_ID"),
        },
    )


@server.tool()
def record_update(summary: str, kind: str = "progress") -> dict:
    """Record a progress update, decision or blocker (`kind`: progress, decision or blocker) for
    the connected project. Queued for the user's approval."""
    return _call(
        "POST",
        "/claude/update",
        json={"project_dir": _project_dir(), "summary": summary, "kind": kind},
    )


if __name__ == "__main__":
    server.run("stdio")
