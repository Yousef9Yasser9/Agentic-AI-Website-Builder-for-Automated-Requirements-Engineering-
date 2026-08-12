from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.auth.database import init_db
from backend.app.routes import (
    admin_routes,
    auth_routes,
    build_routes,
    generation_routes,
    projects_routes,
    settings_routes,
    system_routes,
    workflow_routes,
)
from backend.app.services.builder_service import ROOT_DIR, STAGES

init_db()

app = FastAPI(
    title="AI Website Builder API",
    description="FastAPI wrapper around the existing local AI website generation pipeline.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(projects_routes.router)
app.include_router(workflow_routes.router)
app.include_router(generation_routes.router)
app.include_router(build_routes.router)
app.include_router(settings_routes.router)
app.include_router(system_routes.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "stages": STAGES}


frontend_dist = ROOT_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=Path(frontend_dist), html=True), name="frontend")
