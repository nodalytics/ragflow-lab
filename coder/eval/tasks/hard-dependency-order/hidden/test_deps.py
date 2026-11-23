import pytest
from deps import order, CycleError

def test_simple():
    assert order({"app": ["lib", "log"], "lib": ["log"], "log": []}) == ["log", "lib", "app"]

def test_alphabetically_smallest_order():
    assert order({"b": [], "a": [], "c": ["a"]}) == ["a", "b", "c"]
    assert order({"z": [], "a": ["z"], "m": []}) == ["m", "z", "a"]

def test_external_dependency():
    assert order({"a": ["x"]}) == ["x", "a"]

def check_cycle(deps, cyc):
    assert cyc[0] == cyc[-1] and len(cyc) >= 2
    for u, v in zip(cyc, cyc[1:]):
        assert v in deps.get(u, []), (u, v)
    assert cyc[0] == min(cyc)

def test_cycle_is_reported_as_a_path():
    deps = {"d": [], "c": ["a"], "a": ["b"], "b": ["c"], "e": ["d"]}
    with pytest.raises(CycleError) as e:
        order(deps)
    check_cycle(deps, e.value.cycle)
    assert set(e.value.cycle) == {"a", "b", "c"}

def test_self_dependency():
    with pytest.raises(CycleError) as e:
        order({"a": ["a"]})
    assert e.value.cycle == ["a", "a"]

def test_cycle_behind_a_tail():
    deps = {"start": ["x"], "x": ["y"], "y": ["z"], "z": ["y"]}
    with pytest.raises(CycleError) as e:
        order(deps)
    check_cycle(deps, e.value.cycle)
    assert e.value.cycle == ["y", "z", "y"]
