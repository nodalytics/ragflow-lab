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
