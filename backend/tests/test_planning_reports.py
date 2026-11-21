from datetime import date, timedelta

TODAY = date.today()
MONDAY = TODAY - timedelta(days=TODAY.weekday())


def test_day_plan_scheduling_and_capacity(client, make_task):
    d = str(TODAY)
    make_task(title="Planned", scheduled_date=d, estimate_hours=3)
    make_task(title="No estimate", scheduled_date=d)
    make_task(title="Old", scheduled_date=str(TODAY - timedelta(days=2)))
    make_task(title="Due today", due_date=d)
    plan = client.get(f"/api/planner/day?date={d}").json()
    assert {t["title"] for t in plan["scheduled"]} == {"Planned", "No estimate"}
    assert [t["title"] for t in plan["carried_over"]] == ["Old"]
    assert [t["title"] for t in plan["due_unscheduled"]] == ["Due today"]
    cap = plan["capacity"]
    assert cap["planned_hours"] == 3 and cap["available_hours"] is None
    assert cap["over_capacity"] is False and "not been set" in cap["message"]

    client.put(
        "/api/planner/notes",
        json={"period": "day", "period_start": d, "available_hours": 2, "objectives": "Finish API"},
    )
    plan = client.get(f"/api/planner/day?date={d}").json()
    assert plan["capacity"]["over_capacity"] is True
    assert plan["note"]["objectives"] == "Finish API"


def test_carry_forward_reschedules_unfinished(client, make_task):
    old = make_task(title="Old", scheduled_date=str(TODAY - timedelta(days=3)))
    done = make_task(
        title="Done", scheduled_date=str(TODAY - timedelta(days=3)), status="completed"
    )
    r = client.post("/api/planner/carry-forward", json={"to_date": str(TODAY)})
    assert [t["id"] for t in r.json()] == [old["id"]]
    assert client.get(f"/api/tasks/{old['id']}").json()["scheduled_date"] == str(TODAY)
    assert client.get(f"/api/tasks/{done['id']}").json()["scheduled_date"] != str(TODAY)


def test_week_plan_planned_vs_completed(client, make_task):
    a = make_task(title="Mon", scheduled_date=str(MONDAY))
    make_task(title="Tue", scheduled_date=str(MONDAY + timedelta(days=1)))
    client.patch(f"/api/tasks/{a['id']}", json={"status": "completed"})
    make_task(title="Unplanned", status="completed")
    week = client.get(f"/api/planner/week?start={TODAY}").json()
    assert week["week_start"] == str(MONDAY) and len(week["days"]) == 7
    assert week["planned_count"] == 2 and week["completed_count"] == 1
    assert week["completed_unplanned_count"] == 1
    # The note is normalised to Monday whichever day is supplied.
    client.put(
        "/api/planner/notes",
        json={"period": "week", "period_start": str(TODAY), "objectives": "Ship"},
    )
    assert client.get(f"/api/planner/week?start={MONDAY}").json()["note"]["objectives"] == "Ship"


def test_month_plan(client, make_task):
    make_task(title="This month", scheduled_date=str(TODAY), due_date=str(TODAY))
    m = client.get(f"/api/planner/month?month={TODAY}").json()
    assert m["planned_count"] == 1 and m["month_start"] == str(TODAY.replace(day=1))
    assert sum(w["planned"] for w in m["weeks"]) == 1


def test_plan_check_flags_gaps(client, project, make_task):
    pid = project["id"]
    client.patch(f"/api/projects/{pid}", json={"target_date": str(TODAY + timedelta(days=10))})
    client.post(f"/api/projects/{pid}/milestones", json={"title": "Empty"})
    a = make_task(title="A", due_date=str(TODAY + timedelta(days=5)))
    b = make_task(
        title="B",
        due_date=str(TODAY + timedelta(days=2)),
        acceptance_criteria="ok",
        estimate_hours=1,
    )
    make_task(title="Late", due_date=str(TODAY + timedelta(days=30)))
    client.post(f"/api/tasks/{b['id']}/dependencies", json={"depends_on_id": a["id"]})
    cats = {c["category"] for c in client.get(f"/api/projects/{pid}/plan-check").json()}
    assert {
        "acceptance_criteria",
        "deliverables",
        "missing_tasks",
        "deadlines",
        "dependencies",
        "estimates",
    } <= cats


def test_work_log_crud_and_task_project_inference(client, project, make_task):
    t = make_task()
    r = client.post(
        "/api/work-logs",
        json={"entry_date": str(TODAY), "summary": "Did things", "task_id": t["id"]},
    )
    assert r.status_code == 201
    log = r.json()
    assert log["project_id"] == project["id"] and log["task_title"] == "A task"
    r = client.patch(f"/api/work-logs/{log['id']}", json={"kind": "decision"})
    assert r.json()["kind"] == "decision"
    other = client.post("/api/projects", json={"name": "Other"}).json()
    r = client.patch(f"/api/work-logs/{log['id']}", json={"project_id": other["id"]})
    assert r.status_code == 400
    assert client.delete(f"/api/work-logs/{log['id']}").status_code == 204


def test_daily_report_reflects_real_data_only(client, make_task):
    done = make_task(title="Shipped login")
    client.patch(f"/api/tasks/{done['id']}", json={"status": "completed"})
    wip = make_task(title="Half done")
    client.patch(f"/api/tasks/{wip['id']}", json={"progress": 50})
    client.post(
        "/api/work-logs",
        json={"entry_date": str(TODAY), "kind": "decision", "summary": "Use PostgreSQL"},
    )
    r = client.post("/api/reports/generate", json={"kind": "daily", "date": str(TODAY)})
    assert r.status_code == 200
    md = r.json()["content"]
    assert "Shipped login" in md and "Use PostgreSQL" in md
    assert "progress 0% → 50%" in md
    assert "_None recorded._" in md  # e.g. research section is empty, not invented


def test_empty_weekly_report_invents_nothing(client):
    r = client.post("/api/reports/generate", json={"kind": "weekly", "date": str(TODAY)})
    md = r.json()["content"]
    assert md.count("_None recorded._") >= 5
    assert "Tasks planned this week: **0**" in md


def test_project_report_and_save_edit(client, project, make_task):
    make_task(title="T", status="completed")
    r = client.post("/api/reports/generate", json={"kind": "project", "date": str(TODAY)})
    assert r.status_code == 400
    draft = client.post(
        "/api/reports/generate",
        json={
            "kind": "project",
            "date": str(TODAY),
            "project_id": project["id"],
            "audience": "technical",
        },
    ).json()
    assert "Overall progress: **100%**" in draft["content"]
    saved = client.post("/api/reports", json=draft)
    assert saved.status_code == 201
    rid = saved.json()["id"]
    r = client.patch(f"/api/reports/{rid}", json={"content": "# Edited"})
    assert r.json()["content"] == "# Edited"
    assert len(client.get("/api/reports").json()) == 1


def test_dashboard(client, make_task):
    make_task(title="Due today", due_date=str(TODAY))
    make_task(title="Overdue", due_date=str(TODAY - timedelta(days=1)))
    make_task(title="Blocked", status="blocked")
    d = client.get("/api/dashboard").json()
    assert [t["title"] for t in d["due_today"]] == ["Due today"]
    assert [t["title"] for t in d["overdue"]] == ["Overdue"]
    assert [t["title"] for t in d["blocked"]] == ["Blocked"]
    assert len(d["projects"]) == 1 and len(d["recent_activity"]) == 3


def test_admin_system(client):
    info = client.get("/api/admin/system").json()
    assert info["database"]["engine"].startswith("PostgreSQL")
    assert "password" not in str(info).lower()
