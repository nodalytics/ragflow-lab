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
