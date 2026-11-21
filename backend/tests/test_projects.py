def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


def test_stages_are_seeded(client):
    names = [s["name"] for s in client.get("/api/stages").json()]
    assert names[0] == "Discovery" and "Maintenance" in names


def test_create_project_with_workstreams(client):
    stage = client.get("/api/stages").json()[0]
    r = client.post(
        "/api/projects",
        json={
            "name": "Workspace MVP",
            "objectives": "Ship it",
            "start_date": "2026-11-01",
            "target_date": "2027-01-31",
            "priority": "high",
            "stage_id": stage["id"],
            "workstreams": ["Backend", " ", "Frontend"],
        },
    )
    assert r.status_code == 201
    p = r.json()
    assert p["status"] == "active" and p["stage"]["name"] == "Discovery"
    assert p["progress"]["method"] == "none"
    ws = client.get(f"/api/projects/{p['id']}/workstreams").json()
    assert [w["name"] for w in ws] == ["Backend", "Frontend"]


def test_project_validation(client):
    r = client.post("/api/projects", json={"name": ""})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    r = client.post(
        "/api/projects",
        json={"name": "Bad dates", "start_date": "2026-12-01", "target_date": "2026-11-01"},
    )
    assert r.status_code == 422
    assert "before the start date" in r.json()["error"]["message"]


def test_update_search_and_archive(client, project):
    pid = project["id"]
    r = client.patch(f"/api/projects/{pid}", json={"description": "Searchable words"})
    assert r.json()["description"] == "Searchable words"
    assert [p["id"] for p in client.get("/api/projects?q=searchable").json()] == [pid]
    assert client.get("/api/projects?q=nothing-matches").json() == []

    r = client.post(f"/api/projects/{pid}/archive")
    assert r.json()["status"] == "archived" and r.json()["archived_at"]
    assert client.get("/api/projects").json() == []
    assert len(client.get("/api/projects?include_archived=true").json()) == 1

    r = client.post(f"/api/projects/{pid}/restore")
    assert r.json()["status"] == "active" and r.json()["archived_at"] is None


def test_delete_requires_exact_name(client, project):
    pid = project["id"]
    r = client.delete(f"/api/projects/{pid}", params={"confirm": "wrong"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "confirmation_required"
    assert (
        client.delete(f"/api/projects/{pid}", params={"confirm": "Test project"}).status_code == 204
    )
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_unknown_project_is_404(client):
    r = client.get("/api/projects/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.json()["error"]["message"] == "Project not found."


def test_milestone_lifecycle_and_warnings(client, project, make_task):
    pid = project["id"]
    r = client.post(
        f"/api/projects/{pid}/milestones",
        json={"title": "Alpha", "due_date": "2020-01-01"},
    )
    assert r.status_code == 201
    ms = r.json()
    assert "No deliverables defined." in ms["warnings"]
    assert "No tasks linked to this milestone." in ms["warnings"]
    assert "Due date has passed." in ms["warnings"]

    make_task(title="One", milestone_id=ms["id"], acceptance_criteria="Done when X")
    r = client.patch(
        f"/api/milestones/{ms['id']}",
        json={"deliverables": "Working build", "status": "achieved"},
    )
    body = r.json()
    assert body["achieved_at"] is not None
    assert body["warnings"] == []  # achieved milestones are not flagged as overdue

    other = client.post("/api/projects", json={"name": "Other"}).json()
    ws_other = client.post(f"/api/projects/{other['id']}/workstreams", json={"name": "X"}).json()
    r = client.post(
        f"/api/projects/{pid}/milestones", json={"title": "Bad", "workstream_id": ws_other["id"]}
    )
    assert r.status_code == 400


def test_deleting_workstream_keeps_tasks(client, project, make_task):
    ws = client.get(f"/api/projects/{project['id']}/workstreams").json()[0]
    t = make_task(workstream_id=ws["id"])
    assert client.delete(f"/api/workstreams/{ws['id']}").status_code == 204
    assert client.get(f"/api/tasks/{t['id']}").json()["workstream_id"] is None
