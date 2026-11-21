import io
from datetime import date

from docx import Document
from pptx import Presentation

from app.services import exports

MD = (
    "# Title\n\n## Section A\n\n- **Bold** item\n  - nested\n- [x] done\n\n"
    "Para with _italic_ → arrow.\n\n---\n## Section B\n\n"
    + "\n".join(f"- item {i}" for i in range(10))
)


def test_parse_markdown_subset():
    kinds = [(b.kind, b.level, b.marker) for b in exports.parse(MD)][:6]
    assert kinds == [("h1", 0, ""), ("h2", 0, ""), ("bullet", 0, ""), ("bullet", 1, ""),
                     ("bullet", 0, "☑"), ("p", 0, "")]  # fmt: skip
    assert exports.runs("a **b** _c_ `d`") == [
        ("a ", False, False, False),
        ("b", True, False, False),
        (" ", False, False, False),
        ("c", False, True, False),
        (" ", False, False, False),
        ("d", False, False, True),
    ]


def test_render_all_formats():
    doc = Document(io.BytesIO(exports.to_docx("Title", MD)))
    texts = [p.text for p in doc.paragraphs]
    assert texts.count("Title") == 1  # the H1 matching the title is not repeated
    assert "Section A" in texts and any("Bold item" in t for t in texts)
    pdf = exports.to_pdf("Title", MD)
    assert pdf.startswith(b"%PDF")  # non-WinAnsi characters (→, ☑) did not break rendering
    prs = Presentation(io.BytesIO(exports.to_pptx("Title", MD)))
    titles = [s.shapes.title.text for s in prs.slides if s.shapes.title]
    # title, A, B (10 bullets → split over two slides), closing slide
    assert titles == ["Title", "Section A", "Section B", "Section B (continued 2/2)",
                      "Generated from workspace data"]  # fmt: skip


def test_export_endpoints(client, project, make_task):
    make_task(title="Ship it", status="completed")
    for kind in ("brief", "status", "report"):
        for fmt, mime in exports.MIME.items():
            r = client.get(f"/api/export/project/{project['id']}/{kind}?format={fmt}")
            assert r.status_code == 200, (kind, fmt)
            assert r.headers["content-type"] == mime
            assert f'.{fmt}"' in r.headers["content-disposition"]
    deck = Presentation(
        io.BytesIO(client.get(f"/api/export/project/{project['id']}/status").content)
    )
    texts = " ".join(
        sh.text_frame.text for s in deck.slides for sh in s.shapes if sh.has_text_frame
    )
    assert "100% complete" in texts and "Ship it" in texts
    r = client.post(
        "/api/export", json={"title": "Draft", "content": "## Hi\n\n- there", "format": "pdf"}
    )
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert (
        client.get("/api/export/project/00000000-0000-0000-0000-000000000000/brief").status_code
        == 404
    )


def test_saved_report_and_knowledge_export(client, project):
    draft = client.post(
        "/api/reports/generate", json={"kind": "weekly", "date": str(date.today())}
    ).json()
    rid = client.post("/api/reports", json=draft).json()["id"]
    r = client.get(f"/api/export/report/{rid}?format=docx")
    assert r.status_code == 200 and "weekly-report" in r.headers["content-disposition"]
    k = client.post("/api/knowledge", json={"category": "troubleshooting", "title": "Docker mounts",
                                            "fields": {"root_cause": "macOS privacy"},
                                            "verification": "ai_suggestion"}).json()  # fmt: skip
    doc = Document(io.BytesIO(client.get(f"/api/export/knowledge/{k['id']}?format=docx").content))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Root cause" in text and "not verified" in text
