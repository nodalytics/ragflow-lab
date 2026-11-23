import pytest
from duration import parse_duration

@pytest.mark.parametrize("s,n", [("P3DT4H5M", 3*86400 + 4*3600 + 5*60), ("PT90S", 90), ("P1W", 604800),
                                  ("P1D", 86400), ("PT1H", 3600), ("PT0S", 0), ("P2DT1S", 2*86400 + 1)])
def test_valid(s, n):
    assert parse_duration(s) == n

@pytest.mark.parametrize("s", ["", "P", "3D", "PT", "P1H", "PT5M3H", "P1DT", "PXD", "P-1D", "p1d", "P1D "])
def test_invalid(s):
    with pytest.raises(ValueError):
        parse_duration(s)
