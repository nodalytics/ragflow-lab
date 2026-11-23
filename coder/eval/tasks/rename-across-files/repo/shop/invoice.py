from shop import pricing

def invoice_line(prices, tax_rate):
    return f"TOTAL {pricing.calc_total(prices, tax_rate):.2f}"
