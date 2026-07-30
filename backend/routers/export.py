"""
Export API endpoints.

Generates downloadable files in ASCII, SAC, and MINISEED formats.
"""

import tempfile
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from backend.dependencies import get_session
from backend.session import SessionState
from backend.schemas import SacHeaderRequest
from backend.core import io as tio
from backend.core import vectorization as vec

router = APIRouter(tags=["export"])

# Data types with an evenly-sampled time axis; required for SAC/MiniSEED export.
_EVENLY_SAMPLED_TYPES = {"curvature_ga", "curvature_ls", "resampled", "response"}


def _uniform_delta(t: np.ndarray, data: str) -> float:
    """Compute the sample interval of an evenly-sampled time array."""
    if len(t) < 2:
        raise HTTPException(400, f"Not enough samples in '{data}' to determine a sampling interval")
    return float(np.median(np.diff(t)))


@router.get("/sessions/{sid}/export/ascii")
async def export_ascii(
    sid: str,
    data: str = Query("vectorized"),
    session: SessionState = Depends(get_session),
):
    """Download data as ASCII two-column file.
    data: vectorized | detrend | curvature_ga | curvature_ls | resampled | response
    """
    t, a = _resolve_data(session, data)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp_path = tmp.name

    tio.save_ascii(t, a, tmp_path)
    basename = session.imagefile_name or session.datafile_name or "tiitba"
    basename = Path(basename).stem
    filename = f"{basename}_{data}.txt"

    return FileResponse(
        tmp_path,
        media_type="text/plain",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sessions/{sid}/export/sac")
async def export_sac(
    sid: str,
    data: str = Query("resampled"),
    station: str = Query(""),
    channel: str = Query(""),
    network: str = Query(""),
    starttime: str | None = Query(None),
    session: SessionState = Depends(get_session),
):
    """Download data as SAC file."""
    if data not in _EVENLY_SAMPLED_TYPES:
        raise HTTPException(400, f"'{data}' is not evenly sampled; SAC requires one of {sorted(_EVENLY_SAMPLED_TYPES)}")

    t, a = _resolve_data(session, data)
    delta = _uniform_delta(t, data)
    try:
        header = tio.build_sac_header(
            station=station or "STA",
            channel=channel or "HHZ",
            delta=delta,
            network=network,
            starttime=starttime,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".sac") as tmp:
        tmp_path = tmp.name

    tio.save_sac(t, a, tmp_path, header)
    basename = session.datafile_name or session.imagefile_name or "tiitba"
    basename = Path(basename).stem
    filename = f"{basename}_{data}.sac"

    return FileResponse(
        tmp_path,
        media_type="application/octet-stream",
        filename=filename,
    )


@router.get("/sessions/{sid}/export/miniseed")
async def export_miniseed(
    sid: str,
    data: str = Query("resampled"),
    station: str = Query(""),
    channel: str = Query(""),
    network: str = Query(""),
    starttime: str | None = Query(None),
    session: SessionState = Depends(get_session),
):
    """Download data as MINISEED file."""
    if data not in _EVENLY_SAMPLED_TYPES:
        raise HTTPException(400, f"'{data}' is not evenly sampled; MiniSEED requires one of {sorted(_EVENLY_SAMPLED_TYPES)}")

    t, a = _resolve_data(session, data)
    delta = _uniform_delta(t, data)
    try:
        header = tio.build_sac_header(
            station=station or "STA",
            channel=channel or "HHZ",
            delta=delta,
            network=network,
            starttime=starttime,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    trace = tio.create_trace(a, header)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mseed") as tmp:
        tmp_path = tmp.name

    tio.save_miniseed({"trace_0": trace}, tmp_path)
    basename = session.datafile_name or session.imagefile_name or "tiitba"
    basename = Path(basename).stem
    filename = f"{basename}_{data}.mseed"

    return FileResponse(
        tmp_path,
        media_type="application/octet-stream",
        filename=filename,
    )


def _resolve_data(session: SessionState, data: str):
    """Resolve which time/amplitude arrays to export."""
    if data == "vectorized":
        if not session.points:
            raise HTTPException(400, "No vectorized points")
        img_shape = session.img.shape[:2] if session.img is not None else (0, 0)
        return vec.convert_points(
            session.points, session.scale_mode,
            ppi=session.ppi, vr=session.vr, amp0=session.amp0, image_height_mm=session.imheight_mm,
            x_values=session.x_values, y_values=session.y_values, img_shape=img_shape,
        )

    elif data == "detrend":
        if session.amp1 is None:
            raise HTTPException(400, "No detrended data available")
        return session.treg, session.amp1

    elif data == "curvature_ga":
        if session.amp_ga_res is None or session.t_ga_res is None:
            raise HTTPException(400, "No G&A94 curvature data available")
        return session.t_ga_res, session.amp_ga_res

    elif data == "curvature_ls":
        if session.amp1_res is None or session.tapr_res is None:
            raise HTTPException(400, "No least-squares curvature data available")
        return session.tapr_res, session.amp1_res

    elif data == "resampled":
        if session.amp_res is None or session.tres is None:
            raise HTTPException(400, "No resampled data available")
        return session.tres, session.amp_res

    elif data == "response":
        if session.amp_correct is None:
            raise HTTPException(400, "No instrument response data available")
        t = session.t_ga_res if session.t_ga_res is not None else session.tres
        return t, session.amp_correct

    else:
        raise HTTPException(400, f"Unknown data type: {data}")
