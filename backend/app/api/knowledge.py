"""Knowledge & research API, plus global search across the workspace."""

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import Text, cast, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import bad_request, conflict, not_found
from app.models import (
    KnowledgeItem,
    KnowledgeProjectLink,
    KnowledgeRelation,
    KnowledgeTaskLink,
    KnowledgeVersion,
    Methodology,
    Project,
    ProjectDocument,
    Task,
    VoiceNote,
    WorkLog,
)
from app.models.enums import WorkLogKind
from app.models.knowledge import KnowledgeCategory, LinkRole, RelationKind, Verification
from app.schemas.knowledge import (
    CategoryTemplate,
    KnowledgeDetail,
    KnowledgeIn,
    KnowledgeOut,
    KnowledgeUpdate,
    KnowledgeVersionOut,
    ProjectLinkIn,
    ProjectLinkOut,
    RelationIn,
    RelationOut,
    SearchHit,
    TaskLinkIn,
    TaskLinkOut,
    TemplateField,
)
from app.services.knowledge_templates import LABELS, TEMPLATES, clean_fields
from app.services.tasks import now

router = APIRouter(tags=["knowledge"])

VERSIONED = (
    "category",
    "title",
    "summary",
    "content",
    "fields",
    "verification",
    "tags",
    "sources",
    "limitations",
    "reuse_notes",
)


def _get(db: Session, item_id: uuid.UUID) -> KnowledgeItem:
    item = db.get(KnowledgeItem, item_id)
    if not item:
        raise not_found("Knowledge item")
    return item


def _fields(category: KnowledgeCategory, fields: dict) -> dict:
    try:
        return clean_fields(category, fields)
    except ValueError as e:
        raise bad_request(str(e)) from e


def _snapshot(item: KnowledgeItem) -> dict:
    snap = {k: getattr(item, k) for k in VERSIONED}
    snap["category"] = item.category.value
    snap["verification"] = item.verification.value
    return snap


def _out(item: KnowledgeItem) -> KnowledgeOut:
    return KnowledgeOut.model_validate(
        {
            **{k: getattr(item, k) for k in KnowledgeOut.model_fields if k != "projects"},
            "projects": [
                ProjectLinkOut(
                    project_id=link.project_id,
                    project_name=link.project.name,
                    role=link.role,
                    note=link.note,
                    created_at=link.created_at,
                )
                for link in sorted(item.project_links, key=lambda x: x.created_at)
            ],
        }
    )


def _detail(db: Session, item: KnowledgeItem) -> KnowledgeDetail:
    tasks = db.scalars(select(KnowledgeTaskLink).where(KnowledgeTaskLink.item_id == item.id)).all()
    rels = db.scalars(
        select(KnowledgeRelation).where(
            or_(KnowledgeRelation.from_id == item.id, KnowledgeRelation.to_id == item.id)
        )
    ).all()
    relations = []
    for r in rels:
        outgoing = r.from_id == item.id
        other = db.get(KnowledgeItem, r.to_id if outgoing else r.from_id)
        relations.append(
            RelationOut(
                id=r.id,
                kind=r.kind,
                direction="outgoing" if outgoing else "incoming",
                other_id=other.id,
                other_title=other.title,
                other_category=other.category,
                other_verification=other.verification,
            )
        )
    return KnowledgeDetail(
        **_out(item).model_dump(),
        tasks=[
            TaskLinkOut(
                task_id=t.task_id, task_title=t.task.title, project_name=t.task.project.name
            )
            for t in tasks
        ],
        relations=relations,
    )


@router.get("/knowledge/templates", response_model=list[CategoryTemplate])
def templates():
    return [
        CategoryTemplate(
            category=c,
            label=LABELS[c],
            fields=[TemplateField(key=k, label=lbl, hint=h) for k, lbl, h in TEMPLATES.get(c, [])],
        )
        for c in KnowledgeCategory
    ]


