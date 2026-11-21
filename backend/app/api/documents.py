"""Documents & artefacts: registered folders (read-only), indexed files, links and notes."""

import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError, bad_request, conflict, not_found
from app.models import DocumentRoot, DocumentTaskLink, Project, ProjectDocument, Task
from app.models.documents import DocumentCategory
from app.schemas.documents import (
    DocumentIn,
    DocumentOut,
    DocumentUpdate,
    PreviewOut,
    RegisterIn,
    RootIn,
    RootOut,
    ScannedFile,
    ScanResult,
    TaskLink,
)
from app.services import files
from app.services.tasks import now

router = APIRouter(tags=["documents"])


def _path_error(e: files.PathError) -> AppError:
    return bad_request(str(e), code="invalid_path")


def _root(db: Session, rid: uuid.UUID) -> DocumentRoot:
    r = db.get(DocumentRoot, rid)
    if not r:
        raise not_found("Folder")
    return r


def _doc(db: Session, did: uuid.UUID) -> ProjectDocument:
    d = db.get(ProjectDocument, did)
    if not d:
        raise not_found("Document")
    return d


def _doc_out(db: Session, d: ProjectDocument, with_tasks: bool = False) -> DocumentOut:
    available = None
    if d.root_id and d.relative_path:
        try:
            available = files.safe_file(d.root.path, d.relative_path).is_file()
        except files.PathError:
            available = False
    tasks = []
    if with_tasks:
        tasks = [
            {"task_id": str(link.task_id), "task_title": link.task.title}
            for link in db.scalars(
                select(DocumentTaskLink).where(DocumentTaskLink.document_id == d.id)
            )
        ]
    return DocumentOut.model_validate(
        {
            **{k: getattr(d, k) for k in DocumentOut.model_fields if hasattr(d, k)},
            "project_name": d.project.name if d.project else None,
            "root_name": d.root.name if d.root else None,
            "source": "file" if d.relative_path else "link" if d.url else "note",
            "file_available": available,
            "tasks": tasks,
        }
    )


# ---------------------------------------------------------------- roots
@router.get("/document-roots", response_model=list[RootOut])
def list_roots(db: Session = Depends(get_db)):
    roots = list(db.scalars(select(DocumentRoot).order_by(DocumentRoot.name)).unique())
    counts = Counter(
        db.scalars(
            select(ProjectDocument.root_id).where(
                ProjectDocument.root_id.in_([r.id for r in roots])
            )
        )
    )
    return [
        RootOut.model_validate(
            {
                **{k: getattr(r, k) for k in RootOut.model_fields if hasattr(r, k)},
                "project_name": r.project.name if r.project else None,
                "document_count": counts.get(r.id, 0),
                "available": Path(r.path).is_dir(),
            }
        )
        for r in roots
    ]


@router.post("/document-roots", response_model=RootOut, status_code=201)
def register_root(body: RootIn, db: Session = Depends(get_db)):
    try:
        real = files.validate_root(body.path)
    except files.PathError as e:
        raise _path_error(e) from e
    if body.project_id and not db.get(Project, body.project_id):
        raise bad_request("Project does not exist.")
    if db.scalar(select(DocumentRoot).where(DocumentRoot.path == str(real))):
        raise conflict("That folder is already registered.")
    r = DocumentRoot(name=body.name.strip(), path=str(real), project_id=body.project_id)
    db.add(r)
    db.commit()
    return RootOut.model_validate(
        {
            **{k: getattr(r, k) for k in RootOut.model_fields if hasattr(r, k)},
            "project_name": r.project.name if r.project else None,
        }
    )


