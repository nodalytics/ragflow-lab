import pytest
from cache import LRUCache

def test_basic_eviction():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2)
    assert c.get("a") == 1          # a is now most recent
    c.put("c", 3)                   # evicts b
    assert c.get("b") is None
    assert c.get("a") == 1 and c.get("c") == 3
    assert len(c) == 2

def test_update_moves_to_front():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2); c.put("a", 10)   # a updated and most recent
    c.put("c", 3)                                  # evicts b
    assert c.get("a") == 10 and c.get("b") is None

def test_capacity_one_and_bad_capacity():
    c = LRUCache(1)
    c.put(1, 1); c.put(2, 2)
    assert c.get(1) is None and c.get(2) == 2
    with pytest.raises(ValueError):
        LRUCache(0)

def test_many_operations_are_fast():
    import time
    c = LRUCache(1000)
    t = time.time()
    for i in range(200000):
        c.put(i, i)
        c.get(i - 500)
    assert time.time() - t < 3
    assert len(c) == 1000
