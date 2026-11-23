"""The harder tier of coding tasks (hard-*), added to tasks/ beside make_tasks.py's: every model passed nearly all of
the first ten, so these separate them. Same layout: prompt.txt, repo/, hidden/ (the grade), solution/ (the proof).
Run: python3 make_hard_tasks.py   (writes only tasks/hard-*)
"""

import os
import shutil

from make_tasks import OUT, write

H = {}


def task(name, prompt, repo, hidden, solution):
    H["hard-" + name] = (prompt, repo, hidden, solution)


task(
    "cron",
    "Implement next_run in cron.py as its docstring describes.",
    {
        "cron.py": '''
            from datetime import datetime


            def next_run(expr, after):
                """The first time strictly after `after` (a naive datetime) that matches the cron expression `expr`.

                `expr` has five space-separated fields: minute (0-59), hour (0-23), day of month (1-31), month (1-12) and
                day of week (0-7, where 0 and 7 are both Sunday). Each field is `*`, a number, a range `a-b`, a step
                `*/n` or `a-b/n`, or a comma-separated list of these. As in standard cron, when both day of month and
                day of week are restricted (neither is `*`), a day matches if either matches.
                The result has seconds and microseconds of zero. Anything invalid (a wrong number of fields, a value
                out of range, a step of 0, text that is not a number) raises ValueError.
                """
                raise NotImplementedError
        ''',
    },
    {
        "test_cron.py": '''
            from datetime import datetime as D
            import pytest
            from cron import next_run

            def test_working_hours_skip_the_weekend():
                assert next_run("*/15 9-17 * * 1-5", D(2026, 1, 2, 17, 50)) == D(2026, 1, 5, 9, 0)

            def test_strictly_after_and_seconds():
                assert next_run("5,10 * * * *", D(2026, 1, 1, 10, 10, 30)) == D(2026, 1, 1, 11, 5)
                assert next_run("* * * * *", D(2026, 1, 1, 10, 10)) == D(2026, 1, 1, 10, 11)

            def test_month_rollover_and_leap_day():
                assert next_run("0 0 1 * *", D(2026, 1, 31, 12, 0)) == D(2026, 2, 1, 0, 0)
                assert next_run("30 2 29 2 *", D(2026, 3, 1)) == D(2028, 2, 29, 2, 30)

            def test_day_of_month_or_day_of_week():
                assert next_run("0 12 1 * 1", D(2026, 1, 1, 12, 0)) == D(2026, 1, 5, 12, 0)

            def test_sunday_is_0_and_7():
                assert next_run("0 0 * * 7", D(2026, 1, 1)) == D(2026, 1, 4)
                assert next_run("0 0 * * 0", D(2026, 1, 1)) == D(2026, 1, 4)

            def test_ranges_with_steps_and_lists():
                assert next_run("0 8-18/5 * * *", D(2026, 1, 1, 13, 1)) == D(2026, 1, 1, 18, 0)
                assert next_run("0 0 * 3,6 *", D(2026, 1, 1)) == D(2026, 3, 1)

            @pytest.mark.parametrize("bad", ["60 * * * *", "* * *", "*/0 * * * *", "a * * * *", "* 24 * * *", "* * 0 * *",
                                             "* * * 13 *", "* * * * 8", "5-1 * * * *"])
            def test_invalid(bad):
                with pytest.raises(ValueError):
                    next_run(bad, D(2026, 1, 1))
        ''',
    },
    {
        "cron.py": '''
            from datetime import datetime, timedelta

            RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]


            def _field(text, lo, hi):
                out = set()
                for part in text.split(","):
                    rng, _, step = part.partition("/")
                    step = int(step) if step else 1
                    if step < 1:
                        raise ValueError("step must be positive")
                    if rng == "*":
                        a, b = lo, hi
                    elif "-" in rng:
                        a, b = (int(x) for x in rng.split("-"))
                    else:
                        a = b = int(rng)
                    if not (lo <= a <= b <= hi):
                        raise ValueError(f"out of range: {part}")
                    out.update(range(a, b + 1, step))
                return out


            def next_run(expr, after):
                f = expr.split()
                if len(f) != 5:
                    raise ValueError("five fields expected")
                mins, hours, doms, months, dows = (_field(t, lo, hi) for t, (lo, hi) in zip(f, RANGES))
                if 7 in dows:
                    dows.add(0)
                both = f[2] != "*" and f[4] != "*"
                t = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
                day = t.date()
                for _ in range(366 * 8):
                    dow = (day.weekday() + 1) % 7
                    dm, ww = day.day in doms, dow in dows
                    if day.month in months and ((dm or ww) if both else (dm and ww)):
                        for h in sorted(hours):
                            for m in sorted(mins):
                                c = datetime(day.year, day.month, day.day, h, m)
                                if c >= t:
                                    return c
                    day += timedelta(days=1)
                raise ValueError("no matching time")
        ''',
    },
)

