"""Voice & writing: recordings, transcripts, deterministic writing tools and reviewable
suggestions. Nothing is added to the backlog until a suggestion is approved."""

import logging
import shutil
import tempfile
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import AppError, bad_request, conflict, not_found
from app.models import Milestone, Project, Suggestion, Task, VoiceNote, WorkLog
from app.models.enums import Priority, TaskStatus, WorkLogKind
from app.models.voice import SuggestionKind, SuggestionStatus
from app.services import text_tools
from app.services.tasks import now, record, update_task
from app.services.transcription import TranscriptionUnavailable, get_provider

router = APIRouter(tags=["voice"])
log = logging.getLogger("app.voice")
AUDIO_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/aiff",
    "audio/x-aiff",
    "audio/m4a",
    "audio/x-m4a",
    "video/webm",
}
SUFFIX = {
    "audio/webm": ".webm",
    "video/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/m4a": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/aiff": ".aiff",
    "audio/x-aiff": ".aiff",
}


# ---------------------------------------------------------------- schemas
class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    project_id: uuid.UUID | None
    project_name: str | None = None
    source: str
    duration_seconds: float | None
    has_audio: bool = False
    audio_deleted_at: str | None = None
    transcript_raw: str | None
    transcript_edited: str | None
    transcription_provider: str | None
    created_at: str
    updated_at: str
    pending_suggestions: int = 0


class TextNoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=200_000)
    project_id: uuid.UUID | None = None


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    transcript_edited: str | None = Field(default=None, max_length=200_000)
    project_id: uuid.UUID | None = None


class TransformIn(BaseModel):
    output: str
    text: str | None = None  # defaults to the edited (or raw) transcript


class TransformOut(BaseModel):
    output: str
    label: str
    text: str | None
    needs_ai: bool = False
    message: str | None = None


class SaveUpdateIn(BaseModel):
    kind: WorkLogKind = WorkLogKind.PROGRESS
    entry_date: date
    text: str = Field(min_length=1, max_length=20_000)


class SuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: SuggestionKind
    status: SuggestionStatus
    source_type: str
    source_id: uuid.UUID | None
    project_id: uuid.UUID | None
    project_name: str | None = None
    generator: str
    payload: dict
    evidence: str | None
    duplicate_of_task_id: uuid.UUID | None
    duplicate_of_title: str | None = None
    created_task_id: uuid.UUID | None
    created_work_log_id: uuid.UUID | None


class SuggestionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    priority: Priority | None = None
    project_id: uuid.UUID | None = None


class ApproveIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    priority: Priority | None = None
    project_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    due_date: date | None = None
    entry_date: date | None = None
    allow_duplicate: bool = False


# ---------------------------------------------------------------- helpers
def _note(db: Session, nid: uuid.UUID) -> VoiceNote:
    n = db.get(VoiceNote, nid)
    if not n:
        raise not_found("Voice note")
    return n


def _note_out(db: Session, n: VoiceNote) -> NoteOut:
    pending = db.scalar(
        select(func.count())
        .select_from(Suggestion)
        .where(Suggestion.source_id == n.id, Suggestion.status == SuggestionStatus.PENDING)
    )
    return NoteOut.model_validate(
        {
            **{
                k: getattr(n, k)
                for k in (
                    "id",
                    "title",
                    "project_id",
                    "source",
                    "duration_seconds",
                    "transcript_raw",
                    "transcript_edited",
                    "transcription_provider",
                )
            },
            "project_name": n.project.name if n.project else None,
            "has_audio": bool(n.audio_path and Path(n.audio_path).is_file()),
            "audio_deleted_at": n.audio_deleted_at.isoformat() if n.audio_deleted_at else None,
            "created_at": n.created_at.isoformat(),
            "updated_at": n.updated_at.isoformat(),
            "pending_suggestions": pending or 0,
        }
    )


