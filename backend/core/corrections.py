"""
Core correction algorithms for historical seismograms.

Implements signal processing functions for detrending, curvature correction
(Grabrovec & Allegretti 1994), resampling, tapering, and Wiechert instrument
response removal/addition.

All functions are pure (no UI dependencies) and operate on numpy arrays.
"""

import time as _time

import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline, PchipInterpolator
from scipy.optimize import isotonic_regression
import obspy.signal.interpolation as osi


def detrend(t, a, ntrv=60):
    """
    De-trend time series in overlapped windows by first derivative
    and a second degree polynomial function.

    :param t: time array
    :type t: array_like
    :param a: amplitude array
    :type a: array_like
    :param ntrv: time window size in samples
    :type ntrv: int
    :returns: (t, amp1) detrended time and amplitude arrays
    :rtype: tuple(np.ndarray, np.ndarray)
    """
    a = np.array(a, dtype=float) - a[0]
    t = np.array(t, dtype=float) - t[0]
    amp1 = np.empty_like(a)
    n = len(a)

    for start in range(0, n, ntrv):
        end = min(start + ntrv, n)
        dt = t[start:end] - t[start]
        if len(dt) < 2:
            amp1[start:end] = a[start:end]
            continue
        coef = np.polyfit(dt, a[start:end], 1)
        amp1[start:end] = a[start:end] - (coef[0] * dt + coef[1])

    amp1 = amp1 - amp1[0]

    return t, amp1


def curvature_correction(treg, amp, vr, R, ampinfl):
    """
    Curvature correction with the Grabrovec and Allegretti (1994) equation.
    Additionally approximates by least squares the time series to ensure
    progressive time.

    :param treg: sampled time (evenly sampled or not)
    :type treg: array_like
    :param amp: amplitudes
    :type amp: array_like
    :param vr: Paper Drum Speed Rotation in mm/s
    :type vr: float
    :param R: Stylet length in mm
    :type R: float
    :param ampinfl: Amplitude of inflection point of the curvature
    :type ampinfl: float
    :returns: (tapr, t_ga) approximated and G&A94 corrected time arrays
    :rtype: tuple(np.ndarray, np.ndarray)
    """
    # Parameters and variables for loop
    sign0 = np.sign(amp[0])
    ki, kf = 0, 1
    tint = []
    while kf < len(treg) - 1:
        if np.sign(amp[kf]) != sign0:
            sign0 = np.sign(amp[kf])
            tint[ki:kf] = (np.linspace(treg[ki], treg[kf], kf - ki + 1))
            ki = kf
        kf = kf + 1
    tint[ki:] = (np.linspace(treg[ki], treg[-1], len(treg) - ki))
    tapr = np.array(tint).T
    del tint

    # Time correction per Grabrovec & Allegretti (1994), eq. on p.30:
    #   t = X0/vr - [R - sqrt(R^2 - Y0^2)] / vr
    # applied pointwise using each sample's own elongation Y0 from the zero
    # line (amp - ampinfl) - the paper has no notion of resetting the
    # correction at each zero-crossing; it is a direct, per-point formula.
    amp2 = amp - ampinfl
    Y0 = np.clip(amp2, -R, R)  # guard against sqrt of a negative number
    t_ga = treg - (R - np.sqrt(R**2 - Y0**2)) / vr

    # This pointwise correction is not guaranteed to be strictly increasing
    # when adjacent digitized points have a large amplitude jump (common
    # with hand-picked points, where R and vr can make the correction very
    # sensitive to point-to-point noise). Project onto the closest
    # (least-squares) non-decreasing sequence instead of a fragile local
    # 3-point sort, which neither guarantees global monotonicity nor
    # handles the first sample correctly.
    t_ga = isotonic_regression(t_ga).x

    # Linear approximation between re-sampled and recovered times by G&A94
    # progressive time values
    N = len(treg)
    G = np.transpose(np.matrix([np.ones(N), tapr.T]))
    ssq1 = np.sqrt(np.sum((t_ga - tapr)**2) / np.sum(tapr**2))
    ssq = 10000
    damp = np.eye(G.shape[1]) * 0.001
    sign0 = np.sign(amp[0])

    while ssq - ssq1 > 0.001:
        ki = 0
        ssq = ssq1
        for kf in range(1, len(treg)):
            if np.sign(amp[kf]) != sign0:
                mest = np.dot(
                    np.linalg.inv(np.dot(G[ki:kf, 0:].T, G[ki:kf, 0:]) + damp),
                    np.dot(G[ki:kf, 0:2].T, t_ga[ki:kf]).T
                )
                tapr[ki:kf] = (G[ki:kf, 0:] * mest).ravel()
                ki = kf
        mest = np.dot(
            np.linalg.inv(np.dot(G[ki:, 0:].T, G[ki:, 0:]) + damp),
            np.dot(G[ki:, 0:2].T, t_ga[ki:]).T
        )
        tapr[ki:] = (G[ki:, 0:] * mest).ravel()
        ssq1 = np.sqrt(np.sum((t_ga - tapr)**2) / np.sum(tapr**2))

    ind = np.argwhere(tapr > 0.0)[0][0]
    tapr[:ind] = np.linspace(0, tapr[ind] - 0.001, ind)

    return tapr, t_ga


