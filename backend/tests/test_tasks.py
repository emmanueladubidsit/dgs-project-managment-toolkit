from datetime import date, timedelta


def test_create_task_defaults_and_history(client, make_task):
    t = make_task(title="Write API", priority="high", labels=["api", " api ", ""])
    assert t["status"] == "todo" and t["progress"] == 0
    assert t["labels"] == ["api"]
    assert t["project_name"] == "Test project"
    hist = client.get(f"/api/tasks/{t['id']}/activity").json()
    assert [h["action"] for h in hist] == ["created"]


def test_status_and_progress_are_independent(client, make_task):
    t = make_task()
    r = client.patch(f"/api/tasks/{t['id']}", json={"status": "in_progress", "progress": 40})
    body = r.json()
    assert body["status"] == "in_progress" and body["progress"] == 40
    assert body["completed_at"] is None


def test_completion_sets_date_and_100_and_reopen_clears(client, make_task):
    t = make_task()
    body = client.patch(f"/api/tasks/{t['id']}", json={"status": "completed"}).json()
    assert body["progress"] == 100 and body["completed_at"]
    body = client.patch(f"/api/tasks/{t['id']}", json={"status": "in_progress"}).json()
    assert body["completed_at"] is None and body["progress"] == 100


def test_history_records_field_changes(client, make_task):
    t = make_task()
    client.patch(f"/api/tasks/{t['id']}", json={"priority": "critical", "title": "Renamed"})
    latest = client.get(f"/api/tasks/{t['id']}/activity").json()[0]
    assert latest["action"] == "updated"
    assert latest["changes"]["priority"] == ["medium", "critical"]
    assert latest["changes"]["title"] == ["A task", "Renamed"]


def test_no_history_for_noop_update(client, make_task):
    t = make_task()
    client.patch(f"/api/tasks/{t['id']}", json={"priority": "medium"})
    assert len(client.get(f"/api/tasks/{t['id']}/activity").json()) == 1


def test_validation_errors(client, project, make_task):
    r = client.post("/api/tasks", json={"project_id": project["id"], "title": "x", "progress": 150})
    assert r.status_code == 422
    r = client.post(
        "/api/tasks",
        json={
            "project_id": project["id"],
            "title": "x",
            "start_date": "2026-02-02",
            "due_date": "2026-02-01",
        },
    )
    assert r.status_code == 422
    t = make_task(start_date="2026-02-01")
    r = client.patch(f"/api/tasks/{t['id']}", json={"due_date": "2026-01-01"})
    assert r.status_code == 400


def test_subtasks_do_not_auto_complete_parent(client, make_task):
    parent = make_task(title="Parent")
    s1 = make_task(title="Sub 1", parent_id=parent["id"])
    make_task(title="Sub 2", parent_id=parent["id"])
    client.patch(f"/api/tasks/{s1['id']}", json={"status": "completed"})
    detail = client.get(f"/api/tasks/{parent['id']}").json()
    assert detail["status"] == "todo"
    assert detail["subtask_count"] == 2 and detail["subtasks_completed"] == 1
    assert [s["title"] for s in detail["subtasks"]] == ["Sub 1", "Sub 2"]


def test_parent_cycle_rejected(client, make_task):
    a = make_task(title="A")
    b = make_task(title="B", parent_id=a["id"])
    r = client.patch(f"/api/tasks/{a['id']}", json={"parent_id": b["id"]})
    assert r.status_code == 400 and "circular" in r.json()["error"]["message"]
    r = client.patch(f"/api/tasks/{a['id']}", json={"parent_id": a["id"]})
    assert r.status_code == 400


def test_cross_project_references_rejected(client, project, make_task):
    other = client.post("/api/projects", json={"name": "Other"}).json()
    ms = client.post(f"/api/projects/{other['id']}/milestones", json={"title": "M"}).json()
    r = client.post(
        "/api/tasks", json={"project_id": project["id"], "title": "x", "milestone_id": ms["id"]}
    )
    assert r.status_code == 400


