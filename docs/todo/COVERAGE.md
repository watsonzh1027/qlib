Why train_lgb.py may not show up in coverage

- Running pytest with `--cov=examples/train_lgb.py` passes a file path to coverage.
  Coverage maps measured modules by import name (package.module), so when you import `examples.train_lgb`
  the file-path form can fail to match and coverage reports "Module ... was never imported."

Recommended commands (run from repo root /home/watson/work/qlib):

- Measure the examples package (includes train_lgb):
  pytest tests/test_train_lgb.py -v --cov=examples --cov-report=term-missing

- Or specify the module name:
  pytest tests/test_train_lgb.py -v --cov=examples.train_lgb --cov-report=term-missing

Notes:
- Ensure `examples/__init__.py` exists so `examples` is a package (we added it).
- If you still see "module not imported", confirm tests import the module using the package path:
  `from examples.train_lgb import train_from_features` — that import must occur during the test run.
- CI: prefer `--cov=examples` to capture all example scripts in the package.