@router.delete("/document-roots/{rid}", status_code=204)
def unregister_root(rid: uuid.UUID, confirm: bool = False, db: Session = Depends(get_db)):
    """Removes the folder registration and its index entries. Files on disk are untouched."""
    r = _root(db, rid)
    docs = list(db.scalars(select(ProjectDocument).where(ProjectDocument.root_id == rid)))
    if docs and not confirm:
        raise bad_request(
            f"This removes {len(docs)} indexed document record(s). Your files are "
            "not affected. Confirm to continue.",
            code="confirmation_required",
        )
    for d in docs:
        db.delete(d)
    db.delete(r)
    db.commit()
    return Response(status_code=204)


@router.post("/document-roots/{rid}/scan", response_model=ScanResult)
def scan_root(rid: uuid.UUID, db: Session = Depends(get_db)):
    """List files in the folder (read-only) and refresh metadata of registered documents."""
    r = _root(db, rid)
    if not Path(r.path).is_dir():
        raise bad_request("The folder is no longer available at its registered path.")
    found, truncated = files.scan(r.path)
    registered = {
        d.relative_path: d
        for d in db.scalars(select(ProjectDocument).where(ProjectDocument.root_id == rid))
    }
    out = []
    for f in found:
        d = registered.get(f.relative_path)
        if d:
            d.size_bytes, d.file_modified_at = f.size_bytes, f.modified_at
        out.append(
            ScannedFile(
                relative_path=f.relative_path,
                size_bytes=f.size_bytes,
                modified_at=f.modified_at,
                suggested_category=f.suggested_category,
                document_id=d.id if d else None,
            )
        )
    r.last_scanned_at = now()
    db.commit()
    return ScanResult(
        root_id=rid,
        files=out,
        truncated=truncated,
        skipped_note=(
            "Hidden files, dependency and build folders (.git, node_modules, .venv…) and "
            "files that look like secrets (.env, keys, credentials) are never listed."
        ),
    )


@router.post("/document-roots/{rid}/register", response_model=list[DocumentOut], status_code=201)
def register_files(rid: uuid.UUID, body: RegisterIn, db: Session = Depends(get_db)):
    r = _root(db, rid)
    project_id = body.project_id or r.project_id
    if project_id and not db.get(Project, project_id):
        raise bad_request("Project does not exist.")
    created = []
    for rel in dict.fromkeys(body.paths):
        try:
            path = files.safe_file(r.path, rel)
        except files.PathError as e:
            raise _path_error(e) from e
        if not path.is_file():
            raise bad_request(f"Not a file: {rel}")
        rel_norm = str(path.relative_to(Path(r.path).resolve()))
        if db.scalar(
            select(ProjectDocument).where(
                ProjectDocument.root_id == rid, ProjectDocument.relative_path == rel_norm
            )
        ):
            continue
        st = path.stat()
        d = ProjectDocument(
            title=path.stem.replace("_", " ").replace("-", " ").strip() or path.name,
            category=body.category or files.guess_category(rel_norm),
            project_id=project_id,
            root_id=rid,
            relative_path=rel_norm,
            size_bytes=st.st_size,
            file_modified_at=datetime.fromtimestamp(st.st_mtime, UTC),
            tags=[],
        )
        db.add(d)
        created.append(d)
    db.commit()
    return [_doc_out(db, d) for d in created]


# ---------------------------------------------------------------- documents
@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    project_id: uuid.UUID | None = None,
    root_id: uuid.UUID | None = None,
    category: list[DocumentCategory] = Query(default=[]),
    q: str | None = None,
    include_archived: bool = False,
    task_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(ProjectDocument).order_by(ProjectDocument.updated_at.desc())
    if task_id:
        stmt = stmt.where(
            ProjectDocument.id.in_(
                select(DocumentTaskLink.document_id).where(DocumentTaskLink.task_id == task_id)
            )
        )
    if not include_archived:
        stmt = stmt.where(ProjectDocument.archived_at.is_(None))
    if project_id:
        stmt = stmt.where(ProjectDocument.project_id == project_id)
    if root_id:
        stmt = stmt.where(ProjectDocument.root_id == root_id)
    if category:
        stmt = stmt.where(ProjectDocument.category.in_(category))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                ProjectDocument.title.ilike(like),
                ProjectDocument.description.ilike(like),
                ProjectDocument.relative_path.ilike(like),
                ProjectDocument.content.ilike(like),
            )
        )
    return [_doc_out(db, d) for d in db.scalars(stmt.limit(1000)).unique()]


