"""AI assistant: tested against a fake OpenAI-compatible server (real HTTP shape, no model)."""

import json

import httpx
import pytest

from app.services.ai import provider as provider_mod


class FakeLLM:
    """Records requests and replies with whatever the test queues."""

    def __init__(self):
        self.replies: list = []
        self.requests: list[dict] = []
        self.status = 200

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "llama3.1:8b"}, {"id": "qwen3:14b"}]})
        body = json.loads(request.content)
        self.requests.append({"body": body, "headers": dict(request.headers)})
        if self.status != 200:
            return httpx.Response(self.status, json={"error": {"message": "nope"}})
        reply = self.replies.pop(0) if self.replies else "ok"
        content = reply if isinstance(reply, str) else json.dumps(reply)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


@pytest.fixture
def llm(monkeypatch, client):
    fake = FakeLLM()
    real = httpx.Client
    monkeypatch.setattr(
        provider_mod.httpx,
        "Client",
        lambda **kw: real(transport=httpx.MockTransport(fake.handler), **kw),
    )
    r = client.put("/api/ai/settings", json={"provider": "openai_compatible", "preset": "ollama",
                                             "base_url": "http://localhost:11434/v1",
                                             "model": "llama3.1:8b"})  # fmt: skip
    assert r.status_code == 200, r.text
    yield fake
    from sqlalchemy import text

    from app.db import engine

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE system_settings, ai_interactions"))


def test_disabled_by_default_explains_how_to_enable(client):
    s = client.get("/api/ai/status").json()
    assert s["provider"] == "disabled" and s["ready"] is False and s["api_key_set"] is False
    assert "ollama" in s["presets"]
    r = client.post("/api/ai/ask", json={"question": "How is it going?"})
    assert r.status_code == 503 and "turned off" in r.json()["error"]["message"]


def test_settings_validation(client):
    assert (
        client.put(
            "/api/ai/settings", json={"provider": "openai_compatible", "base_url": "", "model": ""}
        ).status_code
        == 400
    )
    r = client.put(
        "/api/ai/settings",
        json={"provider": "openai_compatible", "base_url": "ftp://x", "model": "m"},
    )
    assert r.status_code == 422


def test_connection_test_and_models(client, llm):
    llm.replies = ["ready"]
    r = client.post("/api/ai/test").json()
    assert r["ok"] and r["reply"] == "ready"
    assert client.get("/api/ai/models").json()["models"] == ["llama3.1:8b", "qwen3:14b"]
    sent = llm.requests[0]["body"]
    assert sent["model"] == "llama3.1:8b" and sent["messages"][0]["role"] == "system"


def test_ask_is_grounded_in_project_data_with_sources(client, llm, project, make_task):
    make_task(title="Write API docs", status="blocked")
    llm.replies = ["The API docs task is blocked."]
    r = client.post(
        "/api/ai/ask", json={"question": "What is blocked?", "project_id": project["id"]}
    ).json()
    assert r["answer"] == "The API docs task is blocked." and r["ai_generated"] is True
    assert {"type": "task", "title": "Write API docs"}.items() <= next(
        s for s in r["sources"] if s["type"] == "task"
    ).items()
    prompt = llm.requests[0]["body"]["messages"][1]["content"]
    assert "Write API docs [blocked" in prompt and "Test project" in prompt
    system = llm.requests[0]["body"]["messages"][0]["content"]
    assert "British English" in system and "Never invent" in system


def test_write_uses_context_and_never_saves(client, llm, project):
    llm.replies = ["Subject: Re: timeline\n\nThanks — [date to confirm]."]
    r = client.post(
        "/api/ai/write",
        json={"output": "email_draft", "text": "When will it ship?", "project_id": project["id"]},
    ).json()
    assert r["text"].startswith("Subject:") and r["label"] == "Email draft"
    assert client.post("/api/ai/write", json={"output": "poem", "text": "x"}).status_code == 400


