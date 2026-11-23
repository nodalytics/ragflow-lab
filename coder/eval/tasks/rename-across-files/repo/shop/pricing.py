def calc_total(prices, tax_rate=0.0):
    """The sum of prices plus tax, rounded to cents."""
    return round(sum(prices) * (1 + tax_rate), 2)