@router.get("/knowledge", response_model=list[KnowledgeOut])
def list_knowledge(
    q: str | None = None,
    category: list[KnowledgeCategory] = Query(default=[]),
    verification: list[Verification] = Query(default=[]),
    project_id: uuid.UUID | None = None,
    tag: str | None = None,
    include_archived: bool = False,
    task_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(KnowledgeItem).order_by(KnowledgeItem.updated_at.desc())
    if task_id:
        stmt = stmt.where(
            KnowledgeItem.id.in_(
                select(KnowledgeTaskLink.item_id).where(KnowledgeTaskLink.task_id == task_id)
            )
        )
    if not include_archived:
        stmt = stmt.where(KnowledgeItem.archived_at.is_(None))
    if category:
        stmt = stmt.where(KnowledgeItem.category.in_(category))
    if verification:
        stmt = stmt.where(KnowledgeItem.verification.in_(verification))
    if tag:
        stmt = stmt.where(KnowledgeItem.tags.any(tag))
    if project_id:
        stmt = stmt.where(
            KnowledgeItem.id.in_(
                select(KnowledgeProjectLink.item_id).where(
                    KnowledgeProjectLink.project_id == project_id
                )
            )
        )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                KnowledgeItem.title.ilike(like),
                KnowledgeItem.summary.ilike(like),
                KnowledgeItem.content.ilike(like),
                cast(KnowledgeItem.fields, Text).ilike(like),
            )
        )
    return [_out(i) for i in db.scalars(stmt.limit(500)).unique()]


@router.post("/knowledge", response_model=KnowledgeDetail, status_code=201)
def create_knowledge(body: KnowledgeIn, db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"origin_project_id"})
    data["fields"] = _fields(body.category, body.fields)
    item = KnowledgeItem(**data)
    db.add(item)
    db.flush()
    if body.origin_project_id:
        if not db.get(Project, body.origin_project_id):
            raise bad_request("Origin project does not exist.")
        db.add(
            KnowledgeProjectLink(
                item_id=item.id, project_id=body.origin_project_id, role=LinkRole.ORIGIN
            )
        )
    db.commit()
    db.refresh(item)
    return _detail(db, item)


@router.get("/knowledge/{item_id}", response_model=KnowledgeDetail)
def get_knowledge(item_id: uuid.UUID, db: Session = Depends(get_db)):
    return _detail(db, _get(db, item_id))


@router.patch("/knowledge/{item_id}", response_model=KnowledgeDetail)
def update_knowledge(item_id: uuid.UUID, body: KnowledgeUpdate, db: Session = Depends(get_db)):
    """Each substantive change snapshots the previous version and bumps the version number."""
    item = _get(db, item_id)
    changes = body.model_dump(exclude_unset=True)
    note = changes.pop("change_note", None)
    for k in ("category", "title", "verification", "tags", "fields"):
        if k in changes and changes[k] is None:
            changes.pop(k)
    category = changes.get("category", item.category)
    if "fields" in changes or "category" in changes:
        changes["fields"] = _fields(category, changes.get("fields", item.fields) or {})
    real = {k: v for k, v in changes.items() if getattr(item, k) != v}
    if real:
        db.add(
            KnowledgeVersion(
                item_id=item.id, version=item.version, snapshot=_snapshot(item), change_note=note
            )
        )
        for k, v in real.items():
            setattr(item, k, v)
        item.version += 1
    db.commit()
    db.refresh(item)
    return _detail(db, item)


@router.get("/knowledge/{item_id}/versions", response_model=list[KnowledgeVersionOut])
def list_versions(item_id: uuid.UUID, db: Session = Depends(get_db)):
    _get(db, item_id)
    return db.scalars(
        select(KnowledgeVersion)
        .where(KnowledgeVersion.item_id == item_id)
        .order_by(KnowledgeVersion.version.desc())
    ).all()


