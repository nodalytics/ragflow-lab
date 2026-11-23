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
