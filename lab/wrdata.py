"""Parser for ngspice `wrdata` ASCII output.

With default settings ngspice writes one (scale, value) column pair per
requested vector: `wrdata out.txt v(a) v(b)` produces four columns
(scale, v(a), scale, v(b)).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def load_wrdata(path: str | Path) -> tuple[np.ndarray, list[np.ndarray]]:
    """Load a wrdata file. Returns (scale, [vector1, vector2, ...])."""
    data = np.loadtxt(path)
    if data.ndim == 1:
        # A 1-D result means the file has a single row (e.g. an operating point).
        data = data.reshape(1, -1)
    n_cols = data.shape[1]
    if n_cols % 2 != 0:
        raise ValueError(
            f"{path}: expected an even number of columns (scale/value pairs), got {n_cols}"
        )
    scale = data[:, 0]
    vectors = [data[:, 2 * i + 1] for i in range(n_cols // 2)]
    return scale, vectors
