"""
Utility functions for image encoding and data serialization.
"""

import cv2
import numpy as np


def generate_display_jpeg(
    img: np.ndarray, max_dim: int = 4000, quality: int = 85
) -> tuple[bytes, float]:
    """
    Resize image for browser display and encode as JPEG.

    Returns (jpeg_bytes, scale_factor) where scale_factor = display_px / original_px.
    """
    h, w = img.shape[:2]
    scale = min(max_dim / max(h, w), 1.0)

    if scale < 1.0:
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        resized = img

    if len(resized.shape) == 2:
        resized = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)

    _, jpeg = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return jpeg.tobytes(), scale


def numpy_to_list(arr: np.ndarray | None) -> list | None:
    """Convert numpy array to Python list for JSON serialization."""
    if arr is None:
        return None
    return arr.tolist()
