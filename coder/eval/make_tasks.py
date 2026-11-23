"""Write the coding tasks for the model comparison into tasks/<name>/:
  prompt.txt   what the agent is asked, as a user would ask it
  repo/        the starting repository (the agent works in a copy)
  hidden/      tests copied in only after the agent finishes: the grade
  solution/    files that solve the task, overlaid on repo/ to prove the hidden tests can pass (the positive control)
Run: python3 make_tasks.py   (rewrites tasks/)
"""

import os
import shutil
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tasks")

T = {}


def task(name, prompt, repo, hidden, solution):
    T[name] = (prompt, repo, hidden, solution)


# 1. A bug fix: pagination returns the wrong slice
task(
    "fix-pagination",
    "The paginate() function in pager.py returns the wrong items: page 1 should be the first page. Fix it.",
    {
        "pager.py": '''
            def paginate(items, page, per_page):
                """Return the items on page `page` (1-based), `per_page` a page. Pages past the end are empty.
                page < 1 or per_page < 1 raises ValueError."""
                start = page * per_page
                return items[start:start + per_page]
        ''',
    },
    {
        "test_pager.py": '''
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
        ''',
    },
    {
        "pager.py": '''
            def paginate(items, page, per_page):
                if page < 1 or per_page < 1:
                    raise ValueError("page and per_page must be at least 1")
                start = (page - 1) * per_page
                return items[start:start + per_page]
        ''',
    },
)

# 2. A new class to a spec: an LRU cache
task(
    "lru-cache",
    "Implement the LRUCache class in cache.py as its docstring describes. get and put must be O(1).",
    {
        "cache.py": '''
            class LRUCache:
                """A least-recently-used cache holding at most `capacity` items (capacity >= 1, else ValueError).
                get(key) returns the value, or None if absent, and marks the key as most recently used.
                put(key, value) inserts or updates the key, marks it most recently used, and evicts the least
                recently used key when the cache is over capacity. len(cache) is the number of items."""

                def __init__(self, capacity):
                    raise NotImplementedError

                def get(self, key):
                    raise NotImplementedError

                def put(self, key, value):
                    raise NotImplementedError
        ''',
    },
    {
        "test_cache.py": '''
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
        ''',
    },
    {
        "cache.py": '''
            from collections import OrderedDict

            class LRUCache:
                def __init__(self, capacity):
                    if capacity < 1:
                        raise ValueError("capacity must be at least 1")
                    self.capacity = capacity
                    self.d = OrderedDict()

                def get(self, key):
                    if key not in self.d:
                        return None
                    self.d.move_to_end(key)
                    return self.d[key]

                def put(self, key, value):
                    self.d[key] = value
                    self.d.move_to_end(key)
                    if len(self.d) > self.capacity:
                        self.d.popitem(last=False)

                def __len__(self):
                    return len(self.d)
        ''',
    },
)

# 3. A rename across several modules, with a deprecated alias
task(
    "rename-across-files",
    "Rename calc_total to compute_total everywhere in this project. Keep calc_total working as a deprecated alias that "
    "emits a DeprecationWarning and returns the same result.",
    {
        "shop/__init__.py": "",
        "shop/pricing.py": '''
            def calc_total(prices, tax_rate=0.0):
                """The sum of prices plus tax, rounded to cents."""
                return round(sum(prices) * (1 + tax_rate), 2)
        ''',
        "shop/cart.py": '''
            from shop.pricing import calc_total

            class Cart:
                def __init__(self):
                    self.prices = []

                def add(self, price):
                    self.prices.append(price)

                def total(self, tax_rate=0.0):
                    return calc_total(self.prices, tax_rate)
        ''',
        "shop/invoice.py": '''
            from shop import pricing

            def invoice_line(prices, tax_rate):
                return f"TOTAL {pricing.calc_total(prices, tax_rate):.2f}"
        ''',
    },
    {
        "test_rename.py": '''
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
        ''',
    },
    {
        "shop/pricing.py": '''
            import warnings

            def compute_total(prices, tax_rate=0.0):
                return round(sum(prices) * (1 + tax_rate), 2)

            def calc_total(prices, tax_rate=0.0):
                warnings.warn("calc_total is deprecated; use compute_total", DeprecationWarning, stacklevel=2)
                return compute_total(prices, tax_rate)
        ''',
        "shop/cart.py": '''
            from shop.pricing import compute_total

            class Cart:
                def __init__(self):
                    self.prices = []

                def add(self, price):
                    self.prices.append(price)

                def total(self, tax_rate=0.0):
                    return compute_total(self.prices, tax_rate)
        ''',
        "shop/invoice.py": '''
            from shop import pricing

            def invoice_line(prices, tax_rate):
                return f"TOTAL {pricing.compute_total(prices, tax_rate):.2f}"
        ''',
    },
)

