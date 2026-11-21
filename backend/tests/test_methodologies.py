from app.db import SessionLocal
from app.seed import seed_methodologies

STRUCTURE = {
    "stages": [
        {"key": "a", "name": "Discover", "activities": [
            {"title": "Interview users", "expected_output": "Interview notes"},
            {"title": "Map the domain"}]},
        {"key": "b", "name": "Build", "activities": [{"title": "Build MVP"}]},
    ],
    "deliverables": [
        {"name": "Research report", "classification": "mandatory", "stage_key": "a"},
        {"name": "Release notes", "classification": "optional", "stage_key": "b"},
        {"name": "Project brief", "classification": "recommended"},
    ],
}  # fmt: skip


def make(client, **extra):
    r = client.post(
        "/api/methodologies",
        json={"name": "Starter kit", "purpose": "Testing", **STRUCTURE, **extra},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_structure_and_counts(client):
    m = make(client)
    assert m["slug"] == "starter-kit" and m["status"] == "draft" and m["version"] == 1
    assert [s["name"] for s in m["stages"]] == ["Discover", "Build"]
    assert m["stage_count"] == 2 and m["activity_count"] == 3 and m["deliverable_count"] == 3
    by_name = {d["name"]: d for d in m["deliverables"]}
    assert by_name["Research report"]["stage_id"] == m["stages"][0]["id"]
    assert by_name["Project brief"]["stage_id"] is None
    assert make(client)["slug"] == "starter-kit-2"  # unique slugs


def test_unknown_stage_key_rejected(client):
    r = client.post(
        "/api/methodologies",
        json={
            "name": "x",
            "stages": [{"name": "A"}],
            "deliverables": [{"name": "D", "stage_key": "zzz"}],
        },
    )
    assert r.status_code == 400


def test_publish_versioning_and_structure_replace(client):
    empty = client.post("/api/methodologies", json={"name": "Empty"}).json()
    assert client.post(f"/api/methodologies/{empty['id']}/publish", json={}).status_code == 400
    m = make(client)
    p = client.post(
        f"/api/methodologies/{m['id']}/publish", json={"change_note": "First release"}
    ).json()
    assert p["status"] == "published" and p["version"] == 2
    r = client.put(
        f"/api/methodologies/{m['id']}/structure",
        json={"stages": [{"name": "Only stage"}], "change_note": "Simplified"},
    )
    assert r.json()["version"] == 3 and len(r.json()["stages"]) == 1
    versions = client.get(f"/api/methodologies/{m['id']}/versions").json()
    assert [v["version"] for v in versions] == [2, 1]
    assert len(versions[0]["snapshot"]["stages"]) == 2  # the previous structure is preserved


def test_adopt_whole_methodology(client, project):
    m = make(client)
    r = client.post(
        f"/api/projects/{project['id']}/methodologies",
        json={"methodology_id": m["id"], "start_date": "2026-12-01"},
    )
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["milestones_created"] == 2 and a["tasks_created"] == 3
    assert {d["name"]: d["classification"] for d in a["deliverables"]} == {
        "Research report": "mandatory",
        "Release notes": "optional",
        "Project brief": "recommended",
    }
    ms = client.get(f"/api/milestones?project_id={project['id']}").json()
    assert [(x["title"], x["due_date"]) for x in ms] == [
        ("Discover", "2026-12-08"),
        ("Build", "2026-12-15"),
    ]
    tasks = client.get(f"/api/tasks?project_id={project['id']}").json()
    interview = next(t for t in tasks if t["title"] == "Interview users")
    assert (
        interview["acceptance_criteria"] == "Interview notes"
        and interview["milestone_title"] == "Discover"
    )
    detail = client.get(f"/api/methodologies/{m['id']}").json()
    assert (
        detail["adoption_count"] == 1 and detail["adoptions"][0]["project_name"] == "Test project"
    )
    # Adopting the same stages again is refused (no duplicate plan)
    assert (
        client.post(
            f"/api/projects/{project['id']}/methodologies", json={"methodology_id": m["id"]}
        ).status_code
        == 409
    )


def test_adopt_selected_stages_without_duplicate_tasks(client, project, make_task):
    m = make(client)
    make_task(title="build mvp")  # already exists (case-insensitive)
    build = m["stages"][1]["id"]
    a = client.post(
        f"/api/projects/{project['id']}/methodologies",
        json={"methodology_id": m["id"], "stage_ids": [build], "create_milestones": False},
    ).json()
    assert a["tasks_created"] == 0 and a["milestones_created"] == 0
    assert {d["name"] for d in a["deliverables"]} == {"Release notes", "Project brief"}
    # The other stage can still be adopted later
    discover = m["stages"][0]["id"]
    r = client.post(
        f"/api/projects/{project['id']}/methodologies",
        json={"methodology_id": m["id"], "stage_ids": [discover]},
    )
    assert r.status_code == 201 and r.json()["tasks_created"] == 2


def test_project_deliverable_tracking(client, project):
    m = make(client)
    a = client.post(
        f"/api/projects/{project['id']}/methodologies", json={"methodology_id": m["id"]}
    ).json()
    d = a["deliverables"][0]
    r = client.patch(
        f"/api/project-deliverables/{d['id']}",
        json={"status": "done", "classification": "not_applicable"},
    )
    assert r.json()["status"] == "done" and r.json()["classification"] == "not_applicable"
    assert (
        client.get(f"/api/projects/{project['id']}/methodologies").json()[0]["deliverables"][0][
            "status"
        ]
        == "done"
    )
    # Removing the adoption keeps the created tasks
    assert client.delete(f"/api/project-methodologies/{a['id']}").status_code == 204
    assert len(client.get(f"/api/tasks?project_id={project['id']}").json()) == 3


def test_duplicate_and_from_project(client, project, make_task):
    m = make(client)
    copy = client.post(
        f"/api/methodologies/{m['id']}/duplicate", json={"name": "Adapted kit"}
    ).json()
    assert (
        copy["status"] == "draft"
        and copy["stage_count"] == 2
        and "Adapted from" in copy["limitations"]
    )
    ms = client.post(
        f"/api/projects/{project['id']}/milestones",
        json={"title": "Alpha", "deliverables": "Login"},
    ).json()
    make_task(title="Build login", milestone_id=ms["id"], acceptance_criteria="Users can sign in")
    make_task(title="Write README")
    r = client.post(
        f"/api/methodologies/from-project/{project['id']}", json={"name": "Login playbook"}
    )
    assert r.status_code == 201
    pb = r.json()
    assert pb["kind"] == "playbook" and pb["origin_project_name"] == "Test project"
    assert [s["name"] for s in pb["stages"]] == ["Alpha", "Other activities"]
    assert pb["stages"][0]["activities"][0]["expected_output"] == "Users can sign in"
    assert "confidential" in pb["limitations"]


def test_delete_rules(client, project):
    m = make(client)
    client.post(f"/api/projects/{project['id']}/methodologies", json={"methodology_id": m["id"]})
    assert client.delete(f"/api/methodologies/{m['id']}?confirm=true").status_code == 409
    other = make(client)
    assert client.delete(f"/api/methodologies/{other['id']}").status_code == 400
    assert client.delete(f"/api/methodologies/{other['id']}?confirm=true").status_code == 204


def test_seed_is_idempotent_and_complete(client):
    with SessionLocal() as db:
        assert seed_methodologies(db) == 13
        assert seed_methodologies(db) == 0
    items = client.get("/api/methodologies").json()
    assessment = next(m for m in items if m["slug"] == "assessing-an-existing-codebase")
    assert assessment["status"] == "published" and assessment["activity_count"] >= 20
