import uuid
from collections import Counter, defaultdict
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import bad_request, not_found
from app.models import Milestone, Project, ProjectStage, Task, Workstream
from app.models.enums import MilestoneStatus, ProjectStatus, TaskStatus
from app.schemas.project import (
    MilestoneIn,
    MilestoneOut,
    MilestoneSummary,
    MilestoneUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectSummary,
    ProjectUpdate,
    StageIn,
    StageOut,
    WorkstreamIn,
    WorkstreamOut,
    WorkstreamUpdate,
)
from app.services.progress import weighted_progress
from app.services.tasks import DONE, now

router = APIRouter(tags=["projects"])


# ---------------------------------------------------------------- stages
@router.get("/stages", response_model=list[StageOut])
def list_stages(db: Session = Depends(get_db)):
    return db.scalars(select(ProjectStage).order_by(ProjectStage.position)).all()


@router.post("/stages", response_model=StageOut, status_code=201)
def create_stage(body: StageIn, db: Session = Depends(get_db)):
    stage = ProjectStage(**body.model_dump())
    db.add(stage)
    db.commit()
    return stage


@router.patch("/stages/{stage_id}", response_model=StageOut)
def update_stage(stage_id: uuid.UUID, body: StageIn, db: Session = Depends(get_db)):
    stage = db.get(ProjectStage, stage_id)
    if not stage:
        raise not_found("Stage")
    for k, v in body.model_dump().items():
        setattr(stage, k, v)
    db.commit()
    return stage


# ---------------------------------------------------------------- projects
def _get_project(db: Session, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise not_found("Project")
    return project


def _summaries(db: Session, projects: list[Project]) -> list[ProjectSummary]:
    if not projects:
        return []
    today = date.today()
    tasks = db.scalars(
        select(Task).where(
            Task.project_id.in_([p.id for p in projects]), Task.archived_at.is_(None)
        )
    ).all()
    by_project: dict[uuid.UUID, list[Task]] = defaultdict(list)
    for t in tasks:
        by_project[t.project_id].append(t)
    out = []
    for p in projects:
        pts = by_project[p.id]
        top = [t for t in pts if t.parent_id is None]
        out.append(
            ProjectSummary.model_validate(
                {
                    **ProjectOut.model_validate(p).model_dump(),
                    "progress": weighted_progress(top),
                    "task_counts": dict(Counter(t.status.value for t in pts)),
                    "overdue_count": sum(
                        1 for t in pts if t.due_date and t.due_date < today and t.status not in DONE
                    ),
                    "blocked_count": sum(1 for t in pts if t.status == TaskStatus.BLOCKED),
                }
            )
        )
    return out


@router.get("/projects", response_model=list[ProjectSummary])
def list_projects(
    q: str | None = None,
    status: ProjectStatus | None = None,
    stage_id: uuid.UUID | None = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    stmt = select(Project).order_by(Project.updated_at.desc())
    if status:
        stmt = stmt.where(Project.status == status)
    elif not include_archived:
        stmt = stmt.where(Project.status != ProjectStatus.ARCHIVED)
    if stage_id:
        stmt = stmt.where(Project.stage_id == stage_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Project.name.ilike(like), Project.description.ilike(like)))
    return _summaries(db, list(db.scalars(stmt).unique()))


@router.post("/projects", response_model=ProjectSummary, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"workstreams"})
    if data.get("stage_id") and not db.get(ProjectStage, data["stage_id"]):
        raise bad_request("Unknown project stage.")
    project = Project(**data)
    db.add(project)
    db.flush()
    for i, name in enumerate(n.strip() for n in body.workstreams if n.strip()):
        db.add(Workstream(project_id=project.id, name=name, position=i))
    db.commit()
    db.refresh(project)
    return _summaries(db, [project])[0]


@router.get("/projects/{project_id}", response_model=ProjectSummary)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    return _summaries(db, [_get_project(db, project_id)])[0]