@router.post("/knowledge/{item_id}/restore-version/{version}", response_model=KnowledgeDetail)
def restore_version(item_id: uuid.UUID, version: int, db: Session = Depends(get_db)):
    """Restore an earlier version as a new version (history is never rewritten)."""
    _get(db, item_id)
    old = db.scalar(
        select(KnowledgeVersion).where(
            KnowledgeVersion.item_id == item_id, KnowledgeVersion.version == version
        )
    )
    if not old:
        raise not_found("Version")
    snap = dict(old.snapshot)
    return update_knowledge(
        item_id,
        KnowledgeUpdate(
            **{k: snap.get(k) for k in VERSIONED}, change_note=f"Restored version {version}"
        ),
        db,
    )


@router.post("/knowledge/{item_id}/archive", response_model=KnowledgeDetail)
def archive_knowledge(item_id: uuid.UUID, db: Session = Depends(get_db)):
    item = _get(db, item_id)
    item.archived_at = now()
    db.commit()
    return _detail(db, item)


@router.post("/knowledge/{item_id}/restore", response_model=KnowledgeDetail)
def unarchive_knowledge(item_id: uuid.UUID, db: Session = Depends(get_db)):
    item = _get(db, item_id)
    item.archived_at = None
    db.commit()
    return _detail(db, item)


@router.delete("/knowledge/{item_id}", status_code=204)
def delete_knowledge(item_id: uuid.UUID, confirm: bool = False, db: Session = Depends(get_db)):
    item = _get(db, item_id)
    if not confirm:
        raise bad_request(
            "Deleting knowledge is permanent and removes its version history. "
            "Confirm to continue, or archive it instead.",
            code="confirmation_required",
        )
    db.delete(item)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- links
@router.post("/knowledge/{item_id}/projects", response_model=KnowledgeDetail, status_code=201)
def link_project(item_id: uuid.UUID, body: ProjectLinkIn, db: Session = Depends(get_db)):
    item = _get(db, item_id)
    if not db.get(Project, body.project_id):
        raise not_found("Project")
    existing = db.scalar(
        select(KnowledgeProjectLink).where(
            KnowledgeProjectLink.item_id == item_id,
            KnowledgeProjectLink.project_id == body.project_id,
        )
    )
    if existing:
        if existing.role == body.role:
            raise conflict("This knowledge is already linked to that project.")
        if existing.role == LinkRole.ORIGIN:
            raise conflict("That project is this knowledge's origin; its role cannot change.")
        existing.role, existing.note = body.role, body.note
    else:
        if body.role == LinkRole.ORIGIN and any(
            link.role == LinkRole.ORIGIN for link in item.project_links
        ):
            raise conflict("This knowledge already has an origin project.")
        db.add(KnowledgeProjectLink(item_id=item_id, **body.model_dump()))
    db.commit()
    db.refresh(item)
    return _detail(db, item)


@router.delete("/knowledge/{item_id}/projects/{project_id}", response_model=KnowledgeDetail)
def unlink_project(item_id: uuid.UUID, project_id: uuid.UUID, db: Session = Depends(get_db)):
    item = _get(db, item_id)
    link = db.scalar(
        select(KnowledgeProjectLink).where(
            KnowledgeProjectLink.item_id == item_id, KnowledgeProjectLink.project_id == project_id
        )
    )
    if not link:
        raise not_found("Project link")
    db.delete(link)
    db.commit()
    db.refresh(item)
    return _detail(db, item)


@router.post("/knowledge/{item_id}/tasks", response_model=KnowledgeDetail, status_code=201)
def link_task(item_id: uuid.UUID, body: TaskLinkIn, db: Session = Depends(get_db)):
    item = _get(db, item_id)
    if not db.get(Task, body.task_id):
        raise not_found("Task")
    if db.scalar(
        select(KnowledgeTaskLink).where(
            KnowledgeTaskLink.item_id == item_id, KnowledgeTaskLink.task_id == body.task_id
        )
    ):
        raise conflict("This knowledge is already linked to that task.")
    db.add(KnowledgeTaskLink(item_id=item_id, task_id=body.task_id))
    db.commit()
    return _detail(db, item)