def resample(old_time, data, sps, kind):
    """
    Time series re-sample: fit an irregular-to-uniform curve at a fixed 0.2s
    step, then resample that curve to the target sampling rate.

    'slinear' fits a strictly piecewise-linear curve through the data.
    'quadratic'/'cubic' both use a shape-preserving cubic Hermite spline
    (PCHIP) rather than an exact higher-order interpolating spline: on
    unevenly-spaced, noisy hand-digitized points, an exact quadratic/cubic
    spline is prone to Runge's-phenomenon overshoot (wild oscillation between
    distant points), producing amplitudes far outside the physical data
    range. PCHIP is guaranteed to introduce no new extrema between points.

    :param old_time: sampled time (evenly sampled or not)
    :type old_time: array_like
    :param data: amplitude array to interpolate
    :type data: array_like
    :param sps: sampling rate in samples per second
    :type sps: float
    :param kind: fit method ('slinear', 'quadratic', 'cubic')
    :type kind: str
    :returns: (new_time, amp_res) resampled time and amplitude arrays
    :rtype: tuple(np.ndarray, np.ndarray)
    """
    old_time = np.asarray(old_time, dtype=float)
    data = np.asarray(data, dtype=float)

    # When multiple points land on (near-)identical times instead of being
    # jittered apart (ties are expected after a monotonicity-constrained
    # time correction, e.g. curvature_correction), keep the sample with the
    # largest absolute amplitude rather than averaging the group - averaging
    # systematically damps genuine peak amplitudes, which matters for
    # amplitude-sensitive downstream analysis (e.g. finite-source inversion).
    unique_t, inverse = np.unique(old_time, return_inverse=True)
    order = np.lexsort((np.abs(data), inverse))  # primary: bin, secondary: |amp| ascending
    sorted_inverse = inverse[order]
    sorted_data = data[order]
    is_last_in_bin = np.empty(len(sorted_inverse), dtype=bool)
    is_last_in_bin[:-1] = sorted_inverse[:-1] != sorted_inverse[1:]
    is_last_in_bin[-1] = True
    old_time, data = unique_t, sorted_data[is_last_in_bin]

    dt = 1 / sps
    at = np.arange(old_time.min(), old_time.max() + 0.2, 0.2)

    if kind == "slinear":
        aa = InterpolatedUnivariateSpline(old_time, data, k=1)(at)
    else:
        aa = PchipInterpolator(old_time, data)(at)

    new_time = np.arange(old_time.min(), at.max(), dt)
    old_dt = at[1] - at[0]

    amp_res = osi.weighted_average_slopes(
        aa, at.min(), old_dt, new_time.min(), dt, len(new_time)
    )

    return new_time, amp_res


