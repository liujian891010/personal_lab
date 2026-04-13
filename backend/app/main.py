from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import ensure_runtime_dirs, settings
from .db import db_manager
from .routers.health import router as health_router
from .routers.reports import router as reports_router
from .routers.search import router as search_router
from .routers.sync import router as sync_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_runtime_dirs(settings)
    db_manager.initialize()
    yield


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(sync_router)
app.include_router(reports_router)
app.include_router(search_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
    }
