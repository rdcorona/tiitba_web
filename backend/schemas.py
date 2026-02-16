"""
Pydantic request/response models for the TIITBA web API.
"""

from pydantic import BaseModel, Field


# --- Sessions ---

class SessionCreated(BaseModel):
    session_id: str

class SessionSummary(BaseModel):
    session_id: str
    has_image: bool
    has_points: bool
    has_data: bool
    has_scale: bool
    scale_mode: str | None
    imagefile_name: str | None
    datafile_name: str | None
    point_count: int


# --- Image ---

class ImageInfo(BaseModel):
    rows: int
    cols: int
    width_mm: float
    height_mm: float
    ppi: float

class ImageUploaded(BaseModel):
    filename: str
    ppi: float | None
    width: int
    height: int
    width_mm: float | None
    height_mm: float | None

class ImageDimensions(BaseModel):
    width: int
    height: int

class BinarizeResult(BaseModel):
    threshold: float

class TrimRequest(BaseModel):
    x: int
    y: int
    width: int
    height: int

class ContrastRequest(BaseModel):
    clip_limit: float = 2.2
    tile_size: int = 8


# --- Vectorization ---

class PointAdd(BaseModel):
    x: int
    y: int

class PointResponse(BaseModel):
    index: int
    time_or_x: float
    amplitude_or_y: float

class PointRemoved(BaseModel):
    removed: list[int]
    remaining: int

class TimemarkRequest(BaseModel):
    points: list[list[int]]
    ppi: float

class TimemarkResult(BaseModel):
    drum_speed: float
    amp0: float
    mean_distance_px: float

class CornerRequest(BaseModel):
    left_x: float
    up_y: float
    right_x: float
    down_y: float

class PlotData(BaseModel):
    time: list[float]
    amplitude: list[float]
    xlabel: str
    ylabel: str


# --- Corrections ---

class DetrendRequest(BaseModel):
    window_size: int = 60

class CurvatureRequest(BaseModel):
    drum_speed: float
    stylet_length: float
    inflection_amp: float
    sps: int
    spline_order: str = "cubic"

class ResampleRequest(BaseModel):
    sps: int
    spline_order: str = "cubic"

class WiechertRequest(BaseModel):
    T0: float
    epsilon: float
    V0: int
    water_level: float = Field(ge=0, le=1)
    deconvolve: bool = True

class TaperRequest(BaseModel):
    percent: float = 0.08

class CorrectionResult(BaseModel):
    success: bool = True
    message: str = ""

class DataUploaded(BaseModel):
    n_samples: int
    time_range: list[float]
    filename: str

class PlotTraces(BaseModel):
    traces: list[dict]


# --- Export ---

class SacHeaderRequest(BaseModel):
    station: str = ""
    channel: str = ""
    network: str = ""
    starttime: str | None = None
