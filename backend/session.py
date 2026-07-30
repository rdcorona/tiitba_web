"""
Session state management for TIITBA web application with persistence.

Each user session holds the full processing pipeline state.
PersistentSessionManager maintains an index of the last 5 sessions on disk.
"""

import time
import uuid
import os
import json
import shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path

import numpy as np
import cv2


@dataclass
class SessionState:
    """Server-side state for one user session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    # Image processing
    img: np.ndarray | None = None
    img_pre_binarize: np.ndarray | None = None
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

    # Corrections - each pipeline stage has its own field so re-running one
    # correction never overwrites a different correction's output.
    data_source: str | None = None  # 'upload' | 'points' - which raw source is authoritative
    treg: np.ndarray | None = None
    amp: np.ndarray | None = None
    amp1: np.ndarray | None = None  # detrended
    amp_res: np.ndarray | None = None  # standalone resample output (amplitude)
    amp_ga_res: np.ndarray | None = None  # curvature G&A94 output (amplitude)
    amp1_res: np.ndarray | None = None  # curvature least-squares variant output (amplitude)
    t_ga_res: np.ndarray | None = None  # curvature G&A94 output (time)
    tapr_res: np.ndarray | None = None  # curvature least-squares variant output (time)
    tres: np.ndarray | None = None  # standalone resample output (time)
    sps: int | None = None
    amp_correct: np.ndarray | None = None
    datafile_name: str | None = None

    def touch(self):
        """Update last_accessed timestamp."""
        self.last_accessed = time.time()

    def to_dict(self):
        """Return a JSON-serializable dictionary (excluding large arrays)."""
        d = asdict(self)
        # Remove large binary/numpy data for the JSON index
        excluded = [
            'img', 'img_pre_binarize', 'display_jpeg',
            'treg', 'amp', 'amp1', 'amp_res', 'amp_ga_res', 'amp1_res',
            't_ga_res', 'tapr_res', 'tres', 'amp_correct',
            'x_values', 'y_values'
        ]
        for key in excluded:
            d[key] = None if self.__getattribute__(key) is None else "__STAGED__"
        return d


class SessionManager:
    """Session store with TTL-based expiry and persistence."""

    def __init__(self, ttl_seconds: int = 7200, storage_dir: str = "storage"):
        self._sessions: dict[str, SessionState] = {}
        self._ttl = ttl_seconds
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = self._storage_dir / "sessions.json"
        self._load_history()

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
        success = self._sessions.pop(session_id, None) is not None
        if success:
            # Also remove from persistent storage if it exists
            sess_dir = self._storage_dir / session_id
            if sess_dir.exists():
                shutil.rmtree(sess_dir)
            self._update_history_after_delete(session_id)
        return success

    def cleanup_expired(self) -> int:
        """Remove sessions older than TTL. Returns count of removed sessions."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.last_accessed > self._ttl
        ]
        for sid in expired:
            # We don't delete from disk here, just from memory
            # unless they are explicitly deleted.
            del self._sessions[sid]
        return len(expired)

    @property
    def count(self) -> int:
        return len(self._sessions)

    # --- Persistence Logic ---

    def persist(self, sid: str):
        """Save session state to disk."""
        session = self.get(sid)
        if not session:
            return

        sess_dir = self._storage_dir / sid
        sess_dir.mkdir(parents=True, exist_ok=True)

        # Save large arrays
        if session.img is not None:
            cv2.imwrite(str(sess_dir / "img.png"), session.img)
        if session.img_pre_binarize is not None:
            cv2.imwrite(str(sess_dir / "img_pre.png"), session.img_pre_binarize)

        numpy_arrays = {
            'treg': session.treg, 'amp': session.amp, 'amp1': session.amp1,
            'amp_res': session.amp_res, 'amp_ga_res': session.amp_ga_res, 'amp1_res': session.amp1_res,
            't_ga_res': session.t_ga_res, 'tapr_res': session.tapr_res,
            'tres': session.tres, 'amp_correct': session.amp_correct,
            'x_values': session.x_values, 'y_values': session.y_values
        }
        for name, arr in numpy_arrays.items():
            if arr is not None:
                np.save(str(sess_dir / f"{name}.npy"), arr)

        # Save metadata JSON
        with open(sess_dir / "state.json", "w") as f:
            json.dump(session.to_dict(), f)

        self._add_to_history(session)

    def restore(self, target_sid: str, source_sid: str) -> SessionState | None:
        """Restore a session from disk into a target session object."""
        sess_dir = self._storage_dir / source_sid
        if not sess_dir.exists():
            return None

        # Load metadata
        with open(sess_dir / "state.json", "r") as f:
            data = json.load(f)

        session = self.get(target_sid)
        if not session:
            session = self.create()
            session.id = target_sid

        # Restore simple fields
        for k, v in data.items():
            if v != "__STAGED__":
                setattr(session, k, v)

        # Restore images
        if (sess_dir / "img.png").exists():
            session.img = cv2.imread(str(sess_dir / "img.png"), 0)
        if (sess_dir / "img_pre.png").exists():
            session.img_pre_binarize = cv2.imread(str(sess_dir / "img_pre.png"), 0)

        # Restore numpy arrays
        for name in [
            'treg', 'amp', 'amp1', 'amp_res', 'amp_ga_res', 'amp1_res',
            't_ga_res', 'tapr_res', 'tres', 'amp_correct',
            'x_values', 'y_values'
        ]:
            if (sess_dir / f"{name}.npy").exists():
                setattr(session, name, np.load(str(sess_dir / f"{name}.npy")))

        return session

    def get_history(self) -> list[dict]:
        """Return the last 5 persistent sessions."""
        return self._history

    def _load_history(self):
        if self._history_file.exists():
            try:
                with open(self._history_file, "r") as f:
                    self._history = json.load(f)
            except:
                self._history = []
        else:
            self._history = []

    def _add_to_history(self, session: SessionState):
        # Check if already in history
        self._history = [s for s in self._history if s['session_id'] != session.id]
        
        entry = {
            "session_id": session.id,
            "timestamp": time.time(),
            "imagefile_name": session.imagefile_name,
            "datafile_name": session.datafile_name,
            "point_count": len(session.points),
            "has_image": session.img is not None
        }
        self._history.insert(0, entry)
        self._history = self._history[:5]  # keep last 5

        with open(self._history_file, "w") as f:
            json.dump(self._history, f)

    def _update_history_after_delete(self, sid: str):
        self._history = [s for s in self._history if s['session_id'] != sid]
        with open(self._history_file, "w") as f:
            json.dump(self._history, f)