def _text(n: VoiceNote) -> str:
    return (n.transcript_edited or n.transcript_raw or "").strip()


def _recordings_dir() -> Path:
    d = Path(get_settings().recordings_dir).resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _delete_audio(n: VoiceNote) -> None:
    if n.audio_path:
        p = Path(n.audio_path)
        if p.is_file() and p.resolve().is_relative_to(_recordings_dir()):
            p.unlink()
        n.audio_path = None
        n.audio_deleted_at = now()


def _sugg_out(db: Session, s: Suggestion) -> SuggestionOut:
    dup = db.get(Task, s.duplicate_of_task_id) if s.duplicate_of_task_id else None
    return SuggestionOut.model_validate(
        {
            **{k: getattr(s, k) for k in SuggestionOut.model_fields if hasattr(s, k)},
            "project_name": s.project.name if s.project else None,
            "duplicate_of_title": dup.title if dup else None,
        }
    )


def _find_duplicate(db: Session, project_id, title: str) -> Task | None:
    if not project_id:
        return None
    for t in db.scalars(
        select(Task).where(Task.project_id == project_id, Task.archived_at.is_(None))
    ):
        if text_tools.similar(t.title, title):
            return t
    return None


# ---------------------------------------------------------------- status & notes
@router.get("/voice/status")
def voice_status():
    p = get_provider()
    ok, msg = p.available()
    s = get_settings()
    return {
        "provider": p.name,
        "available": ok,
        "message": msg,
        "retention": s.voice_retention,
        "retention_message": (
            "Recordings are deleted as soon as they are transcribed."
            if s.voice_retention == "delete"
            else "Recordings are kept until you delete them."
        ),
        "outputs": [
            {"key": k, "label": v[0], "needs_ai": False}
            for k, v in text_tools.DETERMINISTIC.items()
        ]
        + [{"key": k, "label": v, "needs_ai": True} for k, v in text_tools.NEEDS_AI.items()],
    }


