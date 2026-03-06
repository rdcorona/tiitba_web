"""
Image processing API endpoints.

Handles upload, display, and processing operations (rotate, contrast, binarize, trim).
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response

from backend.config import settings
from backend.dependencies import get_session
from backend.session import SessionState
from backend.schemas import (
    ImageUploaded, ImageDimensions, ImageInfo, BinarizeResult,
    TrimRequest, ContrastRequest,
)
from backend.utils import generate_display_jpeg
from backend.core import image_processing as imgproc

router = APIRouter(tags=["images"])


@router.post("/sessions/{sid}/image", response_model=ImageUploaded)
async def upload_image(
    sid: str,
    file: UploadFile = File(...),
    ppi: float | None = Form(None),
    session: SessionState = Depends(get_session),
):
    """Upload a seismogram image for processing."""
    contents = await file.read()
    if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")

    # Save to temp file for OpenCV to read
    suffix = Path(file.filename or "image.jpg").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        img = imgproc.load_image(tmp_path)
        if img is None:
            raise HTTPException(400, "Failed to load image. Unsupported format?")

        detected_ppi = imgproc.get_image_ppi(tmp_path)
        session.ppi = ppi or detected_ppi
        session.img = img
        session.imagefile_name = file.filename
        session.display_jpeg = None  # invalidate cache

        dims = None
        if session.ppi:
            dims = imgproc.get_dimensions(img, session.ppi)
            session.imheight_mm = dims['height_mm']

        h, w = img.shape[:2]
        return ImageUploaded(
            filename=file.filename or "unknown",
            ppi=session.ppi,
            width=w,
            height=h,
            width_mm=dims['width_mm'] if dims else None,
            height_mm=dims['height_mm'] if dims else None,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/sessions/{sid}/image")
async def get_display_image(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Get the current image as a display-quality JPEG."""
    if session.img is None:
        raise HTTPException(400, "No image loaded")

    if session.display_jpeg is None:
        jpeg_bytes, scale = generate_display_jpeg(
            session.img,
            max_dim=settings.display_image_max_dim,
            quality=settings.jpeg_quality,
        )
        session.display_jpeg = jpeg_bytes
        session.display_scale = scale

    return Response(
        content=session.display_jpeg,
        media_type="image/jpeg",
        headers={"X-Display-Scale": str(session.display_scale)},
    )


@router.post("/sessions/{sid}/image/rotate", response_model=ImageDimensions)
async def rotate_image(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Rotate image 90 degrees clockwise."""
    if session.img is None:
        raise HTTPException(400, "No image loaded")

    session.img = imgproc.rotate_90_clockwise(session.img)
    session.display_jpeg = None
    h, w = session.img.shape[:2]

    if session.ppi:
        dims = imgproc.get_dimensions(session.img, session.ppi)
        session.imheight_mm = dims['height_mm']

    return ImageDimensions(width=w, height=h)


@router.post("/sessions/{sid}/image/contrast", response_model=ImageDimensions)
async def enhance_contrast(
    sid: str,
    body: ContrastRequest | None = None,
    session: SessionState = Depends(get_session),
):
    """Apply CLAHE contrast enhancement."""
    if session.img is None:
        raise HTTPException(400, "No image loaded")

    clip = body.clip_limit if body else 2.2
    tile = body.tile_size if body else 8
    session.img = imgproc.enhance_contrast(session.img, clip_limit=clip, tile_size=tile)
    session.display_jpeg = None
    h, w = session.img.shape[:2]
    return ImageDimensions(width=w, height=h)


@router.post("/sessions/{sid}/image/binarize", response_model=BinarizeResult)
async def binarize_image(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Binarize image using Otsu's threshold."""
    if session.img is None:
        raise HTTPException(400, "No image loaded")

    session.img_pre_binarize = session.img.copy()
    threshold, binary = imgproc.binarize(session.img)
    session.img = binary
    session.display_jpeg = None
    return BinarizeResult(threshold=threshold)

@router.post("/sessions/{sid}/image/binarize/undo", response_model=ImageDimensions)
async def undo_binarize_image(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Undo binarization by restoring the previous image state."""
    if session.img_pre_binarize is None:
        raise HTTPException(400, "No previous state to restore")

    session.img = session.img_pre_binarize
    session.img_pre_binarize = None
    session.display_jpeg = None
    h, w = session.img.shape[:2]
    return ImageDimensions(width=w, height=h)


@router.post("/sessions/{sid}/image/trim", response_model=ImageDimensions)
async def trim_image(
    sid: str,
    body: TrimRequest,
    session: SessionState = Depends(get_session),
):
    """Trim image to specified ROI."""
    if session.img is None:
        raise HTTPException(400, "No image loaded")

    roi = (body.x, body.y, body.width, body.height)
    session.img = imgproc.trim(session.img, roi)
    session.display_jpeg = None
    h, w = session.img.shape[:2]

    if session.ppi:
        dims = imgproc.get_dimensions(session.img, session.ppi)
        session.imheight_mm = dims['height_mm']

    return ImageDimensions(width=w, height=h)


@router.get("/sessions/{sid}/image/info", response_model=ImageInfo)
async def image_info(
    sid: str,
    session: SessionState = Depends(get_session),
):
    """Get image dimensions in pixels and mm."""
    if session.img is None:
        raise HTTPException(400, "No image loaded")
    if session.ppi is None:
        raise HTTPException(400, "PPI not set. Upload image with ppi parameter.")

    dims = imgproc.get_dimensions(session.img, session.ppi)
    return ImageInfo(ppi=session.ppi, **dims)
