import unittest

from shop.report import receipt_line


class ReportTests(unittest.TestCase):
    def test_receipt_line_uses_pricing(self):
        line = receipt_line("apple", 10.0, 2)
        self.assertIn("apple x2", line)
        self.assertIn("24.00", line)

    def test_receipt_line_rounding(self):
        line = receipt_line("pear", 3.33, 1, rate=0.0)
        self.assertIn("3.33", line)


if __name__ == "__main__":
    unittest.main()
