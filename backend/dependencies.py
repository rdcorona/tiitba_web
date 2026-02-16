"""
FastAPI dependency injection functions.
"""

from fastapi import HTTPException

from backend.session import SessionManager, SessionState

# Singleton session manager (initialized in main.py lifespan)
_manager: SessionManager | None = None


def init_session_manager(ttl: int) -> SessionManager:
    global _manager
    _manager = SessionManager(ttl_seconds=ttl)
    return _manager


def get_session_manager() -> SessionManager:
    if _manager is None:
        raise RuntimeError("SessionManager not initialized")
    return _manager


def get_session(sid: str) -> SessionState:
    """Dependency that resolves a session by ID or raises 404."""
    manager = get_session_manager()
    session = manager.get(sid)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
