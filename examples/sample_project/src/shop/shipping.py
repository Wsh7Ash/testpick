"""Shipping cost helper with no corresponding test file."""


def shipping_cost(weight_kg, zone="domestic"):
    base = 5.0 if zone == "domestic" else 12.5
    return round(base + weight_kg * 1.25, 2)