task(
    "split-money",
    "Implement split in money.py as its docstring describes.",
    {
        "money.py": '''
            from decimal import Decimal


            def split(total, weights):
                """Split an amount of money into parts proportional to `weights`, in whole cents, so that the parts add
                up to exactly `total`.

                `total` is a string or Decimal with at most two decimal places (more raises ValueError); `weights` are
                non-negative numbers with a positive sum (otherwise ValueError). Each part is first its exact share
                rounded down to the cent; the cents left over go one each to the parts with the largest remainders,
                earlier parts first when remainders tie. A negative total is split as its absolute value and every part
                negated. Returns a list of Decimals with two decimal places.
                """
                raise NotImplementedError
        ''',
    },
    {
        "test_money.py": '''
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
        ''',
    },
    {
        "money.py": '''
            from decimal import ROUND_FLOOR, Decimal

            CENT = Decimal("0.01")


            def split(total, weights):
                total = Decimal(str(total))
                if total != total.quantize(CENT):
                    raise ValueError("at most two decimal places")
                w = [Decimal(str(x)) for x in weights]
                if not w or any(x < 0 for x in w) or sum(w) <= 0:
                    raise ValueError("weights must be non-negative with a positive sum")
                sign = -1 if total < 0 else 1
                amount = abs(total)
                exact = [amount * x / sum(w) for x in w]
                parts = [e.quantize(CENT, rounding=ROUND_FLOOR) for e in exact]
                left = int((amount - sum(parts)) / CENT)
                order = sorted(range(len(w)), key=lambda i: (-(exact[i] - parts[i]), i))
                for i in order[:left]:
                    parts[i] += CENT
                return [(p * sign).quantize(CENT) for p in parts]
        ''',
    },
)

task(
    "dependency-order",
    "Implement order() in deps.py as its docstring describes.",
    {
        "deps.py": '''
            class CycleError(Exception):
                def __init__(self, cycle):
                    super().__init__(" -> ".join(cycle))
                    self.cycle = cycle


            def order(deps):
                """An install order for packages: `deps` maps each package to the packages it depends on, and every
                package must come after all of its dependencies. A dependency that is not a key is a package with no
                dependencies of its own, and is included. Among the valid orders, return the one that is
                alphabetically smallest (at each step, the alphabetically first package that is ready).

                If the dependencies contain a cycle, raise CycleError(cycle) where `cycle` is a list of packages
                tracing one cycle, starting and ending with the same package, e.g. ["a", "b", "c", "a"] when a depends
                on b, b on c and c on a, and starting at the alphabetically first package of that cycle.
                """
                raise NotImplementedError
        ''',
    },
    {
        "test_deps.py": '''
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
        ''',
    },
    {
        "deps.py": '''
            import heapq


            class CycleError(Exception):
                def __init__(self, cycle):
                    super().__init__(" -> ".join(cycle))
                    self.cycle = cycle


            def _find_cycle(deps):
                state, stack = {}, []

                def visit(u):
                    state[u] = 1
                    stack.append(u)
                    for v in sorted(deps.get(u, [])):
                        if state.get(v) == 1:
                            cyc = stack[stack.index(v):]
                            i = cyc.index(min(cyc))
                            cyc = cyc[i:] + cyc[:i]
                            return cyc + [cyc[0]]
                        if not state.get(v):
                            found = visit(v)
                            if found:
                                return found
                    stack.pop()
                    state[u] = 2
                    return None

                for u in sorted(deps):
                    if not state.get(u):
                        found = visit(u)
                        if found:
                            return found
                return None


            def order(deps):
                nodes = set(deps) | {d for ds in deps.values() for d in ds}
                need = {n: set(deps.get(n, [])) for n in nodes}
                users = {n: set() for n in nodes}
                for n, ds in need.items():
                    for d in ds:
                        users[d].add(n)
                ready = [n for n in nodes if not need[n]]
                heapq.heapify(ready)
                out = []
                while ready:
                    n = heapq.heappop(ready)
                    out.append(n)
                    for u in users[n]:
                        need[u].discard(n)
                        if not need[u]:
                            heapq.heappush(ready, u)
                if len(out) != len(nodes):
                    raise CycleError(_find_cycle(deps))
                return out
        ''',
    },
)

