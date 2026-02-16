"""
I/O functions for loading and saving seismological data.

Supports ASCII two-column format, SAC, MINISEED, and SEISAN S-file formats.
No UI dependencies.
"""

import os
import datetime

import numpy as np
from obspy.core import UTCDateTime, Stream
from obspy.core.trace import Trace, Stats


def load_ascii(filepath):
    """
    Load a two-column ASCII time-series file.

    :param filepath: path to the data file
    :type filepath: str
    :returns: (time, amplitude) arrays
    :rtype: tuple(np.ndarray, np.ndarray)
    :raises IndexError: if file format is unsupported
    """
    treg = np.genfromtxt(filepath, usecols=0, dtype=float, comments='#')
    amp = np.genfromtxt(filepath, usecols=1, dtype=float, comments='#')
    return treg, amp


def save_ascii(t, a, outpath):
    """
    Save time series as two-column tab-separated ASCII file.

    :param t: time array
    :type t: array_like
    :param a: amplitude array
    :type a: array_like
    :param outpath: output file path
    :type outpath: str
    """
    data = np.array([t, a]).T
    with open(outpath, 'w+'):
        np.savetxt(outpath, data, fmt=['%e', '%e'], delimiter='\t')


def build_sac_header(station, channel, delta, network='', starttime=None):
    """
    Build an ObsPy Stats header for SAC/MINISEED export.

    :param station: station code
    :type station: str
    :param channel: channel code (e.g., 'HHZ')
    :type channel: str
    :param delta: sample interval in seconds
    :type delta: float
    :param network: network code
    :type network: str
    :param starttime: event origin time string or UTCDateTime
    :type starttime: str or UTCDateTime or None
    :returns: populated Stats header
    :rtype: obspy.core.trace.Stats
    """
    header = Stats()
    header.station = station
    header.channel = channel
    header.delta = delta
    if network:
        header.network = network
    if starttime is not None:
        if isinstance(starttime, str):
            header.starttime = UTCDateTime(starttime)
        else:
            header.starttime = starttime
    return header


def save_sac(t, a, outpath, header):
    """
    Save time series as SAC format.

    :param t: time array
    :type t: array_like
    :param a: amplitude array
    :type a: array_like
    :param outpath: output file path (should end in .sac)
    :type outpath: str
    :param header: ObsPy Stats header
    :type header: obspy.core.trace.Stats
    """
    trace = Trace(data=a, header=header)
    trace.write(outpath, format='SAC')


def save_miniseed(traces_dict, outpath):
    """
    Save multiple traces as MINISEED format.

    :param traces_dict: dict of {name: Trace} pairs
    :type traces_dict: dict
    :param outpath: output file path
    :type outpath: str
    """
    st = Stream()
    for trace in traces_dict.values():
        st += Stream(trace)
    st.write(outpath, format='MSEED')


def create_trace(amp, header):
    """
    Create an ObsPy Trace from amplitude data and header.

    :param amp: amplitude array
    :type amp: array_like
    :param header: ObsPy Stats header
    :type header: obspy.core.trace.Stats
    :returns: ObsPy Trace
    :rtype: obspy.core.trace.Trace
    """
    return Trace(data=amp, header=header)


def write_sfile(filepath, data_dict, date, hour, directory_name):
    """
    Write phase picks in SEISAN S-file format.

    :param filepath: output file path
    :type filepath: str
    :param data_dict: dict of pick data keyed by record name
    :type data_dict: dict
    :param date: [year, month, day] strings
    :type date: list[str]
    :param hour: [hour, minute, second] strings
    :type hour: list[str]
    :param directory_name: filename of the source image
    :type directory_name: str
    """
    file_exists = os.path.exists(filepath) and os.stat(filepath).st_size > 0

    if file_exists:
        f = open(filepath, 'a')
    else:
        f = open(filepath, 'w+')
        now = str(datetime.datetime.now())
        idd = date[0] + date[1] + date[2] + hour[0] + hour[1] + hour[2]
        f.seek(0)
        f.write(" %4i %2i%2i " % (int(date[0]), int(date[1]), int(date[2])))
        f.write("%2i%2i %4.1f %s %57i\n" % (
            int(hour[0]), int(hour[1]), float(hour[2]), 'R', 1
        ))
        f.write(" %10s %14s %15s%14s %3s%15s%5s\n" % (
            'ACTION:NEW', now[2:16], 'OP:rdcf STATUS:', '', 'ID:', idd + 'd', 'I'
        ))
        f.write(" %-30s %48i\n" % (directory_name, 6))
        f.write(" STAT SP IPHASW D HRMM SECON CODA AMPLIT PERI AZIMU"
                " VELO AIN AR TRES W  DIS CAZ7\n")

    for d_key in data_dict.keys():
        o = data_dict[d_key]
        has_coda = 'coda' in o.keys()

        f.write(" %-5s%1s%1s %1s%-4s%1i %1s %2i%2i%6.2f" % (
            o['Sta'], o['Chan'][-2], o['Chan'][-1],
            o['QualityP'][0], 'P', o['weightP'], o['polarP'],
            int(o['Ptime'][0:2]), int(o['Ptime'][3:5]),
            float(o['Ptime'][6:-1])
        ))
        if has_coda:
            f.write(" %4i \n" % int(o['coda']))
        else:
            f.write(" \n")

        f.write(" %-5s%1s%1s %1s%-4s%1i %1s %2i%2i%6.2f" % (
            o['Sta'], o['Chan'][-2], o['Chan'][-1],
            o['QualityS'][0], 'S', o['weightS'], ' ',
            int(o['Stime'][0:2]), int(o['Stime'][3:5]),
            float(o['Stime'][6:-1])
        ))
        if has_coda:
            f.write(" %4i \n" % int(o['coda']))
        else:
            f.write(" \n")

    f.close()
