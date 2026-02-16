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
    DataUploaded, DetrendRequest, CurvatureRequest, ResampleRequest,
    WiechertRequest, TaperRequest, CorrectionResult, PlotTraces,
)
from backend.core import corrections as cf
from backend.core import io as tio

router = APIRouter(tags=["corrections"])


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

        # Reset corrections state
        session.amp1 = None
        session.amp_res = None
        session.amp1_res = None
        session.t_ga_res = None
        session.tapr_res = None
        session.tres = None
        session.amp_correct = None

        return DataUploaded(
            n_samples=len(amp),
            time_range=[float(treg.min()), float(treg.max())],
            filename=file.filename or "unknown",
        )
    except (IndexError, ValueError) as e:
        raise HTTPException(400, f"Failed to parse data file: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


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
    return CorrectionResult(message="Polarity inverted")


@router.post("/sessions/{sid}/corrections/detrend", response_model=CorrectionResult)
async def detrend(
    sid: str,
    body: DetrendRequest,
    session: SessionState = Depends(get_session),
):
    """Apply windowed detrending."""
    if session.amp is None or session.treg is None:
        raise HTTPException(400, "No data loaded")

    _, session.amp1 = cf.detrend(session.treg.copy(), session.amp.copy(), ntrv=body.window_size)
    return CorrectionResult(message=f"Detrended with window={body.window_size}")


@router.post("/sessions/{sid}/corrections/curvature", response_model=CorrectionResult)
async def curvature_correction(
    sid: str,
    body: CurvatureRequest,
    session: SessionState = Depends(get_session),
):
    """Apply G&A94 curvature correction + resampling."""
    if session.amp is None or session.treg is None:
        raise HTTPException(400, "No data loaded")

    amp_source = session.amp1 if session.amp1 is not None else session.amp
    treg_source = session.treg

    # Curvature correction
    tapr, t_ga = cf.curvature_correction(
        treg_source.copy(), amp_source.copy(),
        body.drum_speed, body.stylet_length, body.inflection_amp,
    )

    # Resample both variants
    session.sps = body.sps
    t_ga_res, amp_res = cf.resample(t_ga.copy(), amp_source.copy(), body.sps, body.spline_order)
    tapr_res, amp1_res = cf.resample(tapr.copy(), amp_source.copy(), body.sps, body.spline_order)

    session.t_ga_res = t_ga_res
    session.amp_res = amp_res
    session.tapr_res = tapr_res
    session.amp1_res = amp1_res
    session.vr = body.drum_speed

    return CorrectionResult(
        message=f"Curvature corrected and resampled at {body.sps} SPS"
    )


@router.post("/sessions/{sid}/corrections/resample", response_model=CorrectionResult)
async def resample(
    sid: str,
    body: ResampleRequest,
    session: SessionState = Depends(get_session),
):
    """Resample time series (without curvature correction)."""
    if session.amp is None or session.treg is None:
        raise HTTPException(400, "No data loaded")

    # Use best available data
    if session.amp1 is not None:
        amp_source = session.amp1
        t_source = session.treg
    elif session.amp_res is not None and session.t_ga_res is not None:
        amp_source = session.amp_res
        t_source = session.t_ga_res
    else:
        amp_source = session.amp
        t_source = session.treg

    session.sps = body.sps
    session.tres, session.amp_res = cf.resample(
        t_source.copy(), amp_source.copy(), body.sps, body.spline_order,
    )

    return CorrectionResult(message=f"Resampled at {body.sps} SPS")


@router.post("/sessions/{sid}/corrections/wiechert", response_model=CorrectionResult)
async def wiechert_response(
    sid: str,
    body: WiechertRequest,
    session: SessionState = Depends(get_session),
):
    """Apply Wiechert seismograph instrumental response correction."""
    # Select best available resampled data
    if session.amp_res is not None and session.tres is not None:
        amp_source = session.amp_res
        t_source = session.tres
    elif session.amp_res is not None and session.t_ga_res is not None:
        amp_source = session.amp_res
        t_source = session.t_ga_res
    elif session.amp is not None and session.treg is not None:
        amp_source = session.amp
        t_source = session.treg
    else:
        raise HTTPException(400, "No data available for Wiechert correction")

    # Apply taper first
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
    elif name == "curvature_ga" and session.amp_res is not None and session.t_ga_res is not None:
        return session.t_ga_res, session.amp_res
    elif name == "curvature_ls" and session.amp1_res is not None and session.tapr_res is not None:
        return session.tapr_res, session.amp1_res
    elif name == "resampled" and session.amp_res is not None:
        t = session.tres if session.tres is not None else session.t_ga_res
        return t, session.amp_res
    elif name == "response" and session.amp_correct is not None:
        t = session.tres if session.tres is not None else session.t_ga_res
        if t is None:
            t = session.treg
        return t, session.amp_correct
    return None, None