@router.patch("/projects/{project_id}", response_model=ProjectSummary)
def update_project(project_id: uuid.UUID, body: ProjectUpdate, db: Session = Depends(get_db)):
    project = _get_project(db, project_id)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("stage_id") and not db.get(ProjectStage, changes["stage_id"]):
        raise bad_request("Unknown project stage.")
    for k, v in changes.items():
        setattr(project, k, v)
    if project.start_date and project.target_date and project.target_date < project.start_date:
        raise bad_request("Target completion date cannot be before the start date.")
    if "status" in changes:
        project.archived_at = now() if project.status == ProjectStatus.ARCHIVED else None
    db.commit()
    db.refresh(project)
    return _summaries(db, [project])[0]


@router.post("/projects/{project_id}/archive", response_model=ProjectSummary)
def archive_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = _get_project(db, project_id)
    project.status, project.archived_at = ProjectStatus.ARCHIVED, now()
    db.commit()
    return _summaries(db, [project])[0]


@router.post("/projects/{project_id}/restore", response_model=ProjectSummary)
def restore_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = _get_project(db, project_id)
    project.status, project.archived_at = ProjectStatus.ACTIVE, None
    db.commit()
    return _summaries(db, [project])[0]


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: uuid.UUID,
    confirm: str = Query(description="Must exactly match the project name."),
    db: Session = Depends(get_db),
):
    """Permanent deletion of a project and everything in it. Archive is the safer default;
    deletion requires the exact project name as confirmation."""
    project = _get_project(db, project_id)
    if confirm != project.name:
        raise bad_request(
            "To delete permanently, type the project name exactly.", code="confirmation_required"
        )
    db.delete(project)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- workstreams
