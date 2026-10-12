"""Price helpers for the sample shop."""

DEFAULT_TAX_RATE = 0.2


def price_with_tax(base_price, rate=DEFAULT_TAX_RATE):
    return round(base_price * (1 + rate), 2)


def apply_discount(price, percent):
    return round(price * (1 - percent / 100.0), 2)
