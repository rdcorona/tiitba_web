"""
Export API endpoints.

Generates downloadable files in ASCII, SAC, and MINISEED formats.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from backend.dependencies import get_session
from backend.session import SessionState
from backend.schemas import SacHeaderRequest
from backend.core import io as tio
from backend.core import vectorization as vec

router = APIRouter(tags=["export"])


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
    t, a = _resolve_data(session, data)

    if session.sps is None:
        raise HTTPException(400, "Data must be resampled before SAC export (uniform sampling required)")

    delta = 1.0 / session.sps
    header = tio.build_sac_header(
        station=station or "STA",
        channel=channel or "HHZ",
        delta=delta,
        network=network,
        starttime=starttime,
    )

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
    t, a = _resolve_data(session, data)

    if session.sps is None:
        raise HTTPException(400, "Data must be resampled before MINISEED export")

    delta = 1.0 / session.sps
    header = tio.build_sac_header(
        station=station or "STA",
        channel=channel or "HHZ",
        delta=delta,
        network=network,
        starttime=starttime,
    )
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
        if session.scale_mode == "timemarks" and session.vr is not None:
            return vec.pixels_to_timemarks(
                session.points, session.ppi, session.vr,
                session.amp0, session.imheight_mm,
            )
        elif session.scale_mode == "corners" and session.x_values is not None:
            h, w = session.img.shape[:2]
            return vec.pixels_to_corners(
                session.points, session.x_values, session.y_values, w, h,
            )
        else:
            h = session.img.shape[0] if session.img is not None else 0
            return vec.pixels_to_raw(session.points, h)

    elif data == "detrend":
        if session.amp1 is None:
            raise HTTPException(400, "No detrended data available")
        return session.treg, session.amp1

    elif data == "curvature_ga":
        if session.amp_res is None or session.t_ga_res is None:
            raise HTTPException(400, "No G&A94 curvature data available")
        return session.t_ga_res, session.amp_res

    elif data == "curvature_ls":
        if session.amp1_res is None or session.tapr_res is None:
            raise HTTPException(400, "No least-squares curvature data available")
        return session.tapr_res, session.amp1_res

    elif data == "resampled":
        if session.amp_res is None:
            raise HTTPException(400, "No resampled data available")
        t = session.tres if session.tres is not None else session.t_ga_res
        return t, session.amp_res

    elif data == "response":
        if session.amp_correct is None:
            raise HTTPException(400, "No instrument response data available")
        t = session.tres if session.tres is not None else session.t_ga_res
        if t is None:
            t = session.treg
        return t, session.amp_correct

    else:
        raise HTTPException(400, f"Unknown data type: {data}")
