"""
Mathematical utility functions for TIITBA.

Provides helper functions for nearest-value lookup, Jacobian computation,
and least-squares constraint application.
"""

import numpy as np


def find_nearest(array, value):
    """
    Find the index of the nearest value in an array.

    :param array: input array to search
    :type array: array_like
    :param value: target value
    :type value: float
    :returns: index of the nearest value
    :rtype: int
    """
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx


def compute_jacobian(prms, direct_data, model_data, vector):
    """
    Compute the Jacobian matrix for least-squares approximation
    using finite differences on a 2nd-degree polynomial model.

    :param prms: parameters [a0, a1, a2] for the polynomial
    :type prms: array_like
    :param direct_data: observed data
    :type direct_data: array_like
    :param model_data: estimated data
    :type model_data: array_like
    :param vector: independent variable values
    :type vector: array_like
    :returns: (G, prms, d) - Jacobian matrix, updated parameters,
              estimated data
    :rtype: tuple(np.ndarray, np.ndarray, np.ndarray)
    """
    n_params = len(prms)
    n_data = len(direct_data)
    delm = prms / 1000
    G = np.ones([n_data, 3])

    for jj in range(n_params):
        prms[jj] = prms[jj] + delm[jj]
        d2 = (prms[0] * vector**0) + (prms[1] * vector) + (prms[2] * vector**2)
        prms[jj] = prms[jj] - 2 * delm[jj]
        d1 = (prms[0] * vector**0) + (prms[1] * vector) + (prms[2] * vector**2)
        prms[jj] = prms[jj] + delm[jj]
        G[0:n_data, jj] = (d2 - d1) / (2 * delm[jj])

    d = (prms[0] * vector**0) + (prms[1] * vector) + (prms[2] * vector**2)
    return G, prms, d


def apply_constraints(G, dif, vector, indx, di):
    """
    Apply boundary constraints to the least-squares system.

    Restricts the polynomial solution to pass through the first,
    second, and last data points.

    :param G: Jacobian matrix
    :type G: np.matrix
    :param dif: difference between observed and estimated data
    :type dif: array_like
    :param vector: independent variable values
    :type vector: array_like
    :param indx: index array
    :type indx: array_like
    :param di: estimated data
    :type di: array_like
    :returns: (GtG, Gd) - constrained normal equation matrices
    :rtype: tuple(np.matrix, np.matrix)
    """
    GtG = np.transpose(G) * G
    Gd = np.transpose(G) * dif

    # 1st constraint: pass through first point
    h = np.array([1, vector[0], vector[0]**2])
    v = np.array([1, vector[0], vector[0]**2, 0])
    s = di[0]
    GtG = np.hstack([GtG, h.reshape(3, 1)])
    GtG = np.vstack([GtG, v])
    Gd = np.vstack([Gd, s])

    # 2nd constraint: pass through last point
    h = np.array([1, vector[-1], vector[-1]**2, 0])
    v = np.array([1, vector[-1], vector[-1]**2, 0, 0])
    s = di[-1]
    GtG = np.hstack([GtG, h.reshape(4, 1)])
    GtG = np.vstack([GtG, v])
    Gd = np.vstack([Gd, s])

    # 3rd constraint: pass through second point
    h = np.array([1, vector[1], vector[1]**2, 0, 0])
    v = np.array([1, vector[1], vector[1]**2, 0, 0, 0])
    s = di[1]
    GtG = np.hstack([GtG, h.reshape(5, 1)])
    GtG = np.vstack([GtG, v])
    Gd = np.vstack([Gd, s])

    return GtG, Gd