def taper(t, a, percent=0.08):
    """
    Apply a Santoyo-Sesma taper (cosine window) to the time series signal.

    :param t: time array
    :type t: array_like
    :param a: amplitude array
    :type a: array_like
    :param percent: percentage of max time to taper at start and end
    :type percent: float
    :returns: tapered amplitude array
    :rtype: np.ndarray
    """
    N = len(a)
    lim = t.max() * percent
    t1 = t[np.abs((t - lim)).argmin()]
    t2 = t[np.abs(t - (t.max() - t1)).argmin()]
    taper_window = np.ones(N)

    for i in range(N):
        if t[i] <= t1:
            taper_window[i] = 0.5 * (1 + np.cos(np.pi * (1 + (t[i] / t1))))
        elif t[i] >= t2:
            taper_window[i] = 0.5 * (1 + np.cos(np.pi * ((t[i] - t2) / (t.max() - t2))))

    return taper_window * a


def wiechert_response(t, a, T0, epsilon, V0, water_level, deconv=True):
    """
    Wiechert seismograph instrumental response correction via FFT.

    :param t: time array (evenly sampled)
    :type t: array_like
    :param a: amplitude array
    :type a: array_like
    :param T0: natural undamped period in seconds
    :type T0: float
    :param epsilon: damping rate
    :type epsilon: float
    :param V0: static magnification constant
    :type V0: int
    :param water_level: water level for regularization (0-1)
    :type water_level: float
    :param deconv: True to remove response (deconvolution),
                   False to add response (convolution)
    :type deconv: bool
    :returns: (fq, Nmedios, H_w, sis_f, amp_correct, elapsed_time)
    :rtype: tuple
    """
    N = len(a)
    if N % 2 == 0:
        Nmedios = int(N / 2)
    else:
        Nmedios = int((N / 2) + 1)

    dt = np.round(t[1] - t[0], 3)
    fN = 1 / (2 * dt)
    fq = np.fft.fftfreq(N, d=dt)
    fr = np.linspace(0, fN, Nmedios)
    w = fr * 2 * np.pi

    ini = _time.time()
    sis_f = np.fft.fft(a)

    # Angular undamped frequency
    W0 = 2 * np.pi / T0
    # Damping constant based on the rate damping
    ds = np.log(epsilon) / np.sqrt(np.pi**2 + np.log(epsilon)**2)

    # Transfer function
    H_w = V0 * (w**2 / np.sqrt(((W0**2 - w**2)**2) + (4 * ds**2 * W0**2 * w**2)))

    # Apply water level
    h_max = max(H_w)
    for j in range(len(fr) - 1):
        if H_w[j] < h_max * water_level:
            H_w[j] = h_max * water_level

    # Build symmetric transfer function
    HW = np.empty(N)
    HW[0:Nmedios] = H_w
    for j in range(int(N / 2)):
        HW[Nmedios + j] = H_w[Nmedios - j - 1]

    # Deconvolution or convolution
    if deconv:
        sis_corr = sis_f / HW
    else:
        sis_corr = sis_f * HW

    amp_correct = np.fft.ifft(sis_corr).real
    end = _time.time()

    return fq, Nmedios, H_w, sis_f, amp_correct, end - ini


def change_polarity(a):
    """
    Invert signal polarity.

    :param a: amplitude array
    :type a: array_like
    :returns: inverted amplitude array
    :rtype: np.ndarray
    """
    return a * -1


def save_ascii(t, a, outname):
    """
    Save time series as two-column ASCII file.

    :param t: time array
    :type t: array_like
    :param a: amplitude array
    :type a: array_like
    :param outname: output file path
    :type outname: str
    """
    data = np.array([t, a]).T
    with open(outname, 'w+'):
        np.savetxt(outname, data, fmt=['%e', '%e'], delimiter='\t')