task(
    "async-retry",
    "Implement retry() in retry.py as its docstring describes.",
    {
        "retry.py": '''
            import asyncio
            import time


            async def retry(fn, *, attempts, base_delay, max_delay, deadline, retry_on=(Exception,), sleep=asyncio.sleep,
                            clock=time.monotonic):
                """Call `await fn()` until it succeeds, and return its result.

                - At most `attempts` calls in all (attempts < 1 raises ValueError).
                - An exception that is an instance of `retry_on` is retried; any other exception propagates at once.
                - asyncio.CancelledError always propagates at once and is never retried, even when `retry_on` would match.
                - Before the k-th retry (k = 0, 1, ...) wait min(max_delay, base_delay * 2**k) seconds with `sleep`.
                - `deadline` is a total budget in seconds, measured with `clock` from the start of retry(): if waiting
                  before the next attempt would end past the deadline, do not wait; raise the last exception instead.
                - When the attempts run out, raise the last exception.
                """
                raise NotImplementedError
        ''',
    },
    {
        "test_retry.py": '''
            import asyncio
            import pytest
            from retry import retry

            class Fake:
                def __init__(self):
                    self.t, self.sleeps = 0.0, []
                def clock(self):
                    return self.t
                async def sleep(self, d):
                    self.sleeps.append(d)
                    self.t += d

            def failing(n_fail, exc=RuntimeError, result=7):
                calls = []
                async def fn():
                    calls.append(1)
                    if len(calls) <= n_fail:
                        raise exc(f"fail {len(calls)}")
                    return result
                return fn, calls

            def run(coro):
                return asyncio.run(coro)

            def test_succeeds_on_the_third_call():
                f, (fn, calls) = Fake(), failing(2)
                assert run(retry(fn, attempts=5, base_delay=0.1, max_delay=10, deadline=100, sleep=f.sleep, clock=f.clock)) == 7
                assert f.sleeps == pytest.approx([0.1, 0.2]) and len(calls) == 3

            def test_delays_are_capped_and_the_last_error_raised():
                f, (fn, calls) = Fake(), failing(99)
                with pytest.raises(RuntimeError, match="fail 5"):
                    run(retry(fn, attempts=5, base_delay=1, max_delay=3, deadline=100, sleep=f.sleep, clock=f.clock))
                assert f.sleeps == [1, 2, 3, 3] and len(calls) == 5

            def test_other_errors_are_not_retried():
                f, (fn, calls) = Fake(), failing(99, exc=KeyError)
                with pytest.raises(KeyError):
                    run(retry(fn, attempts=5, base_delay=1, max_delay=3, deadline=100, retry_on=(ValueError,),
                              sleep=f.sleep, clock=f.clock))
                assert f.sleeps == [] and len(calls) == 1

            def test_deadline_stops_before_sleeping_past_it():
                f, (fn, calls) = Fake(), failing(99)
                with pytest.raises(RuntimeError, match="fail 2"):
                    run(retry(fn, attempts=10, base_delay=1, max_delay=60, deadline=2.5, sleep=f.sleep, clock=f.clock))
                assert f.sleeps == [1] and len(calls) == 2

            def test_cancellation_is_never_retried():
                f, (fn, calls) = Fake(), failing(99, exc=asyncio.CancelledError)
                with pytest.raises(asyncio.CancelledError):
                    run(retry(fn, attempts=5, base_delay=1, max_delay=3, deadline=100, retry_on=(BaseException,),
                              sleep=f.sleep, clock=f.clock))
                assert len(calls) == 1

            def test_attempts_must_be_positive():
                f, (fn, _) = Fake(), failing(0)
                with pytest.raises(ValueError):
                    run(retry(fn, attempts=0, base_delay=1, max_delay=3, deadline=10, sleep=f.sleep, clock=f.clock))
        ''',
    },
    {
        "retry.py": '''
            import asyncio
            import time


            async def retry(fn, *, attempts, base_delay, max_delay, deadline, retry_on=(Exception,), sleep=asyncio.sleep,
                            clock=time.monotonic):
                if attempts < 1:
                    raise ValueError("attempts must be at least 1")
                start = clock()
                for k in range(attempts):
                    try:
                        return await fn()
                    except asyncio.CancelledError:
                        raise
                    except BaseException as e:
                        if not isinstance(e, retry_on) or k == attempts - 1:
                            raise
                        delay = min(max_delay, base_delay * 2**k)
                        if clock() - start + delay > deadline:
                            raise
                        await sleep(delay)
        ''',
    },
)

