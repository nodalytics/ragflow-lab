import warnings

def compute_total(prices, tax_rate=0.0):
    return round(sum(prices) * (1 + tax_rate), 2)

def calc_total(prices, tax_rate=0.0):
    warnings.warn("calc_total is deprecated; use compute_total", DeprecationWarning, stacklevel=2)
    return compute_total(prices, tax_rate)
