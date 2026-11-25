"""Tracker parsing (pure): dates, weekend rule, milestone status, plans. See ADR 0010."""

from datetime import date
from pathlib import Path

from app.services import tracker

SAMPLE = """# Progress report and plan (written Wed 25 Nov 2026)

**Working days:** Monday to Friday only.

## 1. Week 1 (Mon 16 to Fri 20 Nov): review and prototype

| Day | What was done | Evidence |
|---|---|---|
| Mon 16, Tue 17 | No record | none |
| Wed 18 | Read-only index of the codebase (4 agents). Architecture map. ISSUE-0032 logged. | worklog 11-18 |
| Fri 20 | Prototype assistant grounded in 15 documents (1,408 sections. deterministic). | worklog 11-20 |
| Sat 21 | Bulk upload for the admin question template. | worklog 11-21 |

**Week 1 milestone (my reading of the plan: "baseline and scope"):**
- Implementation baseline established: **Verified** (index, architecture).
- Prototype as the spec: **In progress** (grounding built).
- MVP scope approved: **Not started** (not yet written).

## 2. Week 2 to date (Mon 23 to Wed 25 Nov)

| Day | What was done | Evidence |
|---|---|---|
| Mon 23 | **Carried from Sun 22:** demo guide written. Impact levels by category added. | wl |

## 3. Rest of Week 2 (Proposed)

| When | Tasks | Done when |
|---|---|---|
| **Thu 26** | 1. Gap review of every page. 2. Draft the auth ADR. | Gap table approved. |

**M2 success criteria (Fri 27):** scope approved; gap review approved

### Week 6 (21–25 Dec), M6: outputs and release candidate
| Day | Task |
|---|---|
| Mon 21 | Report exports (PDF, CSV). |
| Thu 24 | Fixes only. |
| Fri 25 | Holiday: no planned work. |

## 5. Features at a glance
| Feature | Prototype | Live app |
|---|---|---|
| Login | Simulated | Missing |
"""


def parsed():
    return tracker.parse_tracker(SAMPLE, date(2026, 11, 25))


def test_working_day_moves_weekends_to_monday():
    assert tracker.working_day(date(2026, 11, 21)) == date(2026, 11, 23)  # Saturday
    assert tracker.working_day(date(2026, 11, 22)) == date(2026, 11, 23)  # Sunday
    assert tracker.working_day(date(2026, 11, 20)) == date(2026, 11, 20)  # Friday


def test_done_work_by_working_day():
    t = parsed()
    done = [i for i in t.items if i.kind == "done"]
    by_day = {}
    for i in done:
        by_day.setdefault(i.item_date, []).append(i.title)
    assert date(2026, 11, 16) not in by_day and date(2026, 11, 17) not in by_day  # no record
    assert by_day[date(2026, 11, 18)] == [
        "Read-only index of the codebase (4 agents)",
        "Architecture map",
        "ISSUE-0032 logged",
    ]
    # A full stop inside brackets does not split an item.
    assert by_day[date(2026, 11, 20)] == [
        "Prototype assistant grounded in 15 documents (1,408 sections. deterministic)"
    ]
    # Saturday's row and the carried Sunday work both count on Monday 23.
    mon = by_day[date(2026, 11, 23)]
    assert "Bulk upload for the admin question template" in mon
    assert "Demo guide written" in mon and "Impact levels by category added" in mon
    sat = next(i for i in done if i.title.startswith("Bulk upload"))
    assert sat.original_date == date(2026, 11, 21)
    carried = next(i for i in done if i.title == "Demo guide written")
    assert carried.original_date == date(2026, 11, 22)
    assert all(i.status == "completed" for i in done)
    assert next(i for i in done if i.title == "ISSUE-0032 logged").task_ids == ["ISSUE-0032"]
    days = {d.item_date for d in t.days}
    assert date(2026, 11, 21) not in days and date(2026, 11, 23) in days


def test_milestone_status_bullets():
    t = parsed()
    week1 = next(m for m in t.milestones if m.title.startswith("Week 1"))
    assert week1.title == "Week 1 milestone: baseline and scope"
    assert week1.status == "in_progress"  # some verified, some not started
    assert week1.due_date == date(2026, 11, 20)  # last working day of its done work
    status = {i.title: i.status for i in t.items if i.kind == "status"}
    assert status == {
        "Implementation baseline established": "completed",
        "Prototype as the spec": "in_progress",
        "MVP scope approved": "todo",
    }


def test_plans_become_todo_tasks_under_their_milestone():
    t = parsed()
    ms = {m.code: m for m in t.milestones if m.code}
    assert ms["M2"].due_date == date(2026, 11, 27)
    assert "gap review approved" in ms["M2"].description
    assert ms["M6"].title == "M6: outputs and release candidate"
    plan = [i for i in t.items if i.kind == "plan"]
    titles = {i.title: i for i in plan}
    assert titles["Gap review of every page"].milestone_key == ms["M2"].key
    assert titles["Draft the auth ADR"].acceptance_criteria == "Gap table approved"
    assert titles["Gap review of every page"].item_date == date(2026, 11, 26)
    assert titles["Report exports (PDF, CSV)"].item_date == date(2026, 12, 21)
    assert titles["Fixes only"].milestone_key == ms["M6"].key
    assert ms["M6"].due_date == date(2026, 12, 24)
    assert not any("Holiday" in i.title for i in plan)
    assert all(i.status == "todo" for i in plan)
    assert not t.warnings  # the feature table is ignored silently


def test_keys_are_stable_and_unique():
    a, b = parsed(), parsed()
    assert [i.key for i in a.items] == [i.key for i in b.items]
    assert len({i.key for i in a.items}) == len(a.items)


def test_unrecognised_file_warns():
    t = tracker.parse_tracker("# Notes\n\nJust prose.", date(2026, 11, 25))
    assert t.warnings and not t.items


def test_dates_across_a_year_end():
    text = "### Week 7 (28 Dec to 8 Jan), M7: hardening\n| Day | Task |\n|---|---|\n| Mon 4 | Monitoring. |\n"
    t = tracker.parse_tracker(text, date(2026, 12, 20))
    assert t.items[0].item_date == date(2027, 1, 4)


def test_find_tracker_picks_newest(tmp_path: Path):
    d = tmp_path / "docs" / "project-management"
    d.mkdir(parents=True)
    (d / "PROGRESS-AND-PLAN-2026-11-18.md").write_text("old")
    (d / "PROGRESS-AND-PLAN-2026-11-25.md").write_text("new")
    (d / "NOTES.md").write_text("ignored")
    assert tracker.find_tracker(str(tmp_path)) == (
        "docs/project-management/PROGRESS-AND-PLAN-2026-11-25.md",
        date(2026, 11, 25),
    )
