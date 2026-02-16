"""
Session state management for TIITBA web application.

Each user session holds the full processing pipeline state:
image data, vectorization points, correction results, etc.
"""

import time
import uuid
from dataclasses import dataclass, field

import numpy as np


@dataclass
class SessionState:
    """Server-side state for one user session, mirrors CentralWidget attributes."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    # Image processing
    img: np.ndarray | None = None
    display_jpeg: bytes | None = None
    display_scale: float = 1.0
    ppi: float | None = None
    imagefile_name: str | None = None

    # Vectorization
    points: list[tuple[int, int]] = field(default_factory=list)
    scale_mode: str | None = None  # 'timemarks' | 'corners'
    vr: float | None = None  # drum speed mm/s
    amp0: float | None = None
    x_values: np.ndarray | None = None
    y_values: np.ndarray | None = None
    imheight_mm: float | None = None

    # Corrections
    treg: np.ndarray | None = None
    amp: np.ndarray | None = None
    amp1: np.ndarray | None = None  # detrended
    amp_res: np.ndarray | None = None
    amp1_res: np.ndarray | None = None
    t_ga_res: np.ndarray | None = None
    tapr_res: np.ndarray | None = None
    tres: np.ndarray | None = None
    sps: int | None = None
    amp_correct: np.ndarray | None = None
    datafile_name: str | None = None

    def touch(self):
        """Update last_accessed timestamp."""
        self.last_accessed = time.time()


class SessionManager:
    """In-memory session store with TTL-based expiry."""

    def __init__(self, ttl_seconds: int = 7200):
        self._sessions: dict[str, SessionState] = {}
        self._ttl = ttl_seconds

    def create(self) -> SessionState:
        session = SessionState()
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> SessionState | None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.touch()
        return session

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def cleanup_expired(self) -> int:
        """Remove sessions older than TTL. Returns count of removed sessions."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.last_accessed > self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    @property
    def count(self) -> int:
        return len(self._sessions)
