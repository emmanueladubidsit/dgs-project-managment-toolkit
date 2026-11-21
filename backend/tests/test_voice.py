from datetime import date
from pathlib import Path

import pytest

from app.api import voice as voice_api
from app.config import get_settings
from app.services import text_tools
from app.services.transcription import NoProvider, Transcription

RAMBLE = ("um so basically we finished the the login page. "
          "we need to update the api docs. i'll organize the design review. "
          "we decided to use postgres. we're blocked waiting on the security review.")  # fmt: skip


# ---------------------------------------------------------------- deterministic text tools
def test_clean_removes_filler_repeats_and_uses_british_spelling():
    out = text_tools.clean(RAMBLE)
    assert "um" not in out.lower().split() and "basically" not in out.lower()
    assert "the the" not in out
    assert "organise" in out and "I'll" in out
    assert out.startswith("So we finished the login page.")


def test_extract_classifies_sentences():
    kinds = [(s["kind"], s["title"]) for s in text_tools.extract(RAMBLE)]
    assert ("task", "Update the api docs") in kinds
    assert ("task", "Organise the design review") in kinds
    assert any(k == "decision" for k, _ in kinds)
    assert any(k == "blocker" for k, _ in kinds)
    assert any(k == "progress" for k, _ in kinds)


def test_similarity_for_duplicates():
    assert text_tools.similar("Update the API docs", "update the api docs.")
    assert not text_tools.similar("Update the API docs", "Write release notes")


# ---------------------------------------------------------------- API
def note(client, project=None, text=RAMBLE):
    r = client.post(
        "/api/voice/notes/text",
        json={"title": "Stand-up", "text": text, "project_id": project["id"] if project else None},
    )
    assert r.status_code == 201
    return r.json()


def test_status_lists_outputs_honestly(client):
    s = client.get("/api/voice/status").json()
    assert s["retention"] == "delete"
    by_key = {o["key"]: o["needs_ai"] for o in s["outputs"]}
    assert by_key["clean_transcript"] is False and by_key["email_draft"] is True


def test_transform_deterministic_and_ai_outputs(client):
    n = note(client)
    r = client.post(
        f"/api/voice/notes/{n['id']}/transform", json={"output": "task_breakdown"}
    ).json()
    assert "- [ ] Update the api docs" in r["text"]
    r = client.post(f"/api/voice/notes/{n['id']}/transform", json={"output": "email_draft"}).json()
    assert r["needs_ai"] is True and r["text"] is None  # never faked
    assert (
        client.post(f"/api/voice/notes/{n['id']}/transform", json={"output": "nope"}).status_code
        == 400
    )


