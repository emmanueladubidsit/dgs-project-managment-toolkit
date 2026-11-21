"""Idempotent seed of the starter methodology library. Run: `uv run python -m app.seed`.

Existing methodologies (matched by slug) are never overwritten, so your edits are safe."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.methodologies import build_structure
from app.db import SessionLocal
from app.models import Methodology
from app.models.methodology import MethodologyStatus
from app.schemas.methodology import ActivityIn, DeliverableIn, StageIn
from app.seed_data import METHODOLOGIES


def seed_methodologies(db: Session) -> int:
    created = 0
    for spec in METHODOLOGIES:
        base = spec["name"].lower()
        slug = "-".join("".join(c if c.isalnum() else " " for c in base).split())
        if db.scalar(select(Methodology.id).where(Methodology.slug == slug)):
            continue
        m = Methodology(
            slug=slug,
            name=spec["name"],
            status=MethodologyStatus.PUBLISHED,
            **{
                k: spec.get(k)
                for k in (
                    "purpose",
                    "when_to_use",
                    "prerequisites",
                    "tools",
                    "common_risks",
                    "completion_criteria",
                )
            },
            limitations="Starter content: adapt it to your context before relying on it.",
        )
        stages = [
            StageIn(
                key=str(i),
                name=n,
                description=d or None,
                activities=[ActivityIn(title=a, expected_output=o) for a, o in acts],
            )
            for i, (n, d, acts) in enumerate(spec["stages"])
        ]
        deliverables = [
            DeliverableIn(name=n, classification=c, stage_key=None if s is None else str(s))
            for n, c, s in spec["deliverables"]
        ]
        db.add(m)
        build_structure(m, stages, deliverables)
        created += 1
    db.commit()
    return created


if __name__ == "__main__":
    with SessionLocal() as session:
        n = seed_methodologies(session)
        print(f"Seeded {n} methodolog{'y' if n == 1 else 'ies'} (existing ones left unchanged).")
