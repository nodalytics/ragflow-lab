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
