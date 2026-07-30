"""
Corrections API endpoints.

Handles loading time-series data and applying signal processing corrections:
detrend, curvature, resample, Wiechert response, polarity inversion, taper.
"""

import tempfile
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from backend.dependencies import get_session
from backend.session import SessionState
from backend.schemas import (
    DataUploaded, CurvatureRequest, ResampleRequest,
    WiechertRequest, TaperRequest, CorrectionResult, PlotTraces,
)
from backend.core import corrections as cf
from backend.core import io as tio
from backend.core import vectorization as vec

router = APIRouter(tags=["corrections"])


def _reset_response(session: SessionState):
    """Invalidate the Wiechert response output - it's the last pipeline stage."""
    session.amp_correct = None


def _reset_from_detrend(session: SessionState):
    """Invalidate everything downstream of detrend: both curvature variants,
    the standalone resample, and the response (all stale once detrend changes)."""
    session.t_ga_res = None
    session.amp_ga_res = None
    session.tapr_res = None
    session.amp1_res = None
    session.tres = None
    session.amp_res = None
    session.sps = None
    _reset_response(session)


def _reset_from_raw(session: SessionState):
    """Invalidate every derived stage because the raw (treg, amp) changed."""
    session.amp1 = None
    _reset_from_detrend(session)


@router.post("/sessions/{sid}/data/upload", response_model=DataUploaded)
async def upload_data(
    sid: str,
    file: UploadFile = File(...),
    session: SessionState = Depends(get_session),
):
    """Upload a two-column ASCII time-series file."""
    contents = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="wb") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        treg, amp = tio.load_ascii(tmp_path)
        session.treg = treg
        session.amp = amp
        session.datafile_name = file.filename
        session.data_source = "upload"

        _reset_from_raw(session)

        return DataUploaded(
            n_samples=len(amp),
            time_range=[float(treg.min()), float(treg.max())],
            filename=file.filename or "unknown",
        )
    except (IndexError, ValueError) as e:
        raise HTTPException(400, f"Failed to parse data file: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/sessions/{sid}/data/auto-load", response_model=DataUploaded | None)
