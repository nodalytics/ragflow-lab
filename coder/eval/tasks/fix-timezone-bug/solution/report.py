from datetime import datetime, timezone

def day_of(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

def daily_counts(timestamps):
    out = {}
    for ts in sorted(timestamps):
        d = day_of(ts)
        out[d] = out.get(d, 0) + 1
    return out
