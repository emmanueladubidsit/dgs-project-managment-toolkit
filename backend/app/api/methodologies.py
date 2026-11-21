"""Methodology library, versioning, adoption by projects and creation from past projects."""

import re
import uuid
from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import bad_request, conflict, not_found
from app.models import (
    DeliverableDefinition,
    Methodology,
    MethodologyActivity,
    MethodologyStage,
    MethodologyVersion,
    Milestone,
    Project,
    ProjectDeliverable,
    ProjectDocument,
    ProjectMethodology,
    Task,
)
from app.models.methodology import Classification, MethodologyKind, MethodologyStatus
from app.schemas.methodology import (
    AdoptIn,
    AdoptionOut,
    AdoptionRef,
    DeliverableIn,
    DuplicateIn,
    FromProjectIn,
    MethodologyCreate,
    MethodologyDetail,
    MethodologyMeta,
    MethodologySummary,
    MethodologyVersionOut,
    ProjectDeliverableOut,
    ProjectDeliverableUpdate,
    PublishIn,
    StageIn,
    StructureIn,
)
from app.services.tasks import now, record

router = APIRouter(tags=["methodologies"])

META = (
    "name",
    "kind",
    "purpose",
    "when_to_use",
    "prerequisites",
    "tools",
    "dependencies",
    "common_risks",
    "completion_criteria",
    "limitations",
)


def _get(db: Session, mid: uuid.UUID) -> Methodology:
    m = db.get(Methodology, mid)
    if not m:
        raise not_found("Methodology")
    return m


