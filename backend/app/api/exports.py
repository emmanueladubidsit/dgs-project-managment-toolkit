"""Download reports, project briefs, project status packs and knowledge as DOCX, PDF or PPTX."""

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import not_found
from app.models import KnowledgeItem, Project, Report, Task, WorkLog
from app.models.enums import ReportKind, WorkLogKind
from app.services import exports, privacy
from app.services.knowledge_templates import LABELS, TEMPLATES
from app.services.progress import weighted_progress
from app.services.reports import generate
from app.services.tasks import DONE

router = APIRouter(tags=["exports"])
Format = Literal["docx", "pdf", "pptx"]


def _render(db: Session, fmt: str, title: str, md: str, sub: str | None = None) -> bytes:
    """Exports pass through the privacy filter (named individuals masked, secrets redacted)."""
    return exports.render(fmt, privacy.clean(db, title), privacy.clean(db, md), sub)


def _file(content: bytes, title: str, fmt: str) -> Response:
    name = exports.filename(title, fmt)
    return Response(
        content,
        media_type=exports.MIME[fmt],
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


class ExportIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=500_000)
    subtitle: str | None = Field(default=None, max_length=300)
    format: Format = "docx"


@router.post("/export")
def export_markdown(body: ExportIn, db: Session = Depends(get_db)):
    """Export any Markdown (e.g. an unsaved report draft or an AI draft you have reviewed)."""
    return _file(
        _render(db, body.format, body.title, body.content, body.subtitle),
        body.title,
        body.format,
    )


