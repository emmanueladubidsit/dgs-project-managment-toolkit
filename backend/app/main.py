import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import planning, projects, reports, system, tasks
from app.config import get_settings
from app.errors import register_error_handlers

settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
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

for module in (projects, tasks, planning, reports, system):
    app.include_router(module.router, prefix="/api")
