import pathlib
from users import connect, find_user, add_user

def test_normal():
    db = connect()
    assert find_user(db, "ann") == ("ann", "ann@x.org")
    assert find_user(db, "zed") is None

def test_injection_finds_nothing():
    db = connect()
    assert find_user(db, "x' or '1'='1") is None

def test_quotes_are_data():
    db = connect()
    add_user(db, "o'brien", "o@x.org")
    assert find_user(db, "o'brien") == ("o'brien", "o@x.org")
    add_user(db, "eve', 'evil'); drop table users; --", "e@x.org")
    assert find_user(db, "ann") == ("ann", "ann@x.org")

def test_no_string_built_sql():
    src = (pathlib.Path(__file__).resolve().parent.parent / "users.py").read_text()
    assert "f\"select" not in src and "f\"insert" not in src