@router.delete("/knowledge/{item_id}/tasks/{task_id}", response_model=KnowledgeDetail)
def unlink_task(item_id: uuid.UUID, task_id: uuid.UUID, db: Session = Depends(get_db)):
    item = _get(db, item_id)
    link = db.scalar(
        select(KnowledgeTaskLink).where(
            KnowledgeTaskLink.item_id == item_id, KnowledgeTaskLink.task_id == task_id
        )
    )
    if not link:
        raise not_found("Task link")
    db.delete(link)
    db.commit()
    return _detail(db, item)


@router.post("/knowledge/{item_id}/relations", response_model=KnowledgeDetail, status_code=201)
def add_relation(item_id: uuid.UUID, body: RelationIn, db: Session = Depends(get_db)):
    item = _get(db, item_id)
    if body.to_id == item_id:
        raise bad_request("An item cannot relate to itself.")
    other = _get(db, body.to_id)
    if db.scalar(
        select(KnowledgeRelation).where(
            KnowledgeRelation.from_id == item_id,
            KnowledgeRelation.to_id == body.to_id,
            KnowledgeRelation.kind == body.kind,
        )
    ):
        raise conflict("This relationship already exists.")
    db.add(KnowledgeRelation(from_id=item_id, to_id=body.to_id, kind=body.kind))
    if body.kind == RelationKind.SUPERSEDES:
        other.verification = Verification.OUTDATED  # superseded knowledge is clearly flagged
    db.commit()
    return _detail(db, item)


@router.delete("/knowledge/relations/{relation_id}", status_code=204)
def delete_relation(relation_id: uuid.UUID, db: Session = Depends(get_db)):
    rel = db.get(KnowledgeRelation, relation_id)
    if not rel:
        raise not_found("Relationship")
    db.delete(rel)
    db.commit()
    return Response(status_code=204)


@router.post("/knowledge/from-work-log/{log_id}", response_model=KnowledgeDetail, status_code=201)
def promote_work_log(log_id: uuid.UUID, db: Session = Depends(get_db)):
    """Turn a recorded update into a draft knowledge item, keeping provenance."""
    log = db.get(WorkLog, log_id)
    if not log:
        raise not_found("Work log")
    if db.scalar(select(KnowledgeItem).where(KnowledgeItem.source_work_log_id == log_id)):
        raise conflict("This update has already been promoted to knowledge.")
    summary = log.summary.strip()
    title = summary.splitlines()[0][:120] or "Untitled"
    if log.kind == WorkLogKind.DECISION:
        category, fields = (
            KnowledgeCategory.DECISION,
            {"decision": summary, "decided_on": str(log.entry_date)},
        )
    elif log.kind == WorkLogKind.RESEARCH:
        category, fields = (
            KnowledgeCategory.RESEARCH,
            {"findings": summary, "research_date": str(log.entry_date)},
        )
    else:
        category, fields = KnowledgeCategory.LESSON_LEARNED, {"what_happened": summary}
    item = KnowledgeItem(
        category=category,
        title=title,
        fields=fields,
        verification=Verification.RESEARCH_UNIMPLEMENTED,
        source_work_log_id=log.id,
        tags=[],
    )
    db.add(item)
    db.flush()
    if log.project_id:
        db.add(
            KnowledgeProjectLink(item_id=item.id, project_id=log.project_id, role=LinkRole.ORIGIN)
        )
    if log.task_id:
        db.add(KnowledgeTaskLink(item_id=item.id, task_id=log.task_id))
    db.commit()
    db.refresh(item)
    return _detail(db, item)


# ---------------------------------------------------------------- global search
def _snip(text: str | None, q: str, width: int = 140) -> str | None:
    if not text:
        return None
    i = text.lower().find(q.lower())
    if i < 0:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, i - 40)
    s = text[start : start + width]
    return ("…" if start else "") + s + ("…" if start + width < len(text) else "")


