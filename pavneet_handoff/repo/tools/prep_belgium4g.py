"""Build the LTE channel traces used by D39-D43 (rclib/bufenv.py, RC_BUF_CHANNEL=trace) from the Belgium 4G/LTE logs.

Source: J. van der Hooft, S. Petrangeli, T. Wauters, R. Huysegems, P. Rondao Alface, T. Bostoen, F. De Turck,
"HTTP/2-Based Adaptive Streaming of HEVC Video Over 4G/LTE Networks", IEEE Communications Letters 20(11), 2016.
Logs: https://users.ugent.be/~jvdrhoof/dataset-4g/ (logs_all.zip, 40 report_<mode>_<k>.log files).

Each log line: timestamp_ms, elapsed_ms, lat, lon, bytes_received, interval_ms. We keep only the throughput,
bits/s = bytes x 8 x 1000 / interval_ms, one value per line (about 1 s), and drop the GPS columns.
Output: {"<mode>_<k>": np.array of bits/s} pickled (the file bufenv.TRACES points at; train/val/test split by file name
hash in bufenv.trace_split).

  python tools/prep_belgium4g.py logs_all.zip throughput.pkl
"""
import io
import os
import pickle
import sys
import zipfile

import numpy as np


def parse(text):
    r = []
    for line in text.splitlines():
        f = line.split()
        if len(f) >= 6 and float(f[5]) > 0:
            r.append(float(f[4]) * 8 * 1000 / float(f[5]))
    return np.array(r)


def main(src, out):
    d = {}
    with zipfile.ZipFile(src) as z:
        for n in sorted(z.namelist()):
            b = os.path.basename(n)
            if b.startswith("report_") and b.endswith(".log"):
                d[b[len("report_"):-len(".log")]] = parse(io.TextIOWrapper(z.open(n), encoding="utf-8").read())
    pickle.dump(d, open(out, "wb"))
    print(f"{len(d)} traces, {sum(len(v) for v in d.values())} s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