# 4. A parser from a short spec, with error handling
task(
    "iso-duration",
    "Implement parse_duration in duration.py: it takes an ISO 8601 duration like P3DT4H5M or PT90S or P1W and returns "
    "the total number of seconds as an int. Support W, D, H, M (minutes, after T) and S. Raise ValueError for anything "
    "invalid, such as an empty string, a missing P, a T with nothing after it, or units out of order.",
    {"duration.py": "def parse_duration(s):\n    raise NotImplementedError\n"},
    {
        "test_duration.py": '''
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
        ''',
    },
    {
        "duration.py": '''
            import re

            _RX = re.compile(r"P(?:(\\d+)W)?(?:(\\d+)D)?(?:T(?:(\\d+)H)?(?:(\\d+)M)?(?:(\\d+)S)?)?")

            def parse_duration(s):
                m = _RX.fullmatch(s)
                if not m or s == "P" or s.endswith("T") or not any(m.groups()):
                    raise ValueError(f"invalid duration: {s!r}")
                w, d, h, mi, sec = (int(g) if g else 0 for g in m.groups())
                return w * 604800 + d * 86400 + h * 3600 + mi * 60 + sec
        ''',
    },
)

# 5. Make a failing test pass by fixing the code, not the test
task(
    "fix-timezone-bug",
    "The test in tests/test_report.py fails. Find out why and fix the code (not the test).",
    {
        "report.py": '''
            from datetime import datetime, timezone

            def day_of(ts):
                """The UTC calendar day (YYYY-MM-DD) of a Unix timestamp in seconds."""
                return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

            def daily_counts(timestamps):
                """How many timestamps fall on each UTC day: {day: count}, days in order."""
                out = {}
                for ts in sorted(timestamps):
                    d = day_of(ts)
                    out[d] = out.get(d, 0) + 1
                return out
        ''',
        "tests/test_report.py": '''
            import os, time
            os.environ["TZ"] = "America/New_York"
            time.tzset()
            from report import daily_counts

            def test_counts_by_utc_day():
                # 2026-01-01 23:30 UTC and 2026-01-02 00:30 UTC
                assert daily_counts([1767310200, 1767313800]) == {"2026-01-01": 1, "2026-01-02": 1}
        ''',
    },
    {
        "test_report_hidden.py": '''
            import os, time
            os.environ["TZ"] = "Asia/Tokyo"
            time.tzset()
            from report import daily_counts, day_of

            def test_counts_by_utc_day_any_local_zone():
                assert daily_counts([1767310200, 1767313800]) == {"2026-01-01": 1, "2026-01-02": 1}

            def test_day_of_is_utc():
                assert day_of(0) == "1970-01-01"
        ''',
    },
    {
        "report.py": '''
            from datetime import datetime, timezone

            def day_of(ts):
                return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

            def daily_counts(timestamps):
                out = {}
                for ts in sorted(timestamps):
                    d = day_of(ts)
                    out[d] = out.get(d, 0) + 1
                return out
        ''',
    },
)

