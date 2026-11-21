from datetime import date


def make(client, **fields):
    body = {"category": "research", "title": "Combining design systems", **fields}
    r = client.post("/api/knowledge", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_templates_cover_every_category(client):
    t = {x["category"]: x for x in client.get("/api/knowledge/templates").json()}
    assert len(t) == 14
    assert "research_question" in [f["key"] for f in t["research"]["fields"]]
    assert "root_cause" in [f["key"] for f in t["troubleshooting"]["fields"]]
    assert t["template"]["fields"] == []  # free-form categories use the content body


def test_create_research_with_structured_fields_and_origin(client, project):
    item = make(
        client,
        fields={
            "research_question": "How do we merge tokens?",
            "findings": " Use one scale ",
            "conclusions": "",
        },
        origin_project_id=project["id"],
        tags=["design", "design", " tokens "],
    )
    assert item["fields"] == {
        "research_question": "How do we merge tokens?",
        "findings": "Use one scale",
    }
    assert item["tags"] == ["design", "tokens"]
    assert item["verification"] == "research_unimplemented"  # never assumed verified
    assert item["projects"][0]["role"] == "origin"


def test_unknown_fields_rejected(client):
    r = client.post(
        "/api/knowledge",
        json={"category": "decision", "title": "x", "fields": {"findings": "wrong template"}},
    )
    assert r.status_code == 400 and "Unknown field" in r.json()["error"]["message"]


def test_versioning_and_restore(client):
    item = make(client, summary="First")
    r = client.patch(
        f"/api/knowledge/{item['id']}", json={"summary": "Second", "change_note": "Clarified"}
    )
    assert r.json()["version"] == 2
    # A no-op edit does not create a version
    assert (
        client.patch(f"/api/knowledge/{item['id']}", json={"summary": "Second"}).json()["version"]
        == 2
    )
    versions = client.get(f"/api/knowledge/{item['id']}/versions").json()
    assert [v["version"] for v in versions] == [1]
    assert (
        versions[0]["snapshot"]["summary"] == "First" and versions[0]["change_note"] == "Clarified"
    )
    restored = client.post(f"/api/knowledge/{item['id']}/restore-version/1").json()
    assert restored["summary"] == "First" and restored["version"] == 3


def test_reuse_links_and_origin_rules(client, project):
    other = client.post("/api/projects", json={"name": "Other"}).json()
    item = make(client, origin_project_id=project["id"])
    r = client.post(
        f"/api/knowledge/{item['id']}/projects", json={"project_id": other["id"], "role": "reused"}
    )
    assert r.status_code == 201
    assert {p["role"] for p in r.json()["projects"]} == {"origin", "reused"}
    # A second origin is refused; the origin role cannot be changed
    assert (
        client.post(
            f"/api/knowledge/{item['id']}/projects",
            json={"project_id": project["id"], "role": "related"},
        ).status_code
        == 409
    )
    # Filtering by project finds it for both
    assert len(client.get(f"/api/knowledge?project_id={other['id']}").json()) == 1


def test_relations_and_supersede_marks_outdated(client):
    research = make(client, title="Benchmark")
    decision = make(
        client, category="decision", title="Use Postgres", fields={"decision": "Postgres"}
    )
    old = make(client, category="decision", title="Use MySQL", verification="verified_tested")
    r = client.post(
        f"/api/knowledge/{research['id']}/relations",
        json={"to_id": decision["id"], "kind": "evidence_for"},
    )
    assert r.json()["relations"][0]["direction"] == "outgoing"
    incoming = client.get(f"/api/knowledge/{decision['id']}").json()["relations"]
    assert incoming[0]["direction"] == "incoming" and incoming[0]["other_title"] == "Benchmark"
    client.post(
        f"/api/knowledge/{decision['id']}/relations",
        json={"to_id": old["id"], "kind": "supersedes"},
    )
    assert client.get(f"/api/knowledge/{old['id']}").json()["verification"] == "outdated"
    assert (
        client.post(
            f"/api/knowledge/{decision['id']}/relations", json={"to_id": decision["id"]}
        ).status_code
        == 400
    )


def test_promote_work_log_keeps_provenance(client, project, make_task):
    t = make_task()
    log = client.post(
        "/api/work-logs",
        json={
            "entry_date": str(date.today()),
            "kind": "decision",
            "summary": "Adopt Tailwind tokens\nBecause…",
            "task_id": t["id"],
        },
    ).json()
    r = client.post(f"/api/knowledge/from-work-log/{log['id']}")
    assert r.status_code == 201
    k = r.json()
    assert k["category"] == "decision" and k["title"] == "Adopt Tailwind tokens"
    assert k["fields"]["decision"].startswith("Adopt Tailwind tokens")
    assert k["projects"][0]["project_id"] == project["id"] and k["tasks"][0]["task_id"] == t["id"]
    assert client.post(f"/api/knowledge/from-work-log/{log['id']}").status_code == 409


def test_filters_search_archive_and_delete(client, project, make_task):
    a = make(
        client,
        title="Docker on macOS",
        category="troubleshooting",
        fields={"root_cause": "Desktop folder bind mounts blocked"},
    )
    make(client, title="Something else", verification="verified_docs")
    assert [k["title"] for k in client.get("/api/knowledge?q=bind mounts").json()] == [
        "Docker on macOS"
    ]
    assert len(client.get("/api/knowledge?verification=verified_docs").json()) == 1
    make_task(title="Fix Docker mounts")
    hits = client.get("/api/search?q=docker").json()
    assert {h["type"] for h in hits} >= {"knowledge", "task"}
    client.post(f"/api/knowledge/{a['id']}/archive")
    assert all(k["id"] != a["id"] for k in client.get("/api/knowledge").json())
    assert client.delete(f"/api/knowledge/{a['id']}").status_code == 400
    assert client.delete(f"/api/knowledge/{a['id']}?confirm=true").status_code == 204
    assert client.get("/api/search?q=d").status_code == 422  # too short to search