@router.get("/export/report/{report_id}")
def export_report(report_id: uuid.UUID, format: Format = "docx", db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r:
        raise not_found("Report")
    sub = f"{r.period_start:%d %b %Y} – {r.period_end:%d %b %Y}"
    return _file(_render(db, format, r.title, r.content, sub), r.title, format)


def project_brief_md(db: Session, p: Project) -> str:
    sections = [
        ("Overview", p.description),
        ("Problem statement", p.problem_statement),
        ("Objectives", p.objectives),
        ("Target users", p.target_users),
        ("Business context", p.business_context),
        ("In scope", p.scope),
        ("Out of scope", p.out_of_scope),
        ("Expected outcomes", p.expected_outcomes),
        ("Stakeholders", p.stakeholders),
        ("Dependencies", p.dependencies),
        ("Risks and assumptions", p.risks_assumptions),
        ("Technology", p.tech_stack),
    ]
    out = [
        f"# {p.name}",
        "",
        "## Key facts",
        "",
        f"- **Status:** {p.status.value.replace('_', ' ').title()}",
        f"- **Stage:** {p.stage.name if p.stage else 'Not set'}",
        f"- **Start:** {p.start_date:%d %B %Y}" if p.start_date else "- **Start:** Not set",
        f"- **Target completion:** {p.target_date:%d %B %Y}"
        if p.target_date
        else "- **Target completion:** Not set",
        "",
    ]
    for heading, text in sections:
        if text and text.strip():
            out += [f"## {heading}", ""]
            lines = [x.strip() for x in text.strip().splitlines() if x.strip()]
            out += (
                [x if x.startswith(("-", "*")) else f"- {x}" for x in lines]
                if len(lines) > 1
                else lines
            )
            out.append("")
    if p.milestones:
        out += ["## Milestones", ""]
        out += [
            f"- **{m.title}** — due {m.due_date:%d %b %Y}"
            if m.due_date
            else f"- **{m.title}** — date not set"
            for m in sorted(p.milestones, key=lambda m: (m.due_date is None, m.due_date))
        ]
    return "\n".join(out)


def project_status_md(db: Session, p: Project) -> str:
    tasks = list(
        db.scalars(select(Task).where(Task.project_id == p.id, Task.archived_at.is_(None)))
    )
    top = [t for t in tasks if t.parent_id is None]
    prog = weighted_progress(top)
    today = date.today()
    open_ = [t for t in top if t.status not in DONE]
    overdue = [t for t in open_ if t.due_date and t.due_date < today]
    blocked = [t for t in tasks if t.status.value == "blocked"]
    done = sorted([t for t in tasks if t.completed_at], key=lambda t: t.completed_at, reverse=True)[
        :8
    ]
    logs = list(
        db.scalars(
            select(WorkLog)
            .where(WorkLog.project_id == p.id)
            .order_by(WorkLog.entry_date.desc())
            .limit(40)
        ).unique()
    )
    decisions = [w for w in logs if w.kind == WorkLogKind.DECISION][:6]
    out = [
        f"# {p.name}",
        "",
        "## Overall progress",
        "",
        f"- **{prog.percent:.0f}% complete** "
        f"({prog.tasks_completed} of {prog.tasks_counted} tasks done)",
        f"- {prog.explanation}",
        f"- Target completion: {p.target_date:%d %B %Y}"
        if p.target_date
        else "- Target completion: not set",
        f"- {len(open_)} open, {len(overdue)} overdue, {len(blocked)} blocked",
        "",
        "## Milestones",
        "",
    ]
    for m in sorted(p.milestones, key=lambda m: (m.due_date is None, m.due_date)):
        mp = weighted_progress([t for t in top if t.milestone_id == m.id])
        due = f"due {m.due_date:%d %b}" if m.due_date else "no date"
        out.append(
            f"- **{m.title}** — {m.status.value.replace('_', ' ')}, {mp.percent:.0f}%, {due}"
        )
    if not p.milestones:
        out.append("- No milestones recorded.")
    out += ["", "## Recently completed", ""]
    out += [f"- {t.title}" for t in done] or ["- None recorded."]
    out += ["", "## Risks, blockers and overdue work", ""]
    risk = [f"- Blocked: {t.title}" for t in blocked] + [
        f"- Overdue: {t.title} (due {t.due_date:%d %b})" for t in overdue
    ]
    if p.risks_assumptions:
        risk += [
            f"- {x.strip().lstrip('-* ')}" for x in p.risks_assumptions.splitlines() if x.strip()
        ][:5]
    out += risk[:12] or ["- None recorded."]
    out += ["", "## Decisions", ""]
    out += [f"- {w.entry_date:%d %b}: {w.summary.strip().splitlines()[0]}" for w in decisions] or [
        "- None recorded."
    ]
    nxt = sorted(open_, key=lambda t: (t.due_date is None, t.due_date))[:8]
    out += ["", "## Next steps (planned, not yet done)", ""]
    out += [f"- {t.title}" + (f" — due {t.due_date:%d %b}" if t.due_date else "") for t in nxt] or [
        "- None recorded."
    ]
    return "\n".join(out)


@router.get("/export/project/{project_id}/{kind}")
def export_project(
    project_id: uuid.UUID,
    kind: Literal["brief", "status", "report"],
    format: Format = Query(default="pptx"),
    db: Session = Depends(get_db),
):
    """brief: project context. status: stakeholder progress pack. report: full project report."""
    p = db.get(Project, project_id)
    if not p:
        raise not_found("Project")
    if kind == "brief":
        title, md, sub = f"{p.name} — project brief", project_brief_md(db, p), None
    elif kind == "status":
        title, md = f"{p.name} — status update", project_status_md(db, p)
        sub = f"As at {date.today():%d %B %Y}"
    else:
        draft = generate(db, ReportKind.PROJECT, date.today(), p.id, "stakeholder")
        title, md, sub = draft.title, draft.content, None
    return _file(_render(db, format, title, md, sub), title, format)


@router.get("/export/knowledge/{item_id}")
def export_knowledge(item_id: uuid.UUID, format: Format = "docx", db: Session = Depends(get_db)):
    k = db.get(KnowledgeItem, item_id)
    if not k:
        raise not_found("Knowledge item")
    md = [
        f"# {k.title}",
        "",
        f"_{LABELS[k.category]} · verification: "
        f"{k.verification.value.replace('_', ' ')} · version {k.version}_",
        "",
    ]
    if k.verification.value in ("ai_suggestion", "research_unimplemented", "outdated"):
        md += ["**Note:** this item is not verified. Check it before relying on it.", ""]
    if k.summary:
        md += ["## Summary", "", k.summary, ""]
    for key, label, _ in TEMPLATES.get(k.category, []):
        if k.fields.get(key):
            md += [f"## {label}", "", k.fields[key], ""]
    for label, value in (
        ("Notes", k.content),
        ("Sources and references", k.sources),
        ("Limitations", k.limitations),
        ("Before reusing", k.reuse_notes),
    ):
        if value:
            md += [f"## {label}", "", value, ""]
    return _file(_render(db, format, k.title, "\n".join(md)), k.title, format)
