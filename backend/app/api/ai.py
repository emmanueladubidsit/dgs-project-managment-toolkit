"""AI assistant API. Every endpoint returns a draft, an answer with its sources, or pending
suggestions — nothing is changed in the workspace without a person approving it.

Manual mode: when the provider is "manual", endpoints return {"needs_manual": true, "prompt": ...};
the client shows the prompt to copy into any chat tool and calls the same endpoint again with
`manual_response` set to the pasted answer."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.voice import SuggestionOut, _find_duplicate, _sugg_out
from app.db import get_db
from app.errors import AppError, bad_request, not_found
from app.models import AIInteraction, Project, Suggestion, Task, VoiceNote
from app.models.enums import Priority
from app.models.voice import SuggestionKind, SuggestionStatus
from app.services import text_tools
from app.services.ai import features as F
from app.services.ai.context import (
    Context,
    knowledge_search_context,
    project_context,
    workspace_context,
)
from app.services.ai.provider import (
    PRESETS,
    AIError,
    ManualRequired,
    complete,
    list_models,
    load_config,
    save_config,
)

router = APIRouter(tags=["ai"])


class ManualBody(BaseModel):
    manual_response: str | None = Field(default=None, max_length=200_000)


class SettingsIn(BaseModel):
    provider: Literal["disabled", "openai_compatible", "manual"]
    preset: str = "custom"
    base_url: str = Field(default="", max_length=500)
    model: str = Field(default="", max_length=200)
    temperature: float = Field(default=0.3, ge=0, le=1.5)
    timeout_seconds: int = Field(default=120, ge=5, le=900)
    max_context_chars: int = Field(default=16000, ge=2000, le=200_000)

    @field_validator("base_url")
    @classmethod
    def _url(cls, v: str) -> str:
        v = v.strip()
        if v and not v.lower().startswith(("http://", "https://")):
            raise ValueError("The service address must start with http:// or https://.")
        return v


class WriteIn(ManualBody):
    output: str
    text: str = Field(min_length=1, max_length=100_000)
    project_id: uuid.UUID | None = None
    instructions: str | None = Field(default=None, max_length=2000)


class AskIn(ManualBody):
    question: str = Field(min_length=2, max_length=4000)
    project_id: uuid.UUID | None = None


class SuggestIn(ManualBody):
    text: str | None = Field(default=None, max_length=100_000)
    voice_note_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None


class IdeaIn(ManualBody):
    idea: str = Field(min_length=10, max_length=20_000)


class ResearchIn(ManualBody):
    question: str = Field(min_length=3, max_length=2000)
    notes: str | None = Field(default=None, max_length=100_000)
    project_id: uuid.UUID | None = None


class ReportSummaryIn(ManualBody):
    content: str = Field(min_length=10, max_length=200_000)


def _run(
    db: Session, feature: str, prompt: tuple[str, str], manual: str | None, max_tokens: int = 1500
) -> str | dict:
    """Returns the AI text, or a manual-mode payload for the client."""
    system, user = prompt
    try:
        return complete(db, feature, system, user, manual_response=manual, max_tokens=max_tokens)
    except ManualRequired as m:
        return {"needs_manual": True, "prompt": m.prompt}
    except AIError as e:
        raise AppError(503, "ai_unavailable", str(e)) from e


def _context(db: Session, project_id: uuid.UUID | None) -> Context:
    limit = load_config(db).max_context_chars
    if project_id:
        if not db.get(Project, project_id):
            raise bad_request("Project does not exist.")
        return project_context(db, project_id, limit)
    return Context()


def _parse(text: str):
    try:
        return F.parse_json(text)
    except ValueError as e:
        raise AppError(422, "ai_format", str(e)) from e


# ---------------------------------------------------------------- configuration
@router.get("/ai/status")
def status(db: Session = Depends(get_db)):
    cfg = load_config(db)
    return {
        **cfg.public(),
        "presets": PRESETS,
        "writing_outputs": [{"key": k, "label": v[0]} for k, v in F.WRITING.items()],
        "ready": cfg.provider == "manual"
        or (cfg.provider == "openai_compatible" and bool(cfg.base_url and cfg.model)),
    }


@router.put("/ai/settings")
def update_settings(body: SettingsIn, db: Session = Depends(get_db)):
    if body.provider == "openai_compatible" and (not body.base_url or not body.model):
        raise bad_request("Enter the service address and the model name.")
    save_config(db, body.model_dump())
    return status(db)


@router.post("/ai/test")
def test_connection(db: Session = Depends(get_db)):
    cfg = load_config(db)
    if cfg.provider != "openai_compatible":
        raise bad_request("Testing applies to a connected AI service.")
    import time

    started = time.monotonic()
    try:
        reply = complete(
            db,
            "connection_test",
            "You are a connection test.",
            "Reply with exactly the word: ready",
            max_tokens=20,
        )
    except AIError as e:
        raise AppError(503, "ai_unavailable", str(e)) from e
    return {
        "ok": True,
        "reply": reply[:100],
        "seconds": round(time.monotonic() - started, 1),
        "model": cfg.model,
    }


@router.get("/ai/models")
def models(db: Session = Depends(get_db)):
    return {"models": list_models(db)}


@router.get("/ai/usage")
def usage(db: Session = Depends(get_db)):
    rows = db.scalars(select(AIInteraction).order_by(AIInteraction.created_at.desc()).limit(50))
    return [
        {
            "feature": r.feature,
            "provider": r.provider,
            "model": r.model,
            "ok": r.ok,
            "error": r.error,
            "duration_ms": r.duration_ms,
            "prompt_chars": r.prompt_chars,
            "response_chars": r.response_chars,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


# ---------------------------------------------------------------- features
@router.post("/ai/write")
def write(body: WriteIn, db: Session = Depends(get_db)):
    """Writing outputs that need a language model, optionally using a project's context."""
    if body.output not in F.WRITING:
        raise bad_request("Unknown output type.")
    ctx = _context(db, body.project_id)
    out = _run(
        db,
        f"write:{body.output}",
        F.writing_prompt(body.output, body.text, ctx.text, body.instructions),
        body.manual_response,
        max_tokens=2000,
    )
    if isinstance(out, dict):
        return out
    return {
        "label": F.WRITING[body.output][0],
        "text": out,
        "sources": ctx.sources,
        "ai_generated": True,
    }


