"""Receipt rendering; depends on pricing (the transitive-selection demo)."""

from shop import pricing


def receipt_line(name, unit_price, qty, rate=0.2):
    total = pricing.price_with_tax(unit_price, rate) * qty
    return f"{name} x{qty} = {total:.2f}"
