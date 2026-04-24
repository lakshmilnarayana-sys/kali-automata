"""KALI FastAPI application — serves the REST API for the web dashboard."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from kali.api.db import init_db
from kali.api.routes.experiments import router as experiments_router
from kali.api.routes.runs import router as runs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="KALI API",
    description="Chaos engineering — experiment runner and run history",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiments_router, prefix="/api")
app.include_router(runs_router, prefix="/api")

# Serve built UI as static files in production
_ui_dist = Path(__file__).parent.parent.parent.parent / "ui" / "dist"
if _ui_dist.exists():
    app.mount("/", StaticFiles(directory=str(_ui_dist), html=True), name="ui")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "kali-api"}
