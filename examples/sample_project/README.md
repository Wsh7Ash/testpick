# sample_project

A tiny src-layout project used to demonstrate testpick.

- `src/shop/pricing.py` - price helpers (imported by `shop.report`)
- `src/shop/report.py` - imports `shop.pricing`, giving the transitive case
  `test_report -> shop.report -> shop.pricing`
- `src/shop/inventory.py` - independent of pricing
- `src/shop/utils.py` - not imported by any test (fallback name-match demo)
- `src/shop/shipping.py` - no test exists for this module
- `tests/test_pricing.py`, `tests/test_report.py`, `tests/test_inventory.py`
  - import shop code
- `tests/test_utils.py` - intentionally unrelated (imports nothing from shop)
- `README.md` - a non-Python file

Run the suite from this directory (PowerShell):

    $env:PYTHONPATH = "src"
    python -m unittest discover -s tests -t .

Or pick tests for a change, from the testpick repository root:

    $env:PYTHONPATH = "src"
    python -m testpick examples\sample_project --changed src\shop\pricing.py --explain
