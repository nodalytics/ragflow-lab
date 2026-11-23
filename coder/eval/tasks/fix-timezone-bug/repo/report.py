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
