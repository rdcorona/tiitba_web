"""
Coordinate conversion functions for seismogram vectorization.

Provides methods to convert pixel coordinates to physical units
using either continuous time-marks or opposite corner values.
"""

import numpy as np


def compute_drum_speed(time_marks, ppi):
    """
    Compute drum speed rotation from continuous time-marks on the image.

    Time-marks are spaced 60 seconds apart. The function calculates
    the average pixel distance between marks and converts to mm/s.

    :param time_marks: list of (x, y) pixel coordinates of time marks
    :type time_marks: list[tuple(int, int)]
    :param ppi: image pixels per inch
    :type ppi: float
    :returns: (drum_speed_mm_s, amp0_mm, mean_distance_px)
    :rtype: tuple(float, float, float)
    """
    dd = np.array(time_marks)
    distances = np.array([dd[i + 1, 0] - dd[i, 0] for i in range(len(dd) - 1)])
    mean_px = np.mean(distances)

    # Convert pixel distance to mm/s (60-second marks)
    drum_speed = ((mean_px * 25.4) / ppi) / 60

    # Baseline amplitude from the average Y of first two marks
    amp0 = (((dd[0, 1] + dd[1, 1]) / 2) / ppi) * 25.4

    return drum_speed, amp0, mean_px


def pixels_to_timemarks(points_px, ppi, vr, amp0, image_height_mm):
    """
    Convert pixel coordinates to physical units using time-marks method.

    :param points_px: pixel coordinates [(x, y), ...]
    :type points_px: list[tuple] or np.ndarray
    :param ppi: pixels per inch
    :type ppi: float
    :param vr: drum speed rotation in mm/s
    :type vr: float
    :param amp0: baseline amplitude in mm
    :type amp0: float
    :param image_height_mm: image height in mm
    :type image_height_mm: float
    :returns: (time_seconds, amplitude_mm) arrays
    :rtype: tuple(np.ndarray, np.ndarray)
    """
    points = np.array(points_px)
    x_px = points[:, 0]
    y_px = points[:, 1]

    time_s = ((x_px / ppi) * 25.4) / vr
    amp_mm = ((((y_px / ppi) * 25.4) * -1) + image_height_mm) - amp0

    return time_s, amp_mm


def pixels_to_corners(points_px, x_values, y_values, img_cols, img_rows):
    """
    Convert pixel coordinates to physical units using opposite corners.

    :param points_px: pixel coordinates [(x, y), ...]
    :type points_px: list[tuple] or np.ndarray
    :param x_values: [left_x, right_x] corner values
    :type x_values: np.ndarray
    :param y_values: [up_y, down_y] corner values
    :type y_values: np.ndarray
    :param img_cols: image width in pixels
    :type img_cols: int
    :param img_rows: image height in pixels
    :type img_rows: int
    :returns: (x_scaled, y_scaled) arrays in physical units
    :rtype: tuple(np.ndarray, np.ndarray)
    """
    points = np.array(points_px)
    x_px = points[:, 0]
    y_px = points[:, 1]

    x_scaled = x_values.min() + ((x_px * (x_values[1] - x_values[0])) / img_cols)

    if y_values[0] > y_values[1]:
        y_flipped = (y_px * -1) + img_rows
        y_scaled = y_values.min() + ((y_flipped * np.abs(y_values[1] - y_values[0])) / img_rows)
    else:
        y_scaled = y_values.min() + ((y_px * np.abs(y_values[1] - y_values[0])) / img_rows)

    return x_scaled, y_scaled


def pixels_to_raw(points_px, img_rows):
    """
    Convert pixel coordinates to raw (unscaled) values.
    Flips Y axis so that positive Y is upward.

    :param points_px: pixel coordinates [(x, y), ...]
    :type points_px: list[tuple] or np.ndarray
    :param img_rows: image height in pixels
    :type img_rows: int
    :returns: (x_pixels, y_pixels_flipped)
    :rtype: tuple(np.ndarray, np.ndarray)
    """
    points = np.array(points_px)
    return points[:, 0], (points[:, 1] * -1) + img_rows
