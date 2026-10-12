import unittest

from shop.pricing import apply_discount, price_with_tax


class PricingTests(unittest.TestCase):
    def test_price_with_tax(self):
        self.assertEqual(price_with_tax(10.0), 12.0)

    def test_price_with_tax_custom_rate(self):
        self.assertEqual(price_with_tax(10.0, 0.5), 15.0)

    def test_apply_discount(self):
        self.assertEqual(apply_discount(50.0, 10), 45.0)


if __name__ == "__main__":
    unittest.main()
