import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    ai,
    claude,
    documents,
    exports,
    knowledge,
    methodologies,
    planning,
    projects,
    reports,
    system,
    tasks,
    tracker,
    voice,
)
from app.config import get_settings
from app.errors import register_error_handlers

settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


async def _auto_sync_loop() -> None:
    """Every SYNC_INTERVAL_SECONDS, sync connected folders that have auto-sync on (read only)."""
    import asyncio

    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import ProjectConnection
    from app.services.codebase import sync_connection

    def run_once() -> None:
        with SessionLocal() as db:
            for c in db.scalars(
                select(ProjectConnection).where(ProjectConnection.auto_sync)
            ).unique():
                try:
                    sync_connection(db, c)
                except Exception:  # noqa: BLE001 — one bad folder must not stop the others
                    logging.getLogger("app.sync").exception("Sync failed for %s", c.path)
                    db.rollback()

    while True:
        await asyncio.sleep(settings.sync_interval_seconds)
        await asyncio.to_thread(run_once)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import asyncio

    task = asyncio.create_task(_auto_sync_loop()) if settings.sync_interval_seconds > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version=settings.app_version,
    description="Local-first project, task and engineering knowledge workspace.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

for module in (
    projects,
    tasks,
    planning,
    reports,
    system,
    knowledge,
    methodologies,
    documents,
    voice,
    ai,
    exports,
    claude,
    tracker,
):
    app.include_router(module.router, prefix="/api")