def test_dependencies_and_blocked_detection(client, make_task):
    a = make_task(title="Design")
    b = make_task(title="Build")
    r = client.post(f"/api/tasks/{b['id']}/dependencies", json={"depends_on_id": a["id"]})
    assert r.status_code == 201
    assert [d["title"] for d in r.json()["open_dependencies"]] == ["Design"]
    assert [t["title"] for t in client.get("/api/tasks?blocked=true").json()] == ["Build"]

    # duplicate, self and circular dependencies are rejected
    assert (
        client.post(
            f"/api/tasks/{b['id']}/dependencies", json={"depends_on_id": a["id"]}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/tasks/{a['id']}/dependencies", json={"depends_on_id": a["id"]}
        ).status_code
        == 400
    )
    r = client.post(f"/api/tasks/{a['id']}/dependencies", json={"depends_on_id": b["id"]})
    assert r.status_code == 400 and "circular" in r.json()["error"]["message"]

    client.patch(f"/api/tasks/{a['id']}", json={"status": "completed"})
    assert client.get("/api/tasks?blocked=true").json() == []
    detail = client.get(f"/api/tasks/{a['id']}").json()
    assert [d["title"] for d in detail["dependents"]] == ["Build"]

    r = client.delete(f"/api/tasks/{b['id']}/dependencies/{a['id']}")
    assert r.status_code == 200 and r.json()["dependencies"] == []


def test_filters_and_sorting(client, make_task):
    today = date.today()
    make_task(title="Low later", priority="low", due_date=str(today + timedelta(days=5)))
    make_task(
        title="Critical overdue", priority="critical", due_date=str(today - timedelta(days=1))
    )
    make_task(title="Blocked one", status="blocked")
    titles = lambda r: [t["title"] for t in r.json()]  # noqa: E731
    assert titles(client.get("/api/tasks?sort=priority"))[0] == "Critical overdue"
    assert titles(client.get("/api/tasks?overdue=true")) == ["Critical overdue"]
    assert titles(client.get("/api/tasks?status=blocked")) == ["Blocked one"]
    assert titles(client.get("/api/tasks?q=later")) == ["Low later"]
    assert len(client.get("/api/tasks?priority=low&priority=critical").json()) == 2
    overdue = client.get("/api/tasks?overdue=true").json()[0]
    assert overdue["is_overdue"] is True


def test_comments(client, make_task):
    t = make_task()
    r = client.post(f"/api/tasks/{t['id']}/comments", json={"body": "  Looks good  "})
    assert r.status_code == 201 and r.json()["body"] == "Looks good"
    assert len(client.get(f"/api/tasks/{t['id']}/comments").json()) == 1
    assert client.post(f"/api/tasks/{t['id']}/comments", json={"body": ""}).status_code == 422


def test_bulk_update(client, make_task):
    a, b = make_task(title="a"), make_task(title="b")
    r = client.post(
        "/api/tasks/bulk", json={"task_ids": [a["id"], b["id"]], "changes": {"priority": "high"}}
    )
    assert r.status_code == 200 and {t["priority"] for t in r.json()} == {"high"}
    r = client.post("/api/tasks/bulk", json={"task_ids": [a["id"]], "changes": {"title": "x"}})
    assert r.status_code == 400


def test_archive_and_safe_delete(client, make_task):
    t = make_task()
    client.post(f"/api/tasks/{t['id']}/archive")
    assert client.get("/api/tasks").json() == []
    assert len(client.get("/api/tasks?include_archived=true").json()) == 1
    r = client.delete(f"/api/tasks/{t['id']}")
    assert r.status_code == 400 and r.json()["error"]["code"] == "confirmation_required"
    assert client.delete(f"/api/tasks/{t['id']}?confirm=true").status_code == 204
    assert client.get(f"/api/tasks/{t['id']}").status_code == 404


def test_kanban_move_reorders(client, make_task):
    a, b = make_task(title="a"), make_task(title="b")
    assert b["position"] > a["position"]
    client.patch(
        f"/api/tasks/{b['id']}", json={"position": a["position"] - 1, "status": "in_review"}
    )
    assert [t["title"] for t in client.get("/api/tasks?sort=position").json()] == ["b", "a"]