task(
    "apply-patch",
    "Implement apply_patch in patch.py as its docstring describes.",
    {
        "patch.py": '''
            class PatchError(Exception):
                pass


            def apply_patch(text, patch):
                """Apply a unified diff for one file to `text` and return the new text.

                `patch` may start with `--- ` and `+++ ` header lines; then come hunks, each starting with
                `@@ -a,b +c,d @@` (`,b` and `,d` may be left out, meaning 1). Hunk lines start with a space (context),
                `-` (removed) or `+` (added). Context and removed lines must match the text exactly.
                A hunk normally applies at line a (1-based; with b = 0 it inserts after line a). If the text there
                does not match, look for the same old lines up to 10 lines earlier or later, the nearest offset first
                (earlier before later at equal distance), and keep that offset for later hunks. If no position
                matches, raise PatchError. Lines keep their own line endings; the text's last line may lack a newline.
                """
                raise NotImplementedError
        ''',
    },
    {
        "test_patch.py": '''
            import pytest
            from patch import apply_patch, PatchError

            TEXT = "".join(f"line {i}\\n" for i in range(1, 21))

            P1 = """--- a/f.txt
            +++ b/f.txt
            @@ -3,3 +3,3 @@
             line 3
            -line 4
            +line four
             line 5
            """.replace("            ", "")

            def test_one_hunk():
                assert apply_patch(TEXT, P1) == TEXT.replace("line 4\\n", "line four\\n")

            def test_two_hunks_add_and_remove():
                p = """@@ -1,2 +1,3 @@
             line 1
            +inserted
             line 2
            @@ -18,3 +19,2 @@
             line 18
            -line 19
             line 20
            """.replace("            ", "")
                out = apply_patch(TEXT, p).splitlines()
                assert out[:3] == ["line 1", "inserted", "line 2"] and "line 19" not in out and out[-1] == "line 20"

            def test_offset_when_lines_moved():
                shifted = "new a\\nnew b\\nnew c\\n" + TEXT
                assert apply_patch(shifted, P1) == shifted.replace("line 4\\n", "line four\\n")

            def test_short_header_and_insert_at_end():
                p = "@@ -20,0 +21 @@\\n+line 21\\n"
                assert apply_patch(TEXT, p) == TEXT + "line 21\\n"
                p2 = "@@ -5 +5 @@\\n-line 5\\n+LINE 5\\n"
                assert apply_patch(TEXT, p2) == TEXT.replace("line 5\\n", "LINE 5\\n")

            def test_mismatch_raises():
                bad = P1.replace(" line 5", " line 55")
                with pytest.raises(PatchError):
                    apply_patch(TEXT, bad)

            def test_too_far_raises():
                far = "".join(f"pad {i}\\n" for i in range(15)) + TEXT
                with pytest.raises(PatchError):
                    apply_patch(far, P1)

            def test_no_final_newline_kept():
                t = "a\\nb\\nc"
                assert apply_patch(t, "@@ -1,2 +1,2 @@\\n-a\\n+A\\n b\\n") == "A\\nb\\nc"
        ''',
    },
    {
        "patch.py": '''
            import re


            class PatchError(Exception):
                pass


            HUNK = re.compile(r"@@ -(\\d+)(?:,(\\d+))? \\+(\\d+)(?:,(\\d+))? @@")


            def _hunks(patch):
                hunks, cur = [], None
                for ln in patch.splitlines(keepends=True):
                    if ln.startswith(("--- ", "+++ ")) and cur is None:
                        continue
                    m = HUNK.match(ln)
                    if m:
                        cur = {"a": int(m.group(1)), "b": int(m.group(2) or 1), "lines": []}
                        hunks.append(cur)
                    elif cur is not None and ln[:1] in (" ", "-", "+"):
                        body = ln[1:]
                        cur["lines"].append((ln[0], body if body.endswith("\\n") else body + "\\n"))
                return hunks


            def apply_patch(text, patch):
                lines = text.splitlines(keepends=True)
                no_final = bool(lines) and not lines[-1].endswith("\\n")
                if no_final:
                    lines[-1] += "\\n"
                offset = 0
                for h in _hunks(patch):
                    old = [b for k, b in h["lines"] if k in (" ", "-")]
                    new = [b for k, b in h["lines"] if k in (" ", "+")]
                    start = h["a"] - 1 if h["b"] else h["a"]
                    for d in [0] + [x for k in range(1, 11) for x in (-k, k)]:
                        s = start + offset + d
                        if 0 <= s <= len(lines) - len(old) and lines[s:s + len(old)] == old:
                            lines[s:s + len(old)] = new
                            offset += d + len(new) - len(old)
                            break
                    else:
                        raise PatchError(f"hunk at line {h['a']} does not apply")
                out = "".join(lines)
                return out[:-1] if no_final and out.endswith("\\n") else out
        ''',
    },
)


if __name__ == "__main__":
    for name, (prompt, repo, hidden, solution) in H.items():
        d = os.path.join(OUT, name)
        shutil.rmtree(d, ignore_errors=True)
        write(os.path.join(d, "repo"), repo)
        write(os.path.join(d, "hidden"), hidden)
        write(os.path.join(d, "solution"), solution)
        with open(os.path.join(d, "prompt.txt"), "w") as f:
            f.write(prompt + "\n")
    print(f"{len(H)} hard tasks in {OUT}")
