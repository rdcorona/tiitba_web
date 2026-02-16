"""
Vectorization API endpoints.

Handles scale definition (timemarks/corners), point management,
and coordinate conversion for seismogram digitization.
"""

import numpy as np
from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_session
from backend.session import SessionState
from backend.schemas import (
    PointAdd, PointResponse, PointRemoved,
    TimemarkRequest, TimemarkResult,
    CornerRequest, PlotData,
)
from backend.core import vectorization as vec
from backend.core import image_processing as imgproc

router = APIRouter(tags=["vectorization"])


@router.post("/sessions/{sid}/scale/timemarks", response_model=TimemarkResult)
async def set_timemarks(
    sid: str,
    body: TimemarkRequest,
    session: SessionState = Depends(get_session),
):
    """Define scale using time-mark picking. Computes drum speed."""
    if len(body.points) < 3:
        raise HTTPException(400, "At least 3 time-mark points required")

    drum_speed, amp0, mean_dist = vec.compute_drum_speed(body.points, body.ppi)

    session.vr = drum_speed
    session.amp0 = amp0
    session.ppi = body.ppi
    session.scale_mode = "timemarks"

    if session.img is not None:
        dims = imgproc.get_dimensions(session.img, body.ppi)
        session.imheight_mm = dims['height_mm']

    return TimemarkResult(
        drum_speed=drum_speed,
        amp0=amp0,
        mean_distance_px=mean_dist,
    )


@router.post("/sessions/{sid}/scale/corners")
async def set_corners(
    sid: str,
    body: CornerRequest,
    session: SessionState = Depends(get_session),
):
    """Define scale using opposite corner coordinate values."""
    session.x_values = np.array([body.left_x, body.right_x])
    session.y_values = np.array([body.up_y, body.down_y])
    session.scale_mode = "corners"
    return {"success": True}


@router.post("/sessions/{sid}/points", response_model=PointResponse)
async def add_point(
    sid: str,
    body: PointAdd,
    session: SessionState = Depends(get_session),
):
    """Add a digitized point. Returns converted physical coordinates."""
    session.points.append((body.x, body.y))
    idx = len(session.points) - 1

    # Convert to physical coordinates
    time_or_x, amp_or_y = _convert_point(session, body.x, body.y)

    return PointResponse(
        index=idx,
        time_or_x=time_or_x,
        amplitude_or_y=amp_or_y,
    )


@router.delete("/sessions/{sid}/points/last", response_model=PointRemoved)
async def remove_last_point(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Undo the last digitized point."""
    if not session.points:
        raise HTTPException(400, "No points to remove")

    removed = session.points.pop()
    return PointRemoved(
        removed=list(removed),
        remaining=len(session.points),
    )


@router.delete("/sessions/{sid}/points")
async def clear_points(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Clear all digitized points."""
    session.points.clear()
    return {"cleared": True}


@router.get("/sessions/{sid}/points")
async def get_points(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Get all digitized points."""
    return {"points": session.points, "count": len(session.points)}


@router.get("/sessions/{sid}/plot-data", response_model=PlotData)
async def get_plot_data(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Get converted coordinate arrays for plotting."""
    if not session.points:
        raise HTTPException(400, "No points to plot")

    if session.scale_mode == "timemarks" and session.vr is not None:
        t, a = vec.pixels_to_timemarks(
            session.points, session.ppi, session.vr,
            session.amp0, session.imheight_mm,
        )
        return PlotData(
            time=t.tolist(), amplitude=a.tolist(),
            xlabel="Time [s]", ylabel="Amplitude [mm]",
        )
    elif session.scale_mode == "corners" and session.x_values is not None:
        h, w = session.img.shape[:2]
        x, y = vec.pixels_to_corners(
            session.points, session.x_values, session.y_values, w, h,
        )
        return PlotData(
            time=x.tolist(), amplitude=y.tolist(),
            xlabel="X", ylabel="Y",
        )
    else:
        # Raw pixels
        h = session.img.shape[0] if session.img is not None else 0
        x, y = vec.pixels_to_raw(session.points, h)
        return PlotData(
            time=x.tolist(), amplitude=y.tolist(),
            xlabel="X [pixels]", ylabel="Y [pixels]",
        )


def _convert_point(session: SessionState, x: int, y: int) -> tuple[float, float]:
    """Convert a single pixel point to physical coordinates."""
    if session.scale_mode == "timemarks" and session.vr is not None:
        t, a = vec.pixels_to_timemarks(
            [(x, y)], session.ppi, session.vr,
            session.amp0, session.imheight_mm,
        )
        return float(t[0]), float(a[0])
    elif session.scale_mode == "corners" and session.x_values is not None:
        h, w = session.img.shape[:2] if session.img is not None else (0, 0)
        xv, yv = vec.pixels_to_corners(
            [(x, y)], session.x_values, session.y_values, w, h,
        )
        return float(xv[0]), float(yv[0])
    else:
        h = session.img.shape[0] if session.img is not None else 0
        return float(x), float((y * -1) + h)
