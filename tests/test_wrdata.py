"""Unit tests for the wrdata ASCII parser."""

import numpy as np
import pytest

from lab.wrdata import load_wrdata


def test_two_vector_file(tmp_path):
    f = tmp_path / "out.txt"
    f.write_text(
        " 1.000000e+01  -1.0e-02  1.000000e+01  -5.0e-01\n"
        " 1.000000e+02  -3.0e+00  1.000000e+02  -4.5e+01\n"
        " 1.000000e+03  -2.0e+01  1.000000e+03  -8.5e+01\n"
    )
    scale, vectors = load_wrdata(f)
    assert scale.tolist() == [10.0, 100.0, 1000.0]
    assert len(vectors) == 2
    assert vectors[0].tolist() == [-0.01, -3.0, -20.0]
    assert vectors[1].tolist() == [-0.5, -45.0, -85.0]


def test_single_vector_file(tmp_path):
    f = tmp_path / "out.txt"
    f.write_text("0.0 1.0\n1.0 2.0\n2.0 3.0\n")
    scale, vectors = load_wrdata(f)
    assert len(vectors) == 1
    assert np.allclose(vectors[0], [1.0, 2.0, 3.0])


def test_odd_column_count_raises(tmp_path):
    f = tmp_path / "bad.txt"
    f.write_text("1.0 2.0 3.0\n4.0 5.0 6.0\n")
    with pytest.raises(ValueError, match="even number of columns"):
        load_wrdata(f)
