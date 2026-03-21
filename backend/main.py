"""
TIITBA Web Application - FastAPI entry point.

Serves the backend API and the built frontend static files.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.dependencies import init_session_manager, get_session_manager
from backend.routers import images, vectorization, corrections, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle: init sessions, start cleanup task."""
    manager = init_session_manager(settings.session_ttl_seconds)

    async def cleanup_loop():
        while True:
            await asyncio.sleep(300)  # every 5 minutes
            removed = manager.cleanup_expired()
            if removed > 0:
                print(f"Cleaned up {removed} expired session(s)")

    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()


app = FastAPI(
    title="TIITBA Web",
    description="Historical Seismograms Vectorization, Analysis, and Correction",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Display-Scale"],
)

# API routers
app.include_router(images.router, prefix="/api")
app.include_router(vectorization.router, prefix="/api")
app.include_router(corrections.router, prefix="/api")
app.include_router(export.router, prefix="/api")


# --- Session endpoints (kept here for simplicity) ---

from fastapi import Depends
from backend.dependencies import get_session_manager, get_session
from backend.session import SessionManager, SessionState
from backend.schemas import SessionCreated, SessionSummary


@app.post("/api/sessions", response_model=SessionCreated)
async def create_session():
    manager = get_session_manager()
    session = manager.create()
    return SessionCreated(session_id=session.id)


@app.get("/api/sessions/{sid}", response_model=SessionSummary)
async def get_session_info(session: SessionState = Depends(get_session)):
    return SessionSummary(
        session_id=session.id,
        has_image=session.img is not None,
        has_points=len(session.points) > 0,
        has_data=session.amp is not None,
        has_scale=session.scale_mode is not None,
        scale_mode=session.scale_mode,
        imagefile_name=session.imagefile_name,
        datafile_name=session.datafile_name,
        point_count=len(session.points),
    )


@app.delete("/api/sessions/{sid}")
async def delete_session(sid: str):
    manager = get_session_manager()
    deleted = manager.delete(sid)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found")
    return {"deleted": True}


# Serve frontend static files (production)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
