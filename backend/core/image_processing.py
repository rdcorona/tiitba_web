"""
Pure image processing functions for seismogram raster images.

All functions operate on numpy arrays (OpenCV images) and return
processed arrays. No UI dependencies.
"""

import cv2
import numpy as np
from PIL import Image


# Maximum image size for Pillow decompression
MAX_IMAGE_PIXELS = 999_999_999
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def load_image(filepath):
    """
    Load a seismogram raster image in grayscale.

    :param filepath: path to the image file
    :type filepath: str
    :returns: grayscale image array
    :rtype: np.ndarray
    """
    return cv2.imread(filepath, 0)


def get_image_ppi(filepath):
    """
    Extract PPI (pixels per inch) metadata from an image file.

    :param filepath: path to the image file
    :type filepath: str
    :returns: PPI value or None if not found
    :rtype: float or None
    """
    try:
        img = Image.open(filepath)
        return float(img.info['dpi'][0])
    except (KeyError, TypeError):
        return None


def rotate_90_clockwise(img):
    """
    Rotate image 90 degrees clockwise.

    :param img: input image array
    :type img: np.ndarray
    :returns: rotated image
    :rtype: np.ndarray
    """
    return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)


def enhance_contrast(img, clip_limit=2.2, tile_size=8):
    """
    Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).

    :param img: grayscale input image
    :type img: np.ndarray
    :param clip_limit: CLAHE clip limit
    :type clip_limit: float
    :param tile_size: CLAHE tile grid size
    :type tile_size: int
    :returns: contrast-enhanced image
    :rtype: np.ndarray
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    return clahe.apply(img)


def binarize(img):
    """
    Convert image to binary using Otsu's threshold method.

    :param img: grayscale input image
    :type img: np.ndarray
    :returns: (threshold_value, binary_image)
    :rtype: tuple(float, np.ndarray)
    """
    threshold, binary = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return threshold, binary


def trim(img, roi):
    """
    Crop image to the specified region of interest.

    :param img: input image array
    :type img: np.ndarray
    :param roi: region of interest (x, y, width, height)
    :type roi: tuple(int, int, int, int)
    :returns: cropped image
    :rtype: np.ndarray
    """
    x, y, w, h = roi
    return img[int(y):int(y + h), int(x):int(x + w)]


def get_dimensions(img, ppi):
    """
    Calculate image dimensions in pixels and millimeters.

    :param img: input image array
    :type img: np.ndarray
    :param ppi: pixels per inch
    :type ppi: float
    :returns: dict with rows, cols, width_mm, height_mm
    :rtype: dict
    """
    rows, cols = img.shape[0:2]
    width_mm = (cols / ppi) * 25.4
    height_mm = (rows / ppi) * 25.4
    return {
        'rows': rows,
        'cols': cols,
        'width_mm': width_mm,
        'height_mm': height_mm,
    }


def save_image_with_ppi(img, outpath, ppi):
    """
    Save processed image preserving PPI metadata.

    :param img: image array to save
    :type img: np.ndarray
    :param outpath: output file path
    :type outpath: str
    :param ppi: pixels per inch to embed in metadata
    :type ppi: float
    """
    pil_img = Image.fromarray(img)
    pil_img.save(outpath, dpi=(ppi, ppi))


def to_color(img):
    """
    Convert grayscale image to BGR color.

    :param img: grayscale image
    :type img: np.ndarray
    :returns: BGR color image
    :rtype: np.ndarray
    """
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