@router.post("/documents", response_model=DocumentOut, status_code=201)
def create_document(body: DocumentIn, db: Session = Depends(get_db)):
    """Create a link to an external document, or a simple in-app text document."""
    if body.project_id and not db.get(Project, body.project_id):
        raise bad_request("Project does not exist.")
    d = ProjectDocument(**body.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return _doc_out(db, d, with_tasks=True)


@router.get("/documents/{did}", response_model=DocumentOut)
def get_document(did: uuid.UUID, db: Session = Depends(get_db)):
    return _doc_out(db, _doc(db, did), with_tasks=True)


@router.patch("/documents/{did}", response_model=DocumentOut)
def update_document(did: uuid.UUID, body: DocumentUpdate, db: Session = Depends(get_db)):
    d = _doc(db, did)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("project_id") and not db.get(Project, changes["project_id"]):
        raise bad_request("Project does not exist.")
    if d.relative_path and changes.get("content"):
        raise bad_request("Indexed files are read-only here; edit them in their own folder.")
    for k, v in changes.items():
        if v is None and k in ("title", "category", "status", "tags"):
            continue
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return _doc_out(db, d, with_tasks=True)


@router.get("/documents/{did}/preview", response_model=PreviewOut)
def preview(did: uuid.UUID, db: Session = Depends(get_db)):
    d = _doc(db, did)
    if not (d.root_id and d.relative_path):
        return PreviewOut(document_id=d.id, text=d.content or "")
    try:
        text = files.read_text(files.safe_file(d.root.path, d.relative_path))
    except files.PathError as e:
        raise _path_error(e) from e
    return PreviewOut(document_id=d.id, text=text)


@router.post("/documents/{did}/archive", response_model=DocumentOut)
def archive_document(did: uuid.UUID, db: Session = Depends(get_db)):
    d = _doc(db, did)
    d.archived_at = now()
    db.commit()
    return _doc_out(db, d)


@router.post("/documents/{did}/restore", response_model=DocumentOut)
def restore_document(did: uuid.UUID, db: Session = Depends(get_db)):
    d = _doc(db, did)
    d.archived_at = None
    db.commit()
    return _doc_out(db, d)


@router.delete("/documents/{did}", status_code=204)
def delete_document(did: uuid.UUID, db: Session = Depends(get_db)):
    """Removes the workspace record only. A file on disk is never deleted."""
    d = _doc(db, did)
    db.delete(d)
    db.commit()
    return Response(status_code=204)


@router.post("/documents/{did}/tasks", response_model=DocumentOut, status_code=201)
def link_task(did: uuid.UUID, body: TaskLink, db: Session = Depends(get_db)):
    d = _doc(db, did)
    if not db.get(Task, body.task_id):
        raise not_found("Task")
    if db.scalar(
        select(DocumentTaskLink).where(
            DocumentTaskLink.document_id == did, DocumentTaskLink.task_id == body.task_id
        )
    ):
        raise conflict("This document is already linked to that task.")
    db.add(DocumentTaskLink(document_id=did, task_id=body.task_id))
    db.commit()
    return _doc_out(db, d, with_tasks=True)


@router.delete("/documents/{did}/tasks/{task_id}", response_model=DocumentOut)
def unlink_task(did: uuid.UUID, task_id: uuid.UUID, db: Session = Depends(get_db)):
    d = _doc(db, did)
    link = db.scalar(
        select(DocumentTaskLink).where(
            DocumentTaskLink.document_id == did, DocumentTaskLink.task_id == task_id
        )
    )
    if not link:
        raise not_found("Task link")
    db.delete(link)
    db.commit()
    return _doc_out(db, d, with_tasks=True)
