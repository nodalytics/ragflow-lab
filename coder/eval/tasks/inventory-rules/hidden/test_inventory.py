import pytest
from inventory import Inventory, InsufficientStock

def test_add_remove_and_zero_removes():
    inv = Inventory(); inv.add("bolt", 5); inv.remove("bolt", 5)
    assert "bolt" not in inv.stock

def test_bad_quantities():
    inv = Inventory()
    for q in (0, -1):
        with pytest.raises(ValueError):
            inv.add("bolt", q)
    inv.add("bolt", 1)
    with pytest.raises(ValueError):
        inv.remove("bolt", 0)

def test_insufficient_changes_nothing():
    inv = Inventory(); inv.add("nut", 2)
    with pytest.raises(InsufficientStock):
        inv.remove("nut", 3)
    assert inv.stock == {"nut": 2}

def test_unknown_item():
    with pytest.raises(KeyError):
        Inventory().remove("ghost", 1)

def test_total_value():
    inv = Inventory(); inv.add("a", 2); inv.add("b", 3)
    assert inv.total_value({"a": 1.5, "b": 2}) == 9
    with pytest.raises(KeyError):
        inv.total_value({"a": 1.5})