@router.get("/projects/{project_id}/workstreams", response_model=list[WorkstreamOut])
def list_workstreams(project_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_project(db, project_id).workstreams


@router.post("/projects/{project_id}/workstreams", response_model=WorkstreamOut, status_code=201)
def create_workstream(project_id: uuid.UUID, body: WorkstreamIn, db: Session = Depends(get_db)):
    project = _get_project(db, project_id)
    position = body.position if body.position is not None else len(project.workstreams)
    ws = Workstream(
        project_id=project_id, name=body.name, description=body.description, position=position
    )
    db.add(ws)
    db.commit()
    return ws


@router.patch("/workstreams/{workstream_id}", response_model=WorkstreamOut)
def update_workstream(
    workstream_id: uuid.UUID, body: WorkstreamUpdate, db: Session = Depends(get_db)
):
    ws = db.get(Workstream, workstream_id)
    if not ws:
        raise not_found("Workstream")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(ws, k, v)
    db.commit()
    return ws


@router.delete("/workstreams/{workstream_id}", status_code=204)
def delete_workstream(workstream_id: uuid.UUID, db: Session = Depends(get_db)):
    """Tasks and milestones in the workstream are kept; they simply become unassigned."""
    ws = db.get(Workstream, workstream_id)
    if not ws:
        raise not_found("Workstream")
    db.delete(ws)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- milestones
def _milestone_summaries(db: Session, milestones: list[Milestone]) -> list[MilestoneSummary]:
    if not milestones:
        return []
    today = date.today()
    ids = [m.id for m in milestones]
    tasks = db.scalars(
        select(Task).where(Task.milestone_id.in_(ids), Task.archived_at.is_(None))
    ).all()
    by_ms: dict[uuid.UUID, list[Task]] = defaultdict(list)
    for t in tasks:
        by_ms[t.milestone_id].append(t)
    out = []
    for m in milestones:
        mts = by_ms[m.id]
        in_ms = {t.id for t in mts}
        # Count subtasks only when their parent is not already counted in this milestone.
        counted = [t for t in mts if t.parent_id not in in_ms]
        warnings = []
        if not (m.deliverables or "").strip():
            warnings.append("No deliverables defined.")
        if not mts:
            warnings.append("No tasks linked to this milestone.")
        missing_ac = sum(1 for t in mts if not (t.acceptance_criteria or "").strip())
        if missing_ac:
            warnings.append(f"{missing_ac} task(s) without acceptance criteria.")
        open_statuses = (MilestoneStatus.PLANNED, MilestoneStatus.IN_PROGRESS)
        if m.due_date and m.due_date < today and m.status in open_statuses:
            warnings.append("Due date has passed.")
        late = sum(1 for t in mts if t.due_date and m.due_date and t.due_date > m.due_date)
        if late:
            warnings.append(f"{late} task(s) are due after the milestone date.")
        out.append(
            MilestoneSummary.model_validate(
                {
                    **MilestoneOut.model_validate(m).model_dump(),
                    "project_name": m.project.name,
                    "progress": weighted_progress(counted),
                    "warnings": warnings,
                }
            )
        )
    return out


@router.get("/milestones", response_model=list[MilestoneSummary])
def list_all_milestones(
    project_id: uuid.UUID | None = None,
    status: MilestoneStatus | None = None,
    db: Session = Depends(get_db),
):
    stmt = (
        select(Milestone)
        .join(Project)
        .where(Project.status != ProjectStatus.ARCHIVED)
        .order_by(Milestone.due_date.asc().nulls_last(), Milestone.created_at)
    )
    if project_id:
        stmt = (
            select(Milestone)
            .where(Milestone.project_id == project_id)
            .order_by(Milestone.due_date.asc().nulls_last(), Milestone.created_at)
        )
    if status:
        stmt = stmt.where(Milestone.status == status)
    return _milestone_summaries(db, list(db.scalars(stmt)))


@router.post("/projects/{project_id}/milestones", response_model=MilestoneSummary, status_code=201)
def create_milestone(project_id: uuid.UUID, body: MilestoneIn, db: Session = Depends(get_db)):
    _get_project(db, project_id)
    if body.workstream_id:
        ws = db.get(Workstream, body.workstream_id)
        if not ws or ws.project_id != project_id:
            raise bad_request("Workstream does not belong to this project.")
    ms = Milestone(project_id=project_id, **body.model_dump())
    if ms.status == MilestoneStatus.ACHIEVED:
        ms.achieved_at = now()
    db.add(ms)
    db.commit()
    db.refresh(ms)
    return _milestone_summaries(db, [ms])[0]


@router.get("/milestones/{milestone_id}", response_model=MilestoneSummary)
def get_milestone(milestone_id: uuid.UUID, db: Session = Depends(get_db)):
    ms = db.get(Milestone, milestone_id)
    if not ms:
        raise not_found("Milestone")
    return _milestone_summaries(db, [ms])[0]


@router.patch("/milestones/{milestone_id}", response_model=MilestoneSummary)
def update_milestone(milestone_id: uuid.UUID, body: MilestoneUpdate, db: Session = Depends(get_db)):
    ms = db.get(Milestone, milestone_id)
    if not ms:
        raise not_found("Milestone")
    changes = body.model_dump(exclude_unset=True)
    if ws_id := changes.get("workstream_id"):
        ws = db.get(Workstream, ws_id)
        if not ws or ws.project_id != ms.project_id:
            raise bad_request("Workstream does not belong to this project.")
    if "status" in changes and changes["status"] != ms.status:
        ms.achieved_at = now() if changes["status"] == MilestoneStatus.ACHIEVED else None
    for k, v in changes.items():
        setattr(ms, k, v)
    db.commit()
    db.refresh(ms)
    return _milestone_summaries(db, [ms])[0]


@router.delete("/milestones/{milestone_id}", status_code=204)
def delete_milestone(milestone_id: uuid.UUID, db: Session = Depends(get_db)):
    """Linked tasks are kept and become unassigned from the milestone."""
    ms = db.get(Milestone, milestone_id)
    if not ms:
        raise not_found("Milestone")
    db.delete(ms)
    db.commit()
    return Response(status_code=204)
