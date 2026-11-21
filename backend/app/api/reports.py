import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import bad_request, not_found
from app.models import Project, Report
from app.models.enums import ReportKind
from app.schemas.planning import ReportDraft, ReportGenerateIn, ReportIn, ReportOut, ReportUpdate
from app.services.reports import generate

router = APIRouter(tags=["reports"])


@router.post("/reports/generate", response_model=ReportDraft)
def generate_report(body: ReportGenerateIn, db: Session = Depends(get_db)):
    """Build a draft report from stored data. Nothing is saved until POST /reports."""
    if body.project_id and not db.get(Project, body.project_id):
        raise not_found("Project")
    if body.kind == ReportKind.PROJECT and not body.project_id:
        raise bad_request("Choose a project for a project report.")
    return generate(db, body.kind, body.date, body.project_id, body.audience)


@router.get("/reports", response_model=list[ReportOut])
def list_reports(
    kind: ReportKind | None = None,
    project_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Report).order_by(Report.period_start.desc(), Report.created_at.desc())
    if kind:
        stmt = stmt.where(Report.kind == kind)
    if project_id:
        stmt = stmt.where(Report.project_id == project_id)
    return db.scalars(stmt.limit(200)).all()


@router.post("/reports", response_model=ReportOut, status_code=201)
def save_report(body: ReportIn, db: Session = Depends(get_db)):
    report = Report(**body.model_dump())
    db.add(report)
    db.commit()
    return report


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: uuid.UUID, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise not_found("Report")
    return report


@router.patch("/reports/{report_id}", response_model=ReportOut)
def update_report(report_id: uuid.UUID, body: ReportUpdate, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise not_found("Report")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(report, k, v)
    db.commit()
    return report


@router.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: uuid.UUID, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise not_found("Report")
    db.delete(report)
    db.commit()
    return Response(status_code=204)
