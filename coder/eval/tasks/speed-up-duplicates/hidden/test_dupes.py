import time
from dupes import find_duplicates

def test_order_and_values():
    assert find_duplicates([3, 1, 3, 2, 1, 3, 2]) == [3, 1, 2]
    assert find_duplicates([]) == [] and find_duplicates([1, 2]) == []
    assert find_duplicates(["b", "a", "a", "b"]) == ["a", "b"]

def test_large_input_is_fast():
    items = list(range(150000)) + list(range(0, 150000, 7))
    t = time.time()
    out = find_duplicates(items)
    assert time.time() - t < 1.0
    assert out == list(range(0, 150000, 7))
