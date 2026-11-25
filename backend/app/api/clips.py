"""The "Keep to DGS" browser extension (ADR 0011): keep chosen AI answers in a project, and
write code into the project's connected folder after a preview.

Every endpoint needs the workspace token (`X-Workspace-Token`), so other local programs cannot
post content or write files. File writes are also off until enabled in Administration."""

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import projects as projects_api
from app.api.claude import require_token
from app.db import get_db
from app.errors import AppError, bad_request, not_found
from app.models import CodeEvent, Project, ProjectConnection, ProjectDocument, WorkLog
from app.models.documents import DocumentCategory
from app.models.enums import ProjectStatus, WorkLogKind
from app.models.system import SystemSetting
from app.schemas.project import ProjectCreate
from app.services import file_writes, privacy
from app.services.tasks import now

router = APIRouter(tags=["clips"], dependencies=[Depends(require_token)])
TOOLS = {"chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini", "copilot": "Copilot"}


def file_writes_allowed(db: Session) -> bool:
    row = db.get(SystemSetting, "claude")
    return bool((row.value or {}).get("allow_file_writes")) if row else False


# ---------------------------------------------------------------- projects for the picker
@router.get("/clips/projects")
def clip_projects(db: Session = Depends(get_db)):
    connected = {c.project_id for c in db.scalars(select(ProjectConnection))}
    rows = db.scalars(
        select(Project).where(Project.status != ProjectStatus.ARCHIVED).order_by(Project.name)
    )
    return {
        "projects": [
            {"id": str(p.id), "name": p.name, "has_folder": p.id in connected} for p in rows
        ],
        "file_writes_allowed": file_writes_allowed(db),
    }


# ---------------------------------------------------------------- keep answers
class ClipItem(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    kind: Literal["answer", "code", "selection"] = "answer"
    tool: str = Field(default="other", max_length=30)
    url: str | None = Field(default=None, max_length=1000)
    language: str | None = Field(default=None, max_length=40)


class ClipIn(BaseModel):
    project_id: uuid.UUID | None = None
    new_project_name: str | None = Field(default=None, min_length=1, max_length=200)
    save_as: Literal["note", "update"] = "note"
    title: str | None = Field(default=None, max_length=300)
    items: list[ClipItem] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def _one_project(self):
        if not self.project_id and not self.new_project_name:
            raise ValueError("Choose a project or enter a name for a new project.")
        return self


def _tool(t: str) -> str:
    return TOOLS.get(t.lower(), t[:30] or "AI tool")


def _title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip().lstrip("#*->` ").strip()
        if line:
            return line[:120] + ("…" if len(line) > 120 else "")
    return "Kept AI answer"


def _as_markdown(item: ClipItem) -> str:
    if item.kind == "code":
        return f"```{item.language or ''}\n{item.text.rstrip()}\n```"
    return item.text.strip()


@router.post("/clips", status_code=201)
def keep(body: ClipIn, db: Session = Depends(get_db)):
    """Store only what the user ticked. One note (document) or one update (work log) per keep."""
    if body.project_id:
        project = db.get(Project, body.project_id)
        if not project:
            raise not_found("Project")
        project_id, created_project = project.id, False
    else:
        summary = projects_api.create_project(ProjectCreate(name=body.new_project_name), db)
        project_id, created_project = summary.id, True
    tools = sorted({_tool(i.tool) for i in body.items})
    urls = [i.url for i in body.items if i.url]
    content = "\n\n---\n\n".join(_as_markdown(i) for i in body.items)
    content = privacy.clean(db, content)
    source = f"Kept from {', '.join(tools)} on {date.today():%d %b %Y}" + (
        f" · {urls[0]}" if urls else ""
    )
    title = privacy.clean(db, body.title or _title(body.items[0].text), 300)
    if body.save_as == "note":
        doc = ProjectDocument(
            title=title,
            category=DocumentCategory.RESEARCH,
            description=source,
            project_id=project_id,
            url=urls[0] if urls and urls[0].startswith(("http://", "https://")) else None,
            content=content,
            tags=["ai-clip", *[t.lower() for t in tools]][:10],
        )
        db.add(doc)
        db.commit()
        return {"saved_as": "note", "id": str(doc.id), "project_id": str(project_id),
                "created_project": created_project}  # fmt: skip
    log = WorkLog(
        entry_date=date.today(),
        kind=WorkLogKind.PROGRESS,
        summary=f"{title}\n\n{content}\n\n_{source}_",
        project_id=project_id,
    )
    db.add(log)
    db.commit()
    return {"saved_as": "update", "id": str(log.id), "project_id": str(project_id),
            "created_project": created_project}  # fmt: skip


# ---------------------------------------------------------------- add code to a file
class FileIn(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=600_000)


class FileWriteIn(FileIn):
    expected_sha256: str | None = Field(default=None, max_length=64)


def _folder(db: Session, project_id: uuid.UUID) -> ProjectConnection:
    if not db.get(Project, project_id):
        raise not_found("Project")
    c = db.scalar(select(ProjectConnection).where(ProjectConnection.project_id == project_id))
    if not c:
        raise bad_request(
            "This project has no connected folder. Connect it on the project's Codebase tab first.",
            code="not_connected",
        )
    return c


@router.post("/projects/{project_id}/files/preview")
def preview_file(project_id: uuid.UUID, body: FileIn, db: Session = Depends(get_db)):
    c = _folder(db, project_id)
    try:
        return {**file_writes.preview(c.path, body.path, body.content),
                "writes_allowed": file_writes_allowed(db)}  # fmt: skip
    except file_writes.WriteError as e:
        raise bad_request(str(e), code="invalid_path") from e


@router.post("/projects/{project_id}/files/write")
def write_file(project_id: uuid.UUID, body: FileWriteIn, db: Session = Depends(get_db)):
    c = _folder(db, project_id)
    if not file_writes_allowed(db):
        raise AppError(
            403,
            "writes_disabled",
            "Writing files is switched off. Turn on “Allow the browser extension to write files” "
            "in Administration → Browser extension.",
        )
    try:
        out = file_writes.write(c.path, body.path, body.content, body.expected_sha256)
    except file_writes.WriteError as e:
        raise AppError(409 if "changed" in str(e) else 400, "write_refused", str(e)) from e
    stamp = now()
    db.add(
        CodeEvent(
            connection_id=c.id,
            project_id=project_id,
            kind="file_written",
            ref=f"{out['path']}@{stamp.isoformat()}"[:200],
            title=f"{'Created' if out['created'] else 'Updated'} {out['path']} (browser extension)",
            detail={"files": [out["path"]], "bytes": out["bytes"]},
            occurred_at=stamp,
        )
    )
    c.last_activity_at = stamp
    db.commit()
    return out
