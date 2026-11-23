import pytest
from pager import paginate

def test_first_page():
    assert paginate(list(range(10)), 1, 3) == [0, 1, 2]

def test_last_partial_page():
    assert paginate(list(range(10)), 4, 3) == [9]

def test_past_the_end():
    assert paginate(list(range(10)), 5, 3) == []

def test_bad_arguments():
    for page, per in [(0, 3), (-1, 3), (1, 0)]:
        with pytest.raises(ValueError):
            paginate([1, 2], page, per)
