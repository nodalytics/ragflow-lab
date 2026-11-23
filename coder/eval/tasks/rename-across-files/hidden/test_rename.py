import pathlib, warnings
import pytest
from shop.pricing import compute_total, calc_total
from shop.cart import Cart
from shop.invoice import invoice_line

def test_new_name():
    assert compute_total([1.0, 2.0], 0.1) == 3.3

def test_alias_warns_and_agrees():
    with pytest.warns(DeprecationWarning):
        assert calc_total([1.0, 2.0], 0.1) == 3.3

def test_callers_use_new_name_without_warnings():
    c = Cart(); c.add(5.0); c.add(5.0)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert c.total(0.5) == 15.0
        assert invoice_line([10.0], 0.0) == "TOTAL 10.00"

def test_no_old_name_left_in_callers():
    root = pathlib.Path(__file__).resolve().parent.parent / "shop"
    for f in ("cart.py", "invoice.py"):
        assert "calc_total" not in (root / f).read_text(), f
