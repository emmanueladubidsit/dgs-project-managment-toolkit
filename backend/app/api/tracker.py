"""Project trackers, the recommended projects folder and project discovery (ADR 0010).

- `POST /projects/{id}/tracker/refresh` reads the newest tracker and proposes changes for review.
- The projects folder is where technical projects live; discovery scans it for new projects.
- "Start a new project" is the only place the workspace writes to disk: it creates a new folder
  with a starter tracker and CLAUDE.md, never overwriting anything."""

import re
import uuid
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import claude as claude_api
from app.api import projects as projects_api
from app.config import get_settings
from app.db import get_db
from app.errors import bad_request, conflict, not_found
from app.models import Project, ProjectConnection
from app.models.system import SystemSetting
from app.schemas.project import ProjectCreate
from app.services import files, tracker, tracker_import

router = APIRouter(tags=["tracker"])
TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "tracker"
MARKERS = (".git", "CLAUDE.md", ".claude", "docs/project-management", "pyproject.toml",
           "package.json")  # fmt: skip
FOLDER_NAME_RE = re.compile(r"[^A-Za-z0-9 ._-]")


# ---------------------------------------------------------------- tracker
@router.post("/projects/{project_id}/tracker/refresh")
def refresh(project_id: uuid.UUID, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise not_found("Project")
    conn = db.scalar(select(ProjectConnection).where(ProjectConnection.project_id == project_id))
    if not conn:
        raise bad_request(
            "Connect the project's folder first (Codebase tab), then refresh the tracker.",
            code="not_connected",
        )
    if not Path(conn.path).is_dir():
        raise bad_request("The connected folder is no longer available.", code="folder_missing")
    result = tracker_import.refresh_tracker(db, conn)
    return {**result, "pending": tracker_import.pending_count(db, project_id)}


def _template(template: str, **values: str) -> str:
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    return text


@router.get("/tracker/instructions")
def instructions():
    """The CLAUDE.md section that tells Claude Code how to keep the tracker (to copy into an
    existing project)."""
    text = _template("CLAUDE.md", name="Project name")
    return {"claude_md": text.split("\n", 2)[2].lstrip(), "tracker_dir": tracker.TRACKER_DIR}


# ---------------------------------------------------------------- projects folder
def projects_root(db: Session) -> tuple[str, str]:
    row = db.get(SystemSetting, "projects")
    if row and (row.value or {}).get("root"):
        return row.value["root"], "settings"
    return str(Path(get_settings().projects_root).expanduser()), "default"


def _root_status(root: str) -> dict:
    p = Path(root)
    return {"root": root, "exists": p.is_dir()}


class ProjectsFolderIn(BaseModel):
    root: str = Field(min_length=1, max_length=1000)
    create: bool = False


@router.get("/settings/projects")
def get_projects_folder(db: Session = Depends(get_db)):
    root, source = projects_root(db)
    return {**_root_status(root), "source": source}


@router.put("/settings/projects")
def set_projects_folder(body: ProjectsFolderIn, db: Session = Depends(get_db)):
    raw = Path(body.root.strip()).expanduser()
    if not raw.is_absolute():
        raise bad_request("Use a full (absolute) folder path.", code="invalid_path")
    if not raw.exists():
        if not body.create:
            raise bad_request(
                "That folder does not exist yet. Choose “Create folder” to create it.",
                code="missing_folder",
            )
        try:
            files.validate_root(str(raw.parent))
        except files.PathError:
            # The parent may be the home folder itself (e.g. ~/Projects), which is fine as a
            # parent but must not be registered; anything else must be an allowed location.
            if raw.parent.resolve() != Path.home().resolve():
                raise bad_request(
                    "The folder must be created inside an existing, allowed folder.",
                    code="invalid_path",
                ) from None
        raw.mkdir(exist_ok=True)
    try:
        real = str(files.validate_root(str(raw)))
    except files.PathError as e:
        raise bad_request(str(e), code="invalid_path") from e
    row = db.get(SystemSetting, "projects") or SystemSetting(key="projects", value={})
    row.value = {**(row.value or {}), "root": real}
    db.add(row)
    db.commit()
    return {**_root_status(real), "source": "settings"}


# ---------------------------------------------------------------- discovery
def _visible_dirs(folder: Path):
    try:
        children = sorted(folder.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return []
    return [
        c
        for c in children
        if c.is_dir()
        and not c.is_symlink()
        and not c.name.startswith(".")
        and c.name not in files.SKIP_DIRS
    ]


def _is_project(folder: Path) -> bool:
    return any((folder / m).exists() for m in MARKERS)


def _display_name(folder: Path) -> str:
    readme = folder / "README.md"
    try:
        if readme.is_file() and not readme.is_symlink() and readme.stat().st_size < 512 * 1024:
            for line in files.read_text(readme).splitlines()[:40]:
                if line.startswith("# "):
                    name = line[2:].strip().strip("#").strip()
                    if 0 < len(name) <= 120:
                        return name
    except (OSError, files.PathError):
        pass
    return folder.name


def discover(root: str, connected: set[str]) -> list[dict]:
    """Project folders up to two levels below the root that are not connected yet."""
    base = Path(root)
    found: list[Path] = []
    for child in _visible_dirs(base):
        if _is_project(child):
            found.append(child)
        else:
            found.extend(g for g in _visible_dirs(child) if _is_project(g))
    out = []
    for f in found:
        real = str(f.resolve())
        if real in connected:
            continue
        hit = tracker.find_tracker(real)
        out.append(
            {
                "path": real,
                "relative_path": str(f.relative_to(base)),
                "name": _display_name(f),
                "is_git": (f / ".git").exists(),
                "has_tracker": hit is not None,
                "tracker_file": hit[0] if hit else None,
                "modified_at": date.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
        )
    return out


@router.get("/project-discovery")
def discovery(db: Session = Depends(get_db)):
    root, _ = projects_root(db)
    status = _root_status(root)
    connected = {c.path for c in db.scalars(select(ProjectConnection))}
    if not status["exists"]:
        return {**status, "candidates": [], "connected": 0}
    try:
        real = str(files.validate_root(root))
    except files.PathError as e:
        raise bad_request(str(e), code="invalid_path") from e
    inside = sum(1 for p in connected if Path(p).is_relative_to(real))
    return {**status, "candidates": discover(real, connected), "connected": inside}


class DiscoverAddIn(BaseModel):
    path: str = Field(min_length=1, max_length=1000)
    name: str | None = Field(default=None, min_length=1, max_length=200)


def _create_and_connect(db: Session, name: str, path: str, description: str | None = None):
    summary = projects_api.create_project(ProjectCreate(name=name, description=description), db)
    conn = claude_api.connect(summary.id, claude_api.ConnectionIn(path=path), db)
    pending = tracker_import.pending_count(db, summary.id)
    return {"project_id": str(summary.id), "name": summary.name, "connection": conn,
            "pending": pending}  # fmt: skip


@router.post("/project-discovery/add", status_code=201)
def add_discovered(body: DiscoverAddIn, db: Session = Depends(get_db)):
    """Create a project for a discovered folder and connect it (read only)."""
    root, _ = projects_root(db)
    try:
        real = files.validate_root(body.path)
        base = files.validate_root(root)
    except files.PathError as e:
        raise bad_request(str(e), code="invalid_path") from e
    if not real.is_relative_to(base):
        raise bad_request("Only folders inside the projects folder can be added here.")
    return _create_and_connect(db, body.name or _display_name(real), str(real))


class StartProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    folder_name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=5000)


def _week(monday: date) -> str:
    fri = monday + timedelta(days=4)
    if monday.month == fri.month:
        return f"Mon {monday.day} to Fri {fri.day} {fri:%b}"
    return f"Mon {monday.day} {monday:%b} to Fri {fri.day} {fri:%b}"


@router.post("/project-discovery/start", status_code=201)
def start_project(body: StartProjectIn, db: Session = Depends(get_db)):
    """Create a new project folder in the projects folder with a starter tracker and CLAUDE.md,
    then create and connect the project. Existing files are never overwritten."""
    root, _ = projects_root(db)
    try:
        base = files.validate_root(root)
    except files.PathError as e:
        raise bad_request(
            f"The projects folder is not available ({e}) Set it in Administration.",
            code="invalid_path",
        ) from e
    folder_name = FOLDER_NAME_RE.sub("", (body.folder_name or body.name)).strip(" .")
    folder_name = re.sub(r"\s+", "-", folder_name)
    if not folder_name:
        raise bad_request("Choose a folder name using letters, numbers, spaces, '-' or '_'.")
    target = base / folder_name
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise conflict(f"“{folder_name}” already exists in the projects folder and is not empty.")
    today = date.today()
    monday = tracker.working_day(today) - timedelta(days=tracker.working_day(today).weekday())
    tracker_text = _template(
        "PROGRESS-AND-PLAN.md",
        name=body.name,
        written=f"{today:%a} {today.day} {today:%b %Y}",
        week1=_week(monday),
    )
    claude_text = _template("CLAUDE.md", name=body.name)
    target.mkdir(exist_ok=True)
    docs = target / tracker.TRACKER_DIR
    docs.mkdir(parents=True, exist_ok=True)
    for path, text in (
        (docs / f"PROGRESS-AND-PLAN-{today.isoformat()}.md", tracker_text),
        (target / "CLAUDE.md", claude_text),
    ):
        with open(path, "x", encoding="utf-8") as fh:  # "x": never overwrite
            fh.write(text)
    out = _create_and_connect(db, body.name, str(target.resolve()), body.description)
    return {**out, "path": str(target.resolve())}
