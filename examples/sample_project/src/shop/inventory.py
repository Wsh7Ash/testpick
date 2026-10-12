"""Stock helpers; intentionally independent of pricing."""


def in_stock(items, name):
    return any(item["name"] == name and item["qty"] > 0 for item in items)


def total_quantity(items):
    return sum(item["qty"] for item in items)
