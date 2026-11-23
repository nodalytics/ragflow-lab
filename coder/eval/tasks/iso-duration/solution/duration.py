import re

_RX = re.compile(r"P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?")

def parse_duration(s):
    m = _RX.fullmatch(s)
    if not m or s == "P" or s.endswith("T") or not any(m.groups()):
        raise ValueError(f"invalid duration: {s!r}")
    w, d, h, mi, sec = (int(g) if g else 0 for g in m.groups())
    return w * 604800 + d * 86400 + h * 3600 + mi * 60 + sec