@router.get("/voice/notes", response_model=list[NoteOut])
def list_notes(project_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    stmt = select(VoiceNote).order_by(VoiceNote.created_at.desc())
    if project_id:
        stmt = stmt.where(VoiceNote.project_id == project_id)
    return [_note_out(db, n) for n in db.scalars(stmt.limit(300)).unique()]


@router.post("/voice/notes/text", response_model=NoteOut, status_code=201)
def create_text_note(body: TextNoteIn, db: Session = Depends(get_db)):
    """A typed or pasted note (e.g. an email you need to respond to)."""
    if body.project_id and not db.get(Project, body.project_id):
        raise bad_request("Project does not exist.")
    n = VoiceNote(
        title=body.title,
        project_id=body.project_id,
        source="text",
        transcript_raw=body.text.strip(),
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return _note_out(db, n)


@router.post("/voice/notes", response_model=NoteOut, status_code=201)
def upload_recording(
    audio: UploadFile = File(...),
    title: str = Form(default="Voice note", max_length=300),
    project_id: uuid.UUID | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Transcribe a recording. With the default retention, the audio is deleted immediately
    after transcription; nothing is saved if transcription is unavailable."""
    ctype = (audio.content_type or "").split(";")[0].strip().lower()
    if ctype not in AUDIO_TYPES:
        raise bad_request("Unsupported audio format.", code="unsupported_media")
    if project_id and not db.get(Project, project_id):
        raise bad_request("Project does not exist.")
    provider = get_provider()
    ok, msg = provider.available()
    if not ok:
        raise AppError(503, "transcription_unavailable", msg)
    limit = get_settings().max_upload_mb * 1024 * 1024
    with tempfile.NamedTemporaryFile(suffix=SUFFIX.get(ctype, ".audio"), delete=False) as tmp:
        size = 0
        while chunk := audio.file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                Path(tmp.name).unlink(missing_ok=True)
                raise bad_request(f"Recording is larger than {get_settings().max_upload_mb} MB.")
            tmp.write(chunk)
        tmp_path = Path(tmp.name)
    try:
        result = provider.transcribe(tmp_path)
    except TranscriptionUnavailable as e:
        tmp_path.unlink(missing_ok=True)
        raise AppError(503, "transcription_unavailable", str(e)) from e
    except Exception as e:  # decoding errors etc. — never keep the file on failure
        log.exception("Transcription failed for %s", ctype)
        tmp_path.unlink(missing_ok=True)
        raise bad_request("The recording could not be transcribed.") from e
    n = VoiceNote(
        title=title.strip() or "Voice note",
        project_id=project_id,
        source="recording",
        duration_seconds=result.duration_seconds,
        transcript_raw=result.text,
        transcription_provider=result.provider,
    )
    db.add(n)
    db.flush()
    if get_settings().voice_retention == "keep":
        dest = _recordings_dir() / f"{n.id}{tmp_path.suffix}"
        shutil.move(tmp_path, dest)
        n.audio_path = str(dest)
    else:
        tmp_path.unlink(missing_ok=True)
        n.audio_deleted_at = now()
    db.commit()
    db.refresh(n)
    return _note_out(db, n)


@router.get("/voice/notes/{nid}", response_model=NoteOut)
def get_note(nid: uuid.UUID, db: Session = Depends(get_db)):
    return _note_out(db, _note(db, nid))


@router.patch("/voice/notes/{nid}", response_model=NoteOut)
def update_note(nid: uuid.UUID, body: NoteUpdate, db: Session = Depends(get_db)):
    n = _note(db, nid)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("project_id") and not db.get(Project, changes["project_id"]):
        raise bad_request("Project does not exist.")
    for k, v in changes.items():
        if k == "title" and v is None:
            continue
        setattr(n, k, v)
    db.commit()
    db.refresh(n)
    return _note_out(db, n)


@router.get("/voice/notes/{nid}/audio")
def get_audio(nid: uuid.UUID, db: Session = Depends(get_db)):
    n = _note(db, nid)
    if not n.audio_path or not Path(n.audio_path).is_file():
        raise not_found("Recording")
    return FileResponse(n.audio_path)


@router.delete("/voice/notes/{nid}/audio", response_model=NoteOut)
def delete_audio(nid: uuid.UUID, db: Session = Depends(get_db)):
    n = _note(db, nid)
    _delete_audio(n)
    db.commit()
    return _note_out(db, n)


@router.delete("/voice/notes/{nid}", status_code=204)
def delete_note(nid: uuid.UUID, db: Session = Depends(get_db)):
    """Deletes the note, its recording and its pending suggestions."""
    n = _note(db, nid)
    _delete_audio(n)
    for s in db.scalars(
        select(Suggestion).where(
            Suggestion.source_id == nid, Suggestion.status == SuggestionStatus.PENDING
        )
    ):
        db.delete(s)
    db.delete(n)
    db.commit()
    return Response(status_code=204)


@router.post("/voice/notes/{nid}/transform", response_model=TransformOut)
def transform(nid: uuid.UUID, body: TransformIn, db: Session = Depends(get_db)):
    n = _note(db, nid)
    text = (body.text if body.text is not None else _text(n)).strip()
    if body.output in text_tools.NEEDS_AI:
        return TransformOut(
            output=body.output,
            label=text_tools.NEEDS_AI[body.output],
            text=None,
            needs_ai=True,
            message="This output needs an AI writing provider, which is not "
            "configured. Deterministic outputs work without one.",
        )
    if body.output not in text_tools.DETERMINISTIC:
        raise bad_request("Unknown output type.")
    if not text:
        raise bad_request("There is no text to work with yet.")
    label, fn = text_tools.DETERMINISTIC[body.output]
    return TransformOut(output=body.output, label=label, text=fn(text))


@router.post("/voice/notes/{nid}/save-as-update", status_code=201)
def save_as_update(nid: uuid.UUID, body: SaveUpdateIn, db: Session = Depends(get_db)):
    n = _note(db, nid)
    log = WorkLog(
        entry_date=body.entry_date,
        kind=body.kind,
        summary=body.text.strip(),
        project_id=n.project_id,
    )
    db.add(log)
    db.commit()
    return {"work_log_id": str(log.id)}


@router.post("/voice/notes/{nid}/suggestions", response_model=list[SuggestionOut], status_code=201)
def suggest(nid: uuid.UUID, db: Session = Depends(get_db)):
    """Extract suggested tasks, blockers, decisions and progress using deterministic rules.
    Suggestions already raised for this note, and likely duplicates of existing tasks, are
    flagged rather than silently created again."""
    n = _note(db, nid)
    text = _text(n)
    if not text:
        raise bad_request("There is no text to analyse yet.")
    existing = list(db.scalars(select(Suggestion).where(Suggestion.source_id == nid)))
    created = []
    for item in text_tools.extract(text):
        if any(
            e.kind.value == item["kind"]
            and text_tools.similar(e.payload.get("title", ""), item["title"])
            for e in existing + created
        ):
            continue
        dup = _find_duplicate(db, n.project_id, item["title"]) if item["kind"] == "task" else None
        s = Suggestion(
            kind=SuggestionKind(item["kind"]),
            source_type="voice_note",
            source_id=nid,
            project_id=n.project_id,
            generator="rules",
            payload={"title": item["title"], "priority": "medium"},
            evidence=item["evidence"],
            duplicate_of_task_id=dup.id if dup else None,
        )
        db.add(s)
        created.append(s)
    db.commit()
    return [_sugg_out(db, s) for s in created]


# ---------------------------------------------------------------- suggestions review
@router.get("/suggestions", response_model=list[SuggestionOut])
def list_suggestions(
    status: SuggestionStatus | None = SuggestionStatus.PENDING,
    source_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Suggestion).order_by(Suggestion.created_at)
    if status:
        stmt = stmt.where(Suggestion.status == status)
    if source_id:
        stmt = stmt.where(Suggestion.source_id == source_id)
    if project_id:
        stmt = stmt.where(Suggestion.project_id == project_id)
    return [_sugg_out(db, s) for s in db.scalars(stmt.limit(500)).unique()]


def _pending(db: Session, sid: uuid.UUID) -> Suggestion:
    s = db.get(Suggestion, sid)
    if not s:
        raise not_found("Suggestion")
    if s.status not in (SuggestionStatus.PENDING, SuggestionStatus.DEFERRED):
        raise conflict(f"This suggestion has already been {s.status.value}.")
    return s


@router.patch("/suggestions/{sid}", response_model=SuggestionOut)
def edit_suggestion(sid: uuid.UUID, body: SuggestionUpdate, db: Session = Depends(get_db)):
    s = _pending(db, sid)
    changes = body.model_dump(exclude_unset=True)
    if "project_id" in changes:
        if changes["project_id"] and not db.get(Project, changes["project_id"]):
            raise bad_request("Project does not exist.")
        s.project_id = changes.pop("project_id")
    s.payload = {
        **s.payload,
        **{k: (v.value if hasattr(v, "value") else v) for k, v in changes.items() if v is not None},
    }
    if s.kind == SuggestionKind.TASK:
        dup = _find_duplicate(db, s.project_id, s.payload.get("title", ""))
        s.duplicate_of_task_id = dup.id if dup else None
    db.commit()
    return _sugg_out(db, s)


@router.post("/suggestions/{sid}/approve", response_model=SuggestionOut)
def approve(sid: uuid.UUID, body: ApproveIn, db: Session = Depends(get_db)):
    s = _pending(db, sid)
    if s.kind == SuggestionKind.TASK_UPDATE:
        task = db.get(Task, uuid.UUID(s.payload["task_id"])) if s.payload.get("task_id") else None
        if not task or task.archived_at:
            raise bad_request("The task no longer exists.")
        changes = {"status": TaskStatus(s.payload.get("status", "completed"))}
        update_task(db, task, changes)
        record(db, task, "updated", {"source": [None, f"Approved suggestion from {s.generator}"]})
        s.created_task_id = task.id
        s.status, s.reviewed_at = SuggestionStatus.APPROVED, now()
        db.commit()
        return _sugg_out(db, s)
    title = (body.title or s.payload.get("title", "")).strip()
    project_id = body.project_id or s.project_id
    if not title:
        raise bad_request("A title is required.")
    if s.kind == SuggestionKind.TASK:
        if not project_id or not db.get(Project, project_id):
            raise bad_request("Choose a project for this task.")
        dup = _find_duplicate(db, project_id, title)
        if dup and not body.allow_duplicate:
            raise conflict(
                f"A similar task already exists: “{dup.title}”. Edit the title, "
                "reject the suggestion, or approve it as a duplicate on purpose.",
                code="possible_duplicate",
            )
        if body.milestone_id:
            ms = db.get(Milestone, body.milestone_id)
            if not ms or ms.project_id != project_id:
                raise bad_request("Milestone does not belong to this project.")
        max_pos = db.scalar(select(func.max(Task.position)).where(Task.project_id == project_id))
        parent = None
        if s.payload.get("parent_id"):
            parent = db.get(Task, uuid.UUID(s.payload["parent_id"]))
            if not parent or parent.project_id != project_id:
                raise bad_request("The parent task no longer exists in this project.")
        origin = "an AI suggestion" if s.generator.startswith("ai:") else "a voice/text note"
        t = Task(
            project_id=project_id,
            title=title,
            priority=body.priority or Priority(s.payload.get("priority", "medium")),
            milestone_id=body.milestone_id or (parent.milestone_id if parent else None),
            workstream_id=parent.workstream_id if parent else None,
            parent_id=parent.id if parent else None,
            due_date=body.due_date,
            estimate_hours=s.payload.get("estimate_hours"),
            acceptance_criteria=s.payload.get("acceptance_criteria"),
            description=f"From {origin}: “{s.evidence}”" if s.evidence else None,
            position=(max_pos or 0) + 1000,
            labels=[],
        )
        db.add(t)
        db.flush()
        record(
            db, t, "created", {"title": [None, t.title], "source": [None, "Approved suggestion"]}
        )
        s.created_task_id = t.id
    else:
        kind = {
            SuggestionKind.BLOCKER: WorkLogKind.BLOCKER,
            SuggestionKind.DECISION: WorkLogKind.DECISION,
            SuggestionKind.PROGRESS: WorkLogKind.PROGRESS,
        }[s.kind]
        log = WorkLog(
            entry_date=body.entry_date or date.today(),
            kind=kind,
            summary=s.evidence or title,
            project_id=project_id,
        )
        db.add(log)
        db.flush()
        s.created_work_log_id = log.id
    s.project_id = project_id
    s.status, s.reviewed_at = SuggestionStatus.APPROVED, now()
    db.commit()
    return _sugg_out(db, s)


@router.post("/suggestions/{sid}/reject", response_model=SuggestionOut)
def reject(sid: uuid.UUID, db: Session = Depends(get_db)):
    s = _pending(db, sid)
    s.status, s.reviewed_at = SuggestionStatus.REJECTED, now()
    db.commit()
    return _sugg_out(db, s)


@router.post("/suggestions/{sid}/defer", response_model=SuggestionOut)
def defer(sid: uuid.UUID, db: Session = Depends(get_db)):
    s = _pending(db, sid)
    s.status, s.reviewed_at = SuggestionStatus.DEFERRED, now()
    db.commit()
    return _sugg_out(db, s)
