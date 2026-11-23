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