def test_suggestions_review_flow(client, project, make_task):
    make_task(title="Update the API docs")  # an existing task the note repeats
    n = note(client, project)
    created = client.post(f"/api/voice/notes/{n['id']}/suggestions").json()
    tasks = [s for s in created if s["kind"] == "task"]
    dup = next(s for s in tasks if s["payload"]["title"] == "Update the api docs")
    assert dup["duplicate_of_title"] == "Update the API docs"
    # Re-running does not create the same suggestions again
    assert client.post(f"/api/voice/notes/{n['id']}/suggestions").json() == []
    # Approving a likely duplicate is refused unless explicitly allowed
    r = client.post(f"/api/suggestions/{dup['id']}/approve", json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "possible_duplicate"
    assert client.post(f"/api/suggestions/{dup['id']}/reject").json()["status"] == "rejected"
    # A new task is created only on approval, with edits applied
    other = next(s for s in tasks if s["id"] != dup["id"])
    client.patch(
        f"/api/suggestions/{other['id']}",
        json={"title": "Organise design review", "priority": "high"},
    )
    approved = client.post(f"/api/suggestions/{other['id']}/approve", json={}).json()
    task = client.get(f"/api/tasks/{approved['created_task_id']}").json()
    assert task["title"] == "Organise design review" and task["priority"] == "high"
    assert "From a voice/text note" in task["description"]
    # Blockers become work logs; a reviewed suggestion cannot be approved twice
    blocker = next(s for s in created if s["kind"] == "blocker")
    b = client.post(
        f"/api/suggestions/{blocker['id']}/approve", json={"entry_date": str(date.today())}
    ).json()
    assert b["created_work_log_id"]
    assert client.post(f"/api/suggestions/{blocker['id']}/approve", json={}).status_code == 409
    decision = next(s for s in created if s["kind"] == "decision")
    assert client.post(f"/api/suggestions/{decision['id']}/defer").json()["status"] == "deferred"
    assert len(client.get("/api/suggestions?status=deferred").json()) == 1


def test_task_suggestion_needs_a_project(client):
    n = note(client)
    s = next(
        x
        for x in client.post(f"/api/voice/notes/{n['id']}/suggestions").json()
        if x["kind"] == "task"
    )
    assert client.post(f"/api/suggestions/{s['id']}/approve", json={}).status_code == 400


def test_save_as_update(client, project):
    n = note(client, project)
    r = client.post(
        f"/api/voice/notes/{n['id']}/save-as-update",
        json={"kind": "progress", "entry_date": str(date.today()), "text": "Login page done"},
    )
    assert r.status_code == 201
    logs = client.get(f"/api/work-logs?project_id={project['id']}").json()
    assert logs[0]["summary"] == "Login page done"


# ---------------------------------------------------------------- recordings
class FakeWhisper:
    name = "fake-whisper"

    def available(self):
        return True, "fake"

    def transcribe(self, path: Path) -> Transcription:
        assert path.exists()
        FakeWhisper.seen = path
        return Transcription(
            text="we need to test recordings.", duration_seconds=2.5, provider=self.name
        )


def upload(client, ctype="audio/webm"):
    return client.post(
        "/api/voice/notes",
        data={"title": "Memo"},
        files={"audio": ("memo.webm", b"\x1a\x45\xdf\xa3fake", ctype)},
    )


def test_upload_unavailable_and_unsupported(client, monkeypatch):
    monkeypatch.setattr(voice_api, "get_provider", lambda: NoProvider())
    r = upload(client)
    assert r.status_code == 503 and r.json()["error"]["code"] == "transcription_unavailable"
    assert client.get("/api/voice/notes").json() == []  # nothing saved
    assert upload(client, "application/pdf").status_code == 400


def test_recording_deleted_after_transcription_by_default(client, monkeypatch):
    monkeypatch.setattr(voice_api, "get_provider", lambda: FakeWhisper())
    r = upload(client)
    assert r.status_code == 201, r.text
    n = r.json()
    assert n["transcript_raw"] == "we need to test recordings." and n["duration_seconds"] == 2.5
    assert n["has_audio"] is False and n["audio_deleted_at"]
    assert not FakeWhisper.seen.exists()


@pytest.fixture
def keep_audio(monkeypatch, tmp_path):
    s = get_settings()
    monkeypatch.setattr(s, "voice_retention", "keep")
    monkeypatch.setattr(s, "recordings_dir", str(Path(__file__).parent / "_tmp_recordings"))
    yield
    import shutil

    shutil.rmtree(Path(__file__).parent / "_tmp_recordings", ignore_errors=True)


def test_keep_retention_and_delete_controls(client, monkeypatch, keep_audio):
    monkeypatch.setattr(voice_api, "get_provider", lambda: FakeWhisper())
    n = upload(client).json()
    assert n["has_audio"] is True
    assert client.get(f"/api/voice/notes/{n['id']}/audio").status_code == 200
    after = client.delete(f"/api/voice/notes/{n['id']}/audio").json()
    assert after["has_audio"] is False
    assert client.get(f"/api/voice/notes/{n['id']}/audio").status_code == 404
    assert client.delete(f"/api/voice/notes/{n['id']}").status_code == 204