def slugify(name: str, db: Session) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:100] or "methodology"
    slug, n = base, 2
    while db.scalar(select(Methodology.id).where(Methodology.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    return slug


def snapshot(m: Methodology) -> dict:
    return {
        **{k: (getattr(m, k).value if k == "kind" else getattr(m, k)) for k in META},
        "stages": [
            {
                "name": s.name,
                "description": s.description,
                "validation_criteria": s.validation_criteria,
                "activities": [
                    {
                        "title": a.title,
                        "instructions": a.instructions,
                        "expected_output": a.expected_output,
                    }
                    for a in s.activities
                ],
            }
            for s in m.stages
        ],
        "deliverables": [
            {
                "name": d.name,
                "description": d.description,
                "classification": d.classification.value,
                "stage_index": next(
                    (i for i, s in enumerate(m.stages) if s.id == d.stage_id), None
                ),
            }
            for d in m.deliverables
        ],
    }


def _bump(db: Session, m: Methodology, note: str | None) -> None:
    db.add(
        MethodologyVersion(
            methodology_id=m.id, version=m.version, snapshot=snapshot(m), change_note=note
        )
    )
    m.version += 1


def build_structure(m: Methodology, stages: list[StageIn], deliverables: list[DeliverableIn]):
    """Replace a methodology's stages, activities and deliverables."""
    m.stages.clear()
    m.deliverables.clear()
    keyed: dict[str, MethodologyStage] = {}
    for i, s in enumerate(stages):
        stage = MethodologyStage(
            position=i,
            name=s.name,
            description=s.description,
            validation_criteria=s.validation_criteria,
        )
        stage.activities = [
            MethodologyActivity(
                position=j,
                title=a.title,
                instructions=a.instructions,
                expected_output=a.expected_output,
            )
            for j, a in enumerate(s.activities)
        ]
        m.stages.append(stage)
        keyed[s.key or str(i)] = stage
        keyed[str(i)] = stage
    for i, d in enumerate(deliverables):
        if d.stage_key is not None and d.stage_key not in keyed:
            raise bad_request(f"Deliverable “{d.name}” refers to an unknown stage.")
        stage = keyed.get(d.stage_key) if d.stage_key is not None else None
        m.deliverables.append(
            DeliverableDefinition(
                position=i,
                name=d.name,
                description=d.description,
                classification=d.classification,
                template_id=d.template_id,
                stage=stage,
            )
        )


def _summaries(db: Session, items: list[Methodology]) -> list[MethodologySummary]:
    if not items:
        return []
    ids = [m.id for m in items]
    adoptions = Counter(
        db.scalars(
            select(ProjectMethodology.methodology_id).where(
                ProjectMethodology.methodology_id.in_(ids)
            )
        )
    )
    origin_names = dict(
        db.execute(
            select(Project.id, Project.name).where(
                Project.id.in_([m.origin_project_id for m in items if m.origin_project_id])
            )
        ).all()
    )
    return [
        MethodologySummary.model_validate(
            {
                **{k: getattr(m, k) for k in MethodologySummary.model_fields if hasattr(m, k)},
                "origin_project_name": origin_names.get(m.origin_project_id),
                "stage_count": len(m.stages),
                "activity_count": sum(len(s.activities) for s in m.stages),
                "deliverable_count": len(m.deliverables),
                "adoption_count": adoptions.get(m.id, 0),
            }
        )
        for m in items
    ]


def _detail(db: Session, m: Methodology) -> MethodologyDetail:
    adoptions = db.scalars(
        select(ProjectMethodology)
        .where(ProjectMethodology.methodology_id == m.id)
        .order_by(ProjectMethodology.adopted_at)
    ).all()
    return MethodologyDetail.model_validate(
        {
            **_summaries(db, [m])[0].model_dump(),
            **{
                k: getattr(m, k)
                for k in (
                    "prerequisites",
                    "tools",
                    "dependencies",
                    "common_risks",
                    "completion_criteria",
                    "limitations",
                )
            },
            "stages": m.stages,
            "deliverables": m.deliverables,
            "adoptions": [
                AdoptionRef(
                    id=a.id,
                    project_id=a.project_id,
                    project_name=a.project.name,
                    methodology_version=a.methodology_version,
                    adopted_at=a.adopted_at,
                )
                for a in adoptions
            ],
        }
    )


@router.get("/methodologies", response_model=list[MethodologySummary])
def list_methodologies(
    q: str | None = None,
    kind: MethodologyKind | None = None,
    status: MethodologyStatus | None = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    stmt = select(Methodology).order_by(Methodology.name)
    if not include_archived:
        stmt = stmt.where(Methodology.archived_at.is_(None))
    if kind:
        stmt = stmt.where(Methodology.kind == kind)
    if status:
        stmt = stmt.where(Methodology.status == status)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Methodology.name.ilike(like),
                Methodology.purpose.ilike(like),
                Methodology.when_to_use.ilike(like),
            )
        )
    return _summaries(db, list(db.scalars(stmt)))


@router.post("/methodologies", response_model=MethodologyDetail, status_code=201)
def create_methodology(body: MethodologyCreate, db: Session = Depends(get_db)):
    m = Methodology(slug=slugify(body.name, db), **body.model_dump(include=set(META)))
    db.add(m)
    build_structure(m, body.stages, body.deliverables)
    db.commit()
    db.refresh(m)
    return _detail(db, m)


@router.get("/methodologies/{mid}", response_model=MethodologyDetail)
def get_methodology(mid: uuid.UUID, db: Session = Depends(get_db)):
    return _detail(db, _get(db, mid))


@router.patch("/methodologies/{mid}", response_model=MethodologyDetail)
def update_methodology(mid: uuid.UUID, body: MethodologyMeta, db: Session = Depends(get_db)):
    m = _get(db, mid)
    changes = body.model_dump(exclude_unset=True)
    note = changes.pop("change_note", None)
    for k in ("name", "kind"):
        if k in changes and changes[k] is None:
            changes.pop(k)
    real = {k: v for k, v in changes.items() if getattr(m, k) != v}
    if real:
        _bump(db, m, note)
        for k, v in real.items():
            setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return _detail(db, m)


@router.put("/methodologies/{mid}/structure", response_model=MethodologyDetail)
def replace_structure(mid: uuid.UUID, body: StructureIn, db: Session = Depends(get_db)):
    """Replace stages, activities and deliverables. The previous structure is versioned.
    Projects that adopted it keep their tasks and deliverable tracking unchanged."""
    m = _get(db, mid)
    _bump(db, m, body.change_note)
    build_structure(m, body.stages, body.deliverables)
    db.commit()
    db.refresh(m)
    return _detail(db, m)


@router.post("/methodologies/{mid}/publish", response_model=MethodologyDetail)
def publish(mid: uuid.UUID, body: PublishIn, db: Session = Depends(get_db)):
    m = _get(db, mid)
    if not m.stages:
        raise bad_request("Add at least one stage before publishing.")
    if m.status != MethodologyStatus.PUBLISHED:
        _bump(db, m, body.change_note or "Published")
        m.status = MethodologyStatus.PUBLISHED
    db.commit()
    return _detail(db, m)


@router.post("/methodologies/{mid}/deprecate", response_model=MethodologyDetail)
def deprecate(mid: uuid.UUID, db: Session = Depends(get_db)):
    m = _get(db, mid)
    m.status = MethodologyStatus.DEPRECATED
    db.commit()
    return _detail(db, m)


@router.get("/methodologies/{mid}/versions", response_model=list[MethodologyVersionOut])
def versions(mid: uuid.UUID, db: Session = Depends(get_db)):
    _get(db, mid)
    return db.scalars(
        select(MethodologyVersion)
        .where(MethodologyVersion.methodology_id == mid)
        .order_by(MethodologyVersion.version.desc())
    ).all()


@router.post("/methodologies/{mid}/duplicate", response_model=MethodologyDetail, status_code=201)
def duplicate(mid: uuid.UUID, body: DuplicateIn, db: Session = Depends(get_db)):
    """Copy a methodology as a new draft, e.g. to adapt it for a particular project."""
    src = _get(db, mid)
    snap = snapshot(src)
    stages = [
        StageIn(
            key=str(i),
            **{k: s[k] for k in ("name", "description", "validation_criteria")},
            activities=s["activities"],
        )
        for i, s in enumerate(snap["stages"])
    ]
    deliverables = [
        DeliverableIn(
            name=d["name"],
            description=d["description"],
            classification=d["classification"],
            stage_key=None if d["stage_index"] is None else str(d["stage_index"]),
        )
        for d in snap["deliverables"]
    ]
    meta = {k: snap[k] for k in META if k not in ("name", "limitations")}
    m = Methodology(
        slug=slugify(body.name, db),
        name=body.name,
        **meta,
        origin_project_id=body.origin_project_id or src.origin_project_id,
        limitations=(src.limitations or "") + f"\nAdapted from “{src.name}” v{src.version}.",
    )
    db.add(m)
    build_structure(m, stages, deliverables)
    db.commit()
    db.refresh(m)
    return _detail(db, m)


@router.post(
    "/methodologies/from-project/{project_id}", response_model=MethodologyDetail, status_code=201
)
def from_project(project_id: uuid.UUID, body: FromProjectIn, db: Session = Depends(get_db)):
    """Turn a (completed) project's milestones and tasks into a reusable draft.
    Dates, people and progress are not copied; review it for confidential details."""
    project = db.get(Project, project_id)
    if not project:
        raise not_found("Project")
    milestones = sorted(project.milestones, key=lambda x: (x.due_date is None, x.due_date))
    tasks = list(
        db.scalars(
            select(Task)
            .where(
                Task.project_id == project_id, Task.archived_at.is_(None), Task.parent_id.is_(None)
            )
            .order_by(Task.position)
        )
    )
    if not tasks and not milestones:
        raise bad_request("This project has no milestones or tasks to learn from.")
    stages: list[StageIn] = []
    for ms in milestones:
        acts = [t for t in tasks if t.milestone_id == ms.id]
        stages.append(
            StageIn(
                key=str(len(stages)),
                name=ms.title,
                description=ms.description,
                validation_criteria=ms.deliverables,
                activities=[
                    {
                        "title": t.title,
                        "instructions": t.description,
                        "expected_output": t.acceptance_criteria or t.deliverables,
                    }
                    for t in acts
                ],
            )
        )
    loose = [t for t in tasks if t.milestone_id is None]
    if loose:
        stages.append(
            StageIn(
                key=str(len(stages)),
                name="Other activities",
                activities=[
                    {
                        "title": t.title,
                        "instructions": t.description,
                        "expected_output": t.acceptance_criteria,
                    }
                    for t in loose
                ],
            )
        )
    deliverables = [
        DeliverableIn(
            name=ms.title,
            description=ms.deliverables,
            classification=Classification.RECOMMENDED,
            stage_key=str(i),
        )
        for i, ms in enumerate(milestones)
        if (ms.deliverables or "").strip()
    ]
    m = Methodology(
        slug=slugify(body.name, db),
        name=body.name,
        kind=body.kind,
        purpose=f"Derived from the project “{project.name}”.",
        when_to_use=project.description,
        origin_project_id=project.id,
        limitations="Generated from one project's plan. Review and remove project-specific "
        "assumptions, names and confidential details before publishing.",
    )
    db.add(m)
    build_structure(m, stages, deliverables)
    db.commit()
    db.refresh(m)
    return _detail(db, m)


@router.post("/methodologies/{mid}/archive", response_model=MethodologyDetail)
def archive(mid: uuid.UUID, db: Session = Depends(get_db)):
    m = _get(db, mid)
    m.archived_at = now()
    db.commit()
    return _detail(db, m)


@router.post("/methodologies/{mid}/restore", response_model=MethodologyDetail)
def restore(mid: uuid.UUID, db: Session = Depends(get_db)):
    m = _get(db, mid)
    m.archived_at = None
    db.commit()
    return _detail(db, m)


@router.delete("/methodologies/{mid}", status_code=204)
def delete_methodology(mid: uuid.UUID, confirm: bool = False, db: Session = Depends(get_db)):
    m = _get(db, mid)
    if db.scalar(select(func.count()).where(ProjectMethodology.methodology_id == mid)):
        raise conflict("Projects have adopted this methodology. Archive or deprecate it instead.")
    if not confirm:
        raise bad_request(
            "Deleting a methodology is permanent. Confirm to continue.",
            code="confirmation_required",
        )
    db.delete(m)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- adoption
def _adoption_out(db: Session, a: ProjectMethodology, counts=(0, 0)) -> AdoptionOut:
    return AdoptionOut(
        id=a.id,
        project_id=a.project_id,
        project_name=a.project.name,
        methodology_id=a.methodology_id,
        methodology_name=a.methodology.name,
        methodology_version=a.methodology_version,
        current_version=a.methodology.version,
        stage_ids=a.stage_ids,
        notes=a.notes,
        adopted_at=a.adopted_at,
        deliverables=[
            ProjectDeliverableOut.model_validate(d)
            for d in sorted(a.deliverables, key=lambda d: d.created_at)
        ],
        milestones_created=counts[0],
        tasks_created=counts[1],
    )


@router.get("/projects/{project_id}/methodologies", response_model=list[AdoptionOut])
def list_adoptions(project_id: uuid.UUID, db: Session = Depends(get_db)):
    return [
        _adoption_out(db, a)
        for a in db.scalars(
            select(ProjectMethodology)
            .where(ProjectMethodology.project_id == project_id)
            .order_by(ProjectMethodology.adopted_at)
        ).unique()
    ]


@router.post("/projects/{project_id}/methodologies", response_model=AdoptionOut, status_code=201)
def adopt(project_id: uuid.UUID, body: AdoptIn, db: Session = Depends(get_db)):
    """Adopt a whole methodology or selected stages. Optionally create one milestone per stage
    and one task per activity. Existing tasks with the same title are not duplicated."""
    project = db.get(Project, project_id)
    if not project:
        raise not_found("Project")
    m = _get(db, body.methodology_id)
    if m.archived_at:
        raise bad_request("This methodology is archived. Restore it before adopting it.")
    stages = [s for s in m.stages if body.stage_ids is None or s.id in set(body.stage_ids)]
    if not stages:
        raise bad_request("Choose at least one stage to adopt.")
    previous = db.scalars(
        select(ProjectMethodology).where(
            ProjectMethodology.project_id == project_id, ProjectMethodology.methodology_id == m.id
        )
    ).all()
    already = {sid for a in previous for sid in a.stage_ids}
    overlap = [s.name for s in stages if str(s.id) in already]
    if overlap:
        raise conflict(f"Already adopted in this project: {', '.join(overlap)}.")

    adoption = ProjectMethodology(
        project_id=project_id,
        methodology_id=m.id,
        methodology_version=m.version,
        stage_ids=[str(s.id) for s in stages],
        notes=body.notes,
    )
    db.add(adoption)
    db.flush()
    existing_titles = {
        t.lower().strip()
        for t in db.scalars(select(Task.title).where(Task.project_id == project_id))
    }
    max_pos = db.scalar(select(func.max(Task.position)).where(Task.project_id == project_id)) or 0
    stage_ms: dict[uuid.UUID, Milestone] = {}
    n_ms = n_tasks = 0
    for i, s in enumerate(stages):
        ms = None
        if body.create_milestones:
            stage_deliverables = [d.name for d in m.deliverables if d.stage_id == s.id]
            ms = Milestone(
                project_id=project_id,
                title=f"{s.name}",
                description=s.description,
                deliverables="\n".join(stage_deliverables) or s.validation_criteria,
                due_date=body.start_date + timedelta(weeks=i + 1) if body.start_date else None,
            )
            db.add(ms)
            db.flush()
            stage_ms[s.id] = ms
            n_ms += 1
        if body.create_tasks:
            for a in s.activities:
                if a.title.lower().strip() in existing_titles:
                    continue
                max_pos += 1000
                t = Task(
                    project_id=project_id,
                    title=a.title,
                    description=a.instructions,
                    acceptance_criteria=a.expected_output,
                    milestone_id=ms.id if ms else None,
                    position=max_pos,
                    labels=[m.slug[:60]],
                )
                db.add(t)
                db.flush()
                record(
                    db,
                    t,
                    "created",
                    {"title": [None, t.title], "source": [None, f"Methodology: {m.name}"]},
                )
                existing_titles.add(a.title.lower().strip())
                n_tasks += 1
    stage_set = {s.id for s in stages}
    for d in m.deliverables:
        if d.stage_id is None or d.stage_id in stage_set:
            db.add(
                ProjectDeliverable(
                    adoption_id=adoption.id,
                    definition_id=d.id,
                    name=d.name,
                    classification=d.classification,
                    milestone_id=stage_ms[d.stage_id].id if d.stage_id in stage_ms else None,
                )
            )
    db.commit()
    db.refresh(adoption)
    return _adoption_out(db, adoption, (n_ms, n_tasks))


@router.patch("/project-deliverables/{did}", response_model=ProjectDeliverableOut)
def update_project_deliverable(
    did: uuid.UUID, body: ProjectDeliverableUpdate, db: Session = Depends(get_db)
):
    d = db.get(ProjectDeliverable, did)
    if not d:
        raise not_found("Deliverable")
    changes = body.model_dump(exclude_unset=True)
    if changes.get("document_id") and not db.get(ProjectDocument, changes["document_id"]):
        raise bad_request("Document does not exist.")
    for k, v in changes.items():
        if v is not None or k in ("document_id", "notes"):
            setattr(d, k, v)
    db.commit()
    return d


@router.delete("/project-methodologies/{aid}", status_code=204)
def remove_adoption(aid: uuid.UUID, db: Session = Depends(get_db)):
    """Stops tracking the adoption and its deliverables. Created milestones and tasks are kept."""
    a = db.get(ProjectMethodology, aid)
    if not a:
        raise not_found("Adoption")
    db.delete(a)
    db.commit()
    return Response(status_code=204)