async def auto_load_data(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """
    Check if data is already in session (ASCII upload or vectorized points)
    and return its info. An uploaded ASCII file is authoritative and is
    never replaced; otherwise this bridges the current digitized points
    into a time series on every call, so it always reflects the latest
    state of the Vectorization module.
    """
    if session.data_source == "upload" and session.amp is not None and session.treg is not None:
        return DataUploaded(
            n_samples=len(session.amp),
            time_range=[float(session.treg.min()), float(session.treg.max())],
            filename=session.datafile_name or "in-memory",
        )

    if session.points and len(session.points) >= 2:
        has_scale = (
            (session.scale_mode == "timemarks" and session.vr is not None)
            or (session.scale_mode == "corners" and session.x_values is not None)
        )
        if not has_scale:
            return None

        img_shape = session.img.shape[:2] if session.img is not None else (0, 0)
        t, a = vec.convert_points(
            session.points, session.scale_mode,
            ppi=session.ppi, vr=session.vr, amp0=session.amp0, image_height_mm=session.imheight_mm,
            x_values=session.x_values, y_values=session.y_values, img_shape=img_shape,
        )

        changed = (
            session.treg is None or session.amp is None
            or session.treg.shape != t.shape or session.amp.shape != a.shape
            or not np.array_equal(session.treg, t) or not np.array_equal(session.amp, a)
        )
        if changed:
            session.treg = t
            session.amp = a
            session.data_source = "points"
            session.datafile_name = session.imagefile_name or "vectorized points"
            _reset_from_raw(session)

        return DataUploaded(
            n_samples=len(a),
            time_range=[float(t.min()), float(t.max())],
            filename=session.datafile_name,
        )

    if session.amp is not None and session.treg is not None:
        return DataUploaded(
            n_samples=len(session.amp),
            time_range=[float(session.treg.min()), float(session.treg.max())],
            filename=session.datafile_name or "in-memory",
        )

    return None


@router.get("/sessions/{sid}/data/plot", response_model=PlotTraces)
async def get_data_plot(
    sid: str,
    series: str = "raw",
    session: SessionState = Depends(get_session),
):
    """Get time-series data for plotting. series: comma-separated list of raw,detrend,curvature_ga,curvature_ls,resampled,response."""
    if session.amp is None:
        raise HTTPException(400, "No data loaded")

    requested = [s.strip() for s in series.split(",")]
    traces = []

    for name in requested:
        t, a = _get_series(session, name)
        if t is not None:
            traces.append({
                "name": name,
                "x": t.tolist(),
                "y": a.tolist(),
            })

    return PlotTraces(traces=traces)


@router.post("/sessions/{sid}/corrections/polarity", response_model=CorrectionResult)
async def invert_polarity(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Invert signal polarity."""
    if session.amp is None:
        raise HTTPException(400, "No data loaded")

    session.amp = cf.change_polarity(session.amp)
    _reset_from_raw(session)
    return CorrectionResult(message="Polarity inverted")


@router.post("/sessions/{sid}/corrections/detrend", response_model=CorrectionResult)
async def detrend(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Apply detrending (single linear fit over the whole series)."""
    if session.amp is None or session.treg is None:
        raise HTTPException(400, "No data loaded")

    _, session.amp1 = cf.detrend(session.treg.copy(), session.amp.copy())
    _reset_from_detrend(session)
    return CorrectionResult(message="Detrended")


@router.post("/sessions/{sid}/corrections/curvature", response_model=CorrectionResult)
async def curvature_correction(
    sid: str,
    body: CurvatureRequest,
    session: SessionState = Depends(get_session),
):
    """Apply G&A94 curvature correction + resampling. Source: detrend output
    if available, else raw."""
    if session.amp is None or session.treg is None:
        raise HTTPException(400, "No data loaded")

    amp_source = session.amp1 if session.amp1 is not None else session.amp
    treg_source = session.treg

    tapr, t_ga = cf.curvature_correction(
        treg_source.copy(), amp_source.copy(),
        body.drum_speed, body.stylet_length, body.inflection_amp,
    )

    session.sps = body.sps
    t_ga_res, amp_ga_res = cf.resample(t_ga.copy(), amp_source.copy(), body.sps, body.spline_order)
    tapr_res, amp1_res = cf.resample(tapr.copy(), amp_source.copy(), body.sps, body.spline_order)

    session.t_ga_res = t_ga_res
    session.amp_ga_res = amp_ga_res
    session.tapr_res = tapr_res
    session.amp1_res = amp1_res
    _reset_response(session)

    return CorrectionResult(
        message=f"Curvature corrected and resampled at {body.sps} SPS"
    )


@router.post("/sessions/{sid}/corrections/resample", response_model=CorrectionResult)
async def resample(
    sid: str,
    body: ResampleRequest,
    session: SessionState = Depends(get_session),
):
    """Resample time series directly, as an alternative to curvature's
    built-in resample (not chained after it). Source: detrend output if
    available, else raw."""
    if session.amp is None or session.treg is None:
        raise HTTPException(400, "No data loaded")

    amp_source = session.amp1 if session.amp1 is not None else session.amp
    t_source = session.treg

    session.sps = body.sps
    session.tres, session.amp_res = cf.resample(
        t_source.copy(), amp_source.copy(), body.sps, body.spline_order,
    )
    _reset_response(session)

    return CorrectionResult(message=f"Resampled at {body.sps} SPS")


@router.post("/sessions/{sid}/corrections/wiechert", response_model=CorrectionResult)
async def wiechert_response(
    sid: str,
    body: WiechertRequest,
    session: SessionState = Depends(get_session),
):
    """Apply Wiechert seismograph instrumental response correction. Source:
    G&A94 curvature-corrected resample if available, else the standalone
    resample - both are evenly sampled, which this FFT-based method requires."""
    if session.t_ga_res is not None and session.amp_ga_res is not None:
        amp_source = session.amp_ga_res
        t_source = session.t_ga_res
    elif session.tres is not None and session.amp_res is not None:
        amp_source = session.amp_res
        t_source = session.tres
    else:
        raise HTTPException(
            400,
            "No evenly-sampled data available for Wiechert correction - "
            "run Curvature Correction or Resample first",
        )

    amp_tapered = cf.taper(t_source, amp_source)

    fq, nmedios, h_w, sis_f, amp_correct, elapsed = cf.wiechert_response(
        t_source, amp_tapered,
        body.T0, body.epsilon, body.V0, body.water_level,
        deconv=body.deconvolve,
    )

    session.amp_correct = amp_correct

    return CorrectionResult(
        message=f"Wiechert response {'removed' if body.deconvolve else 'added'} ({elapsed:.3f}s)"
    )


@router.post("/sessions/{sid}/corrections/taper", response_model=CorrectionResult)
async def apply_taper(
    sid: str,
    body: TaperRequest,
    session: SessionState = Depends(get_session),
):
    """Apply Santoyo-Sesma cosine taper."""
    if session.amp is None or session.treg is None:
        raise HTTPException(400, "No data loaded")

    amp_source = session.amp_res if session.amp_res is not None else session.amp
    t_source = session.tres if session.tres is not None else session.treg

    session.amp = cf.taper(t_source, amp_source, percent=body.percent)
    return CorrectionResult(message=f"Taper applied ({body.percent*100:.0f}%)")


def _get_series(session: SessionState, name: str):
    """Get time/amplitude arrays for a named series."""
    if name == "raw" and session.amp is not None:
        return session.treg, session.amp
    elif name == "detrend" and session.amp1 is not None:
        return session.treg, session.amp1
    elif name == "curvature_ga" and session.amp_ga_res is not None and session.t_ga_res is not None:
        return session.t_ga_res, session.amp_ga_res
    elif name == "curvature_ls" and session.amp1_res is not None and session.tapr_res is not None:
        return session.tapr_res, session.amp1_res
    elif name == "resampled" and session.amp_res is not None:
        return session.tres, session.amp_res
    elif name == "response" and session.amp_correct is not None:
        t = session.t_ga_res if session.t_ga_res is not None else session.tres
        return t, session.amp_correct
    return None, None