# 6. A feature in a command-line tool
task(
    "cli-json-flag",
    "Add a --json flag to wc.py: with it, print a JSON object {\"lines\": L, \"words\": W, \"chars\": C} instead of the "
    "plain text output. Without it, the output must not change.",
    {
        "wc.py": '''
            import argparse, sys

            def counts(text):
                return len(text.splitlines()), len(text.split()), len(text)

            def main(argv=None):
                ap = argparse.ArgumentParser()
                ap.add_argument("file")
                a = ap.parse_args(argv)
                text = open(a.file).read()
                lines, words, chars = counts(text)
                print(f"{lines} {words} {chars} {a.file}")

            if __name__ == "__main__":
                sys.exit(main())
        ''',
    },
    {
        "test_wc.py": '''
            import json, pathlib, subprocess, sys
            WC = pathlib.Path(__file__).resolve().parent.parent / "wc.py"

            def run(*args, tmp):
                f = tmp / "t.txt"
                f.write_text("hello world\\nsecond line here\\n")
                return subprocess.run([sys.executable, str(WC), *args, str(f)], capture_output=True, text=True, check=True).stdout, f

            def test_plain_unchanged(tmp_path):
                out, f = run(tmp=tmp_path)
                assert out == f"2 5 29 {f}\\n"

            def test_json(tmp_path):
                out, _ = run("--json", tmp=tmp_path)
                assert json.loads(out) == {"lines": 2, "words": 5, "chars": 29}
        ''',
    },
    {
        "wc.py": '''
            import argparse, json, sys

            def counts(text):
                return len(text.splitlines()), len(text.split()), len(text)

            def main(argv=None):
                ap = argparse.ArgumentParser()
                ap.add_argument("file")
                ap.add_argument("--json", action="store_true")
                a = ap.parse_args(argv)
                text = open(a.file).read()
                lines, words, chars = counts(text)
                if a.json:
                    print(json.dumps({"lines": lines, "words": words, "chars": chars}))
                else:
                    print(f"{lines} {words} {chars} {a.file}")

            if __name__ == "__main__":
                sys.exit(main())
        ''',
    },
)

# 7. A security fix: SQL injection
task(
    "sql-injection",
    "users.py builds SQL by pasting user input into the query string. Fix it so it is safe against SQL injection, "
    "keeping the same behaviour for normal input.",
    {
        "users.py": '''
            import sqlite3

            def connect():
                db = sqlite3.connect(":memory:")
                db.execute("create table users (name text, email text)")
                db.executemany("insert into users values (?, ?)", [("ann", "ann@x.org"), ("bob", "bob@x.org")])
                return db

            def find_user(db, name):
                row = db.execute(f"select name, email from users where name = '{name}'").fetchone()
                return row

            def add_user(db, name, email):
                db.execute(f"insert into users values ('{name}', '{email}')")
        ''',
    },
    {
        "test_users.py": '''
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
                assert "f\\"select" not in src and "f\\"insert" not in src
        ''',
    },
    {
        "users.py": '''
            import sqlite3

            def connect():
                db = sqlite3.connect(":memory:")
                db.execute("create table users (name text, email text)")
                db.executemany("insert into users values (?, ?)", [("ann", "ann@x.org"), ("bob", "bob@x.org")])
                return db

            def find_user(db, name):
                return db.execute("select name, email from users where name = ?", (name,)).fetchone()

            def add_user(db, name, email):
                db.execute("insert into users values (?, ?)", (name, email))
        ''',
    },
)

# 8. Implement to a written spec in the README
task(
    "config-merge",
    "Implement load_config in config.py following the rules in README.md.",
    {
        "README.md": '''
            # Config

            `load_config(defaults, file_values, env)` returns the effective configuration:

            1. Start from `defaults`, then apply `file_values`, then the environment `env` (a dict like os.environ).
               Later sources win.
            2. Nested dicts are merged key by key, not replaced. Lists and other values are replaced.
            3. Only environment variables starting with `APP_` count. `APP_DB__HOST=x` sets `["db"]["host"] = "x"`:
               a double underscore is one level of nesting, names are lowercased.
            4. An environment value is converted to the type of the value it overrides when that is an int, float or
               bool (`"true"`/`"false"`, any case); a value that cannot be converted raises ValueError.
            5. The inputs are never modified.
        ''',
        "config.py": "def load_config(defaults, file_values, env):\n    raise NotImplementedError\n",
    },
    {
        "test_config.py": '''
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
        ''',
    },
    {
        "config.py": '''
            import copy

            def _merge(a, b):
                out = copy.deepcopy(a)
                for k, v in b.items():
                    if isinstance(v, dict) and isinstance(out.get(k), dict):
                        out[k] = _merge(out[k], v)
                    else:
                        out[k] = copy.deepcopy(v)
                return out

            def _convert(raw, old):
                if isinstance(old, bool):
                    if raw.lower() in ("true", "false"):
                        return raw.lower() == "true"
                    raise ValueError(raw)
                if isinstance(old, int):
                    return int(raw)
                if isinstance(old, float):
                    return float(raw)
                return raw

            def load_config(defaults, file_values, env):
                c = _merge(defaults, file_values)
                for k, raw in env.items():
                    if not k.startswith("APP_"):
                        continue
                    path = k[4:].lower().split("__")
                    node = c
                    for p in path[:-1]:
                        node = node.setdefault(p, {})
                    node[path[-1]] = _convert(raw, node.get(path[-1]))
                return c
        ''',
    },
)

