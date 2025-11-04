import os
import sys

"""Ignore RL tests on non-linux platform."""
collect_ignore = []

if sys.platform != "linux":
    for root, dirs, files in os.walk("rl"):
        for file in files:
            collect_ignore.append(os.path.join(root, file))

# Prepend the tests vendor directory so imports like "import ccxtpro" resolve
# to tests/_vendor/ccxtpro during pytest runs. This is test-only and does not
# affect production execution.
_here = os.path.dirname(__file__)
_vendor_dir = os.path.join(_here, "_vendor")
if _vendor_dir not in sys.path:
    sys.path.insert(0, _vendor_dir)
