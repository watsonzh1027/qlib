## Problem
Tests failed during collection with:
```
ImportError: cannot import name 'OkxDataCollector' from 'scripts.okx_data_collector'
```
The module exists but the requested symbol does not.

## Fix (one error)
- Import the module object instead of a non-existent symbol:
  - Add `sys.path.insert(0, '..')` to ensure project root is on PYTHONPATH.
  - Use `import scripts.okx_data_collector as okx_data_collector`.

## Steps taken
1. Updated `tests/test_collector.py` to import the module object.
2. Confirmed this resolves the import error so pytest can proceed to collection.

Next step (after user confirmation)
- If tests now raise NameError or AttributeError when referencing `OkxDataCollector`, inspect `scripts/okx_data_collector.py` to determine the correct exported class/function name and update tests accordingly. Follow the ONE ERROR AT A TIME rule: wait for confirmation before addressing the next error.
