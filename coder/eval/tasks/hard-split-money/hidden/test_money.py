import random
from decimal import Decimal as M
import pytest
from money import split

def test_examples():
    assert split("100.00", [1, 1, 1]) == [M("33.34"), M("33.33"), M("33.33")]
    assert split("0.05", [1, 1, 1, 1]) == [M("0.02"), M("0.01"), M("0.01"), M("0.01")]
    assert split("10", [3, 1]) == [M("7.50"), M("2.50")]
    assert split("1.00", [1, 0, 1]) == [M("0.50"), M("0.00"), M("0.50")]
    assert split("0.01", [1, 1]) == [M("0.01"), M("0.00")]

def test_largest_remainder_not_first():
    # shares 0.333.., 0.666..: the second has the larger remainder
    assert split("1.00", [1, 2]) == [M("0.33"), M("0.67")]

def test_negative():
    assert split("-1.00", [1, 1, 1]) == [M("-0.34"), M("-0.33"), M("-0.33")]

def test_always_adds_up_and_stays_within_a_cent():
    rnd = random.Random(1)
    for _ in range(300):
        total = M(rnd.randint(-100000, 100000)) / 100
        w = [rnd.choice([0, 1, 2, 3, 0.5, 7.25]) for _ in range(rnd.randint(1, 7))]
        if sum(w) == 0:
            continue
        parts = split(total, w)
        assert sum(parts) == total
        assert all(p == p.quantize(M("0.01")) for p in parts)
        for p, x in zip(parts, w):
            assert abs(p - total * M(str(x)) / M(str(sum(w)))) < M("0.01")

@pytest.mark.parametrize("total,w", [("1.005", [1]), ("1", []), ("1", [0, 0]), ("1", [-1, 2])])
def test_invalid(total, w):
    with pytest.raises(ValueError):
        split(total, w)