def test_suggest_creates_pending_suggestions_with_duplicate_checks(client, llm, project, make_task):
    make_task(title="Update the API docs")
    llm.replies = [[
        {"kind": "task", "title": "Update the API docs", "priority": "high"},
        {"kind": "task", "title": "Write release notes", "priority": "urgent", "estimate_hours": 2,
         "acceptance_criteria": "Notes published", "evidence": "we need release notes"},
        {"kind": "decision", "title": "Ship on Friday"},
        {"kind": "nonsense", "title": "ignored"},
    ]]  # fmt: skip
    created = client.post(
        "/api/ai/suggest", json={"text": "notes…", "project_id": project["id"]}
    ).json()
    assert len(created) == 3
    dup = next(s for s in created if s["payload"]["title"] == "Update the API docs")
    assert dup["duplicate_of_title"] == "Update the API docs"
    notes = next(s for s in created if s["payload"]["title"] == "Write release notes")
    assert notes["payload"]["priority"] == "medium"  # invalid priority normalised
    assert notes["generator"] == "ai:llama3.1:8b"
    # Nothing was added to the backlog yet
    assert len(client.get(f"/api/tasks?project_id={project['id']}").json()) == 1
    t = client.post(f"/api/suggestions/{notes['id']}/approve", json={}).json()
    task = client.get(f"/api/tasks/{t['created_task_id']}").json()
    assert task["estimate_hours"] == "2.00" and task["acceptance_criteria"] == "Notes published"
    assert "From an AI suggestion" in task["description"]


def test_breakdown_suggests_subtasks_that_become_children(client, llm, make_task):
    parent = make_task(title="Build login")
    llm.replies = ["Here you go:\n```json\n" + json.dumps([
        {"title": "Design login form", "estimate_hours": 2},
        {"title": "Add session handling", "acceptance_criteria": "Users stay signed in"},
    ]) + "\n```"]  # fmt: skip
    subs = client.post(f"/api/ai/breakdown/{parent['id']}", json={}).json()
    assert [s["payload"]["title"] for s in subs] == ["Design login form", "Add session handling"]
    approved = client.post(f"/api/suggestions/{subs[0]['id']}/approve", json={}).json()
    child = client.get(f"/api/tasks/{approved['created_task_id']}").json()
    assert child["parent_id"] == parent["id"]


def test_structure_project_returns_unsaved_draft(client, llm):
    llm.replies = [{"name": "Tutor match", "objectives": ["Match tutors", "Track sessions"],
                    "workstreams": ["Backend", "Frontend"], "assumptions": ["Parents pay"],
                    "unknowns": ["Budget?"], "description": "An app"}]  # fmt: skip
    r = client.post(
        "/api/ai/structure-project", json={"idea": "An app to match tutors with students"}
    ).json()
    d = r["draft"]
    assert d["name"] == "Tutor match" and d["objectives"] == "Match tutors\nTrack sessions"
    assert "Assumptions (to confirm):" in d["risks_assumptions"] and "Budget?" in d["notes"]
    assert d["workstreams"] == ["Backend", "Frontend"]
    assert client.get("/api/projects").json() == []  # not saved


def test_research_draft_is_marked_ai_suggestion(client, llm):
    llm.replies = [
        {"title": "Auth options", "findings": ["Sessions", "Tokens"], "conclusions": "Sessions"}
    ]
    d = client.post("/api/ai/research-draft", json={"question": "Which auth?"}).json()["draft"]
    assert d["verification"] == "ai_suggestion" and d["fields"]["findings"] == "Sessions\nTokens"


def test_bad_json_and_service_errors_are_explained(client, llm):
    llm.replies = ["I cannot help with that."]
    r = client.post("/api/ai/structure-project", json={"idea": "Some idea for a project"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "ai_format"
    llm.status = 401
    r = client.post("/api/ai/ask", json={"question": "Hello there"})
    assert r.status_code == 503 and "AI_API_KEY" in r.json()["error"]["message"]
    usage = client.get("/api/ai/usage").json()
    assert usage[0]["ok"] is False and "401" in usage[0]["error"]
    assert all("prompt" not in u for u in usage)  # content is never logged


def test_manual_mode_round_trip(client):
    client.put("/api/ai/settings", json={"provider": "manual"})
    r = client.post("/api/ai/ask", json={"question": "Summarise my week"}).json()
    assert r["needs_manual"] is True and "Summarise my week" in r["prompt"]
    r = client.post(
        "/api/ai/ask", json={"question": "Summarise my week", "manual_response": "A good week."}
    ).json()
    assert r["answer"] == "A good week."
    assert (
        client.post("/api/ai/ask", json={"question": "Again", "manual_response": " "}).status_code
        == 503
    )