@router.get("/search", response_model=list[SearchHit], tags=["search"])
def search(q: str = Query(min_length=2, max_length=200), db: Session = Depends(get_db)):
    """Case-insensitive search across projects, tasks, knowledge, methodologies, documents,
    updates and voice notes. Archived records are excluded."""
    like = f"%{q.strip()}%"
    hits: list[SearchHit] = []
    for p in db.scalars(
        select(Project)
        .where(
            or_(
                Project.name.ilike(like),
                Project.description.ilike(like),
                Project.objectives.ilike(like),
            )
        )
        .limit(10)
    ).unique():
        hits.append(
            SearchHit(
                type="project",
                id=p.id,
                title=p.name,
                snippet=_snip(p.description, q),
                meta=p.status.value,
            )
        )
    for t in db.scalars(
        select(Task)
        .where(
            Task.archived_at.is_(None), or_(Task.title.ilike(like), Task.description.ilike(like))
        )
        .limit(15)
    ).unique():
        hits.append(
            SearchHit(
                type="task",
                id=t.id,
                title=t.title,
                snippet=_snip(t.description, q),
                project_id=t.project_id,
                project_name=t.project.name,
                meta=t.status.value,
            )
        )
    for k in list_knowledge(
        q=q, category=[], verification=[], project_id=None, tag=None, include_archived=False, db=db
    )[:15]:
        body = k.summary or k.content or " ".join(str(v) for v in k.fields.values())
        hits.append(
            SearchHit(
                type="knowledge",
                id=k.id,
                title=k.title,
                snippet=_snip(body, q),
                meta=f"{k.category.value} · {k.verification.value}",
            )
        )
    for m in db.scalars(
        select(Methodology)
        .where(
            Methodology.archived_at.is_(None),
            or_(Methodology.name.ilike(like), Methodology.purpose.ilike(like)),
        )
        .limit(10)
    ):
        hits.append(
            SearchHit(
                type="methodology",
                id=m.id,
                title=m.name,
                snippet=_snip(m.purpose, q),
                meta=m.kind.value,
            )
        )
    for d in db.scalars(
        select(ProjectDocument)
        .where(
            ProjectDocument.archived_at.is_(None),
            or_(
                ProjectDocument.title.ilike(like),
                ProjectDocument.description.ilike(like),
                ProjectDocument.relative_path.ilike(like),
                ProjectDocument.content.ilike(like),
            ),
        )
        .limit(10)
    ).unique():
        hits.append(
            SearchHit(
                type="document",
                id=d.id,
                title=d.title,
                snippet=_snip(d.description or d.content, q),
                project_id=d.project_id,
                project_name=d.project.name if d.project else None,
                meta=d.category.value,
            )
        )
    for w in db.scalars(
        select(WorkLog)
        .where(WorkLog.summary.ilike(like))
        .order_by(WorkLog.entry_date.desc())
        .limit(10)
    ).unique():
        hits.append(
            SearchHit(
                type="work_log",
                id=w.id,
                title=w.summary.splitlines()[0][:120],
                snippet=_snip(w.summary, q),
                project_id=w.project_id,
                project_name=w.project.name if w.project else None,
                meta=f"{w.kind.value} · {w.entry_date}",
            )
        )
    for v in db.scalars(
        select(VoiceNote)
        .where(
            or_(
                VoiceNote.title.ilike(like),
                VoiceNote.transcript_edited.ilike(like),
                VoiceNote.transcript_raw.ilike(like),
            )
        )
        .limit(10)
    ).unique():
        hits.append(
            SearchHit(
                type="voice_note",
                id=v.id,
                title=v.title,
                snippet=_snip(v.transcript_edited or v.transcript_raw, q),
                project_id=v.project_id,
                project_name=v.project.name if v.project else None,
            )
        )
    return hits