@router.post("/ai/ask")
def ask(body: AskIn, db: Session = Depends(get_db)):
    """Answer a question from workspace data (one project, or the whole portfolio)."""
    limit = load_config(db).max_context_chars
    ctx = _context(db, body.project_id) if body.project_id else workspace_context(db, limit)
    extra = knowledge_search_context(db, body.question)
    text = (ctx.text + "\n" + extra.text)[:limit]
    out = _run(db, "ask", F.ask_prompt(body.question, text), body.manual_response)
    if isinstance(out, dict):
        return out
    return {"answer": out, "sources": ctx.sources + extra.sources, "ai_generated": True}


def _store_suggestions(
    db: Session,
    items: list,
    project_id,
    source_type: str,
    source_id,
    generator: str,
    parent_id: uuid.UUID | None = None,
) -> list[SuggestionOut]:
    if not isinstance(items, list):
        raise AppError(422, "ai_format", "The AI answer was not a list of suggestions.")
    existing = list(
        db.scalars(
            select(Suggestion).where(
                Suggestion.source_id == source_id, Suggestion.status != SuggestionStatus.REJECTED
            )
        )
    )
    created: list[Suggestion] = []
    for raw in items[:30]:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind", "task")).lower()
        title = str(raw.get("title", "")).strip()[:300]
        if kind not in {k.value for k in SuggestionKind} or not title:
            continue
        if any(
            e.kind.value == kind and text_tools.similar(e.payload.get("title", ""), title)
            for e in existing + created
        ):
            continue
        priority = str(raw.get("priority", "medium")).lower()
        payload = {
            "title": title,
            "priority": priority if priority in {p.value for p in Priority} else "medium",
        }
        est = raw.get("estimate_hours")
        if isinstance(est, (int, float)) and 0 < est <= 1000:
            payload["estimate_hours"] = float(est)
        if raw.get("acceptance_criteria"):
            payload["acceptance_criteria"] = str(raw["acceptance_criteria"])[:2000]
        if parent_id:
            payload["parent_id"] = str(parent_id)
        dup = _find_duplicate(db, project_id, title) if kind == "task" else None
        s = Suggestion(
            kind=SuggestionKind(kind),
            source_type=source_type,
            source_id=source_id,
            project_id=project_id,
            generator=generator,
            payload=payload,
            evidence=str(raw.get("evidence") or "")[:2000] or None,
            duplicate_of_task_id=dup.id if dup else None,
        )
        db.add(s)
        created.append(s)
    db.commit()
    return [_sugg_out(db, s) for s in created]


@router.post("/ai/suggest")
def suggest(body: SuggestIn, db: Session = Depends(get_db)):
    """AI-extracted tasks, blockers, decisions and progress — stored as pending suggestions."""
    note = db.get(VoiceNote, body.voice_note_id) if body.voice_note_id else None
    if body.voice_note_id and not note:
        raise not_found("Voice note")
    text = body.text or (note.transcript_edited or note.transcript_raw if note else None)
    if not text or not text.strip():
        raise bad_request("There is no text to analyse.")
    project_id = body.project_id or (note.project_id if note else None)
    ctx = _context(db, project_id)
    existing = (
        [t for t in db.scalars(select(Task.title).where(Task.project_id == project_id))]
        if project_id
        else []
    )
    out = _run(db, "suggest", F.suggest_prompt(text, ctx.text, existing), body.manual_response)
    if isinstance(out, dict):
        return out
    cfg = load_config(db)
    gen = "manual" if body.manual_response is not None else (cfg.model or cfg.provider)
    return _store_suggestions(
        db,
        _parse(out),
        project_id,
        "voice_note" if note else "text",
        note.id if note else None,
        f"ai:{gen}",
    )


