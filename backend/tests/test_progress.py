"""Progress calculation rules (unit tests on the service, plus one API check)."""

from decimal import Decimal
from types import SimpleNamespace

from app.models.enums import TaskStatus
from app.services.progress import weighted_progress


def t(status=TaskStatus.TODO, progress=0, weight=None, est=None):
    return SimpleNamespace(
        status=status,
        progress=progress,
        weight=weight,
        estimate_hours=Decimal(est) if est is not None else None,
    )


def test_no_tasks():
    p = weighted_progress([])
    assert p.percent == 0 and p.method == "none"


def test_equal_weights_average():
    p = weighted_progress([t(TaskStatus.COMPLETED), t(progress=50), t()])
    assert p.percent == 50.0 and p.method == "equal"
    assert p.tasks_completed == 1 and p.tasks_counted == 3


def test_estimates_weight_progress():
    # A completed 1h task should not count as much as an untouched 9h task.
    p = weighted_progress([t(TaskStatus.COMPLETED, est="1"), t(est="9")])
    assert p.percent == 10.0 and p.method == "weighted"


def test_explicit_weight_beats_estimate():
    p = weighted_progress([t(TaskStatus.COMPLETED, weight=3, est="100"), t(weight=1, est="1")])
    assert p.percent == 75.0


def test_cancelled_excluded():
    p = weighted_progress([t(TaskStatus.COMPLETED), t(TaskStatus.CANCELLED)])
    assert p.percent == 100.0 and p.tasks_excluded == 1
    assert "cancelled" in p.explanation


def test_project_progress_ignores_subtasks(client, make_task, project):
    parent = make_task(title="Parent", progress=20)
    make_task(title="Sub", parent_id=parent["id"], status="completed")
    make_task(title="Other", status="completed")
    p = client.get(f"/api/projects/{project['id']}").json()["progress"]
    assert p["tasks_counted"] == 2 and p["percent"] == 60.0
