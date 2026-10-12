import unittest

from shop import inventory


class InventoryTests(unittest.TestCase):
    ITEMS = [{"name": "apple", "qty": 3}, {"name": "pear", "qty": 0}]

    def test_in_stock(self):
        self.assertTrue(inventory.in_stock(self.ITEMS, "apple"))
        self.assertFalse(inventory.in_stock(self.ITEMS, "pear"))

    def test_total_quantity(self):
        self.assertEqual(inventory.total_quantity(self.ITEMS), 3)


if __name__ == "__main__":
    unittest.main()