@router.post("/ai/breakdown/{task_id}")
def breakdown(task_id: uuid.UUID, body: ManualBody, db: Session = Depends(get_db)):
    """Suggest subtasks for a task (pending suggestions; approve to create them)."""
    task = db.get(Task, task_id)
    if not task:
        raise not_found("Task")
    ctx = _context(db, task.project_id)
    subs = [t.title for t in task.subtasks]
    detail = "\n".join(
        x
        for x in [
            task.description,
            f"Acceptance criteria: {task.acceptance_criteria}"
            if task.acceptance_criteria
            else None,
        ]
        if x
    )
    out = _run(
        db,
        "breakdown",
        F.breakdown_prompt(task.title, detail, ctx.text, subs),
        body.manual_response,
    )
    if isinstance(out, dict):
        return out
    items = [{**x, "kind": "task"} for x in _parse(out) if isinstance(x, dict)]
    cfg = load_config(db)
    gen = "manual" if body.manual_response is not None else (cfg.model or cfg.provider)
    return _store_suggestions(
        db, items, task.project_id, "task", task.id, f"ai:{gen}", parent_id=task.id
    )


@router.post("/ai/structure-project")
def structure_project(body: IdeaIn, db: Session = Depends(get_db)):
    """Turn a rough idea into a draft project brief (not saved — review it in the form)."""
    out = _run(
        db,
        "structure_project",
        F.structure_project_prompt(body.idea),
        body.manual_response,
        max_tokens=2500,
    )
    if isinstance(out, dict):
        return out
    data = _parse(out)
    if not isinstance(data, dict):
        raise AppError(422, "ai_format", "The AI answer was not a project brief.")

    def text(v) -> str:
        if isinstance(v, list):
            return "\n".join(str(x) for x in v)
        return str(v or "").strip()

    draft = {k: text(data.get(k)) for k in F.PROJECT_FIELDS}
    assumptions, unknowns = data.get("assumptions") or [], data.get("unknowns") or []
    if assumptions:
        draft["risks_assumptions"] = "\n".join(
            filter(
                None,
                [
                    draft["risks_assumptions"],
                    "Assumptions (to confirm):",
                    *[f"- {a}" for a in assumptions],
                ],
            )
        )
    draft["notes"] = (
        "\n".join(["Open questions:", *[f"- {u}" for u in unknowns]]) if unknowns else ""
    )
    draft["workstreams"] = [
        str(w)[:200] for w in (data.get("workstreams") or []) if str(w).strip()
    ][:15]
    return {"draft": draft, "ai_generated": True}


@router.post("/ai/research-draft")
def research_draft(body: ResearchIn, db: Session = Depends(get_db)):
    """Draft a research record. Saved items are marked “AI suggestion — awaiting review”."""
    ctx = _context(db, body.project_id)
    extra = knowledge_search_context(db, body.question)
    out = _run(
        db,
        "research_draft",
        F.research_prompt(body.question, body.notes or "", ctx.text + "\n" + extra.text),
        body.manual_response,
        max_tokens=2500,
    )
    if isinstance(out, dict):
        return out
    data = _parse(out)
    if not isinstance(data, dict):
        raise AppError(422, "ai_format", "The AI answer was not a research record.")
    keys = [
        "research_question",
        "objective",
        "findings",
        "options_investigated",
        "comparisons",
        "conclusions",
        "recommendations",
        "outstanding_questions",
    ]
    as_text = lambda v: "\n".join(map(str, v)) if isinstance(v, list) else str(v or "").strip()  # noqa: E731
    return {
        "draft": {
            "category": "research",
            "verification": "ai_suggestion",
            "title": as_text(data.get("title")) or body.question[:200],
            "summary": as_text(data.get("summary")),
            "limitations": as_text(data.get("limitations")),
            "fields": {k: as_text(data.get(k)) for k in keys if as_text(data.get(k))},
        },
        "sources": ctx.sources + extra.sources,
        "ai_generated": True,
    }


@router.post("/ai/report-summary")
def report_summary(body: ReportSummaryIn, db: Session = Depends(get_db)):
    out = _run(db, "report_summary", F.report_summary_prompt(body.content), body.manual_response)
    if isinstance(out, dict):
        return out
    return {"text": out, "ai_generated": True}