# 9. A performance fix
task(
    "speed-up-duplicates",
    "find_duplicates in dupes.py is far too slow on large inputs. Make it fast without changing what it returns.",
    {
        "dupes.py": '''
            def find_duplicates(items):
                """The values that appear more than once, in the order their second occurrence appears."""
                out = []
                for i, x in enumerate(items):
                    if x in items[:i] and x not in out:
                        out.append(x)
                return out
        ''',
    },
    {
        "test_dupes.py": '''
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
        ''',
    },
    {
        "dupes.py": '''
            def find_duplicates(items):
                seen, out, reported = set(), [], set()
                for x in items:
                    if x in seen and x not in reported:
                        out.append(x)
                        reported.add(x)
                    seen.add(x)
                return out
        ''',
    },
)

# 10. A bug that needs reading two files: an inventory that breaks its own rules
task(
    "inventory-rules",
    "inventory.py does not follow the rules in RULES.md. Fix the code so it does.",
    {
        "RULES.md": '''
            # Inventory rules

            - Quantities are whole numbers; adding or removing a quantity of zero or less raises ValueError.
            - Removing more than is in stock raises InsufficientStock (defined in inventory.py) and changes nothing.
            - Removing an item that was never added raises KeyError.
            - An item whose stock reaches zero is removed from the inventory entirely.
            - `total_value(prices)` is the sum of stock times price over all items; an item missing from `prices`
              raises KeyError.
        ''',
        "inventory.py": '''
            class InsufficientStock(Exception):
                pass

            class Inventory:
                def __init__(self):
                    self.stock = {}

                def add(self, item, qty):
                    self.stock[item] = self.stock.get(item, 0) + qty

                def remove(self, item, qty):
                    self.stock[item] = self.stock.get(item, 0) - qty

                def total_value(self, prices):
                    return sum(q * prices.get(i, 0) for i, q in self.stock.items())
        ''',
    },
    {
        "test_inventory.py": '''
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
        ''',
    },
    {
        "inventory.py": '''
            class InsufficientStock(Exception):
                pass

            class Inventory:
                def __init__(self):
                    self.stock = {}

                def add(self, item, qty):
                    if qty <= 0:
                        raise ValueError("quantity must be positive")
                    self.stock[item] = self.stock.get(item, 0) + qty

                def remove(self, item, qty):
                    if qty <= 0:
                        raise ValueError("quantity must be positive")
                    if item not in self.stock:
                        raise KeyError(item)
                    if qty > self.stock[item]:
                        raise InsufficientStock(item)
                    self.stock[item] -= qty
                    if self.stock[item] == 0:
                        del self.stock[item]

                def total_value(self, prices):
                    return sum(q * prices[i] for i, q in self.stock.items())
        ''',
    },
)


def write(base, files):
    for rel, body in files.items():
        p = os.path.join(base, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(textwrap.dedent(body).lstrip("\n"))


if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    for name, (prompt, repo, hidden, solution) in T.items():
        d = os.path.join(OUT, name)
        write(os.path.join(d, "repo"), repo)
        write(os.path.join(d, "hidden"), hidden)
        write(os.path.join(d, "solution"), solution)
        with open(os.path.join(d, "prompt.txt"), "w") as f:
            f.write(prompt + "\n")
    print(f"{len(T)} tasks in {OUT}")
