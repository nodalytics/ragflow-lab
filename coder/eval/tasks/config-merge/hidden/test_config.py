import copy
import pytest
from config import load_config

D = {"db": {"host": "localhost", "port": 5432, "ssl": False}, "debug": False, "tags": ["a"], "rate": 1.5}

def test_precedence_and_deep_merge():
    f = {"db": {"host": "file-host"}, "tags": ["b", "c"]}
    env = {"APP_DB__PORT": "6000", "APP_DEBUG": "TRUE", "PATH": "/bin", "APP_RATE": "2.5"}
    c = load_config(D, f, env)
    assert c == {"db": {"host": "file-host", "port": 6000, "ssl": False}, "debug": True,
                 "tags": ["b", "c"], "rate": 2.5}

def test_new_keys_and_strings():
    c = load_config(D, {}, {"APP_DB__NAME": "main", "APP_NEW": "x"})
    assert c["db"]["name"] == "main" and c["new"] == "x"

def test_bad_conversion():
    with pytest.raises(ValueError):
        load_config(D, {}, {"APP_DB__PORT": "abc"})
    with pytest.raises(ValueError):
        load_config(D, {}, {"APP_DEBUG": "maybe"})

def test_inputs_untouched():
    d, f = copy.deepcopy(D), {"db": {"host": "h"}}
    f0 = copy.deepcopy(f)
    load_config(d, f, {"APP_DB__HOST": "e"})
    assert d == D and f == f0
