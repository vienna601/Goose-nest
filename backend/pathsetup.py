# pathsetup.py — put shared/ on the import path so `from schema import ...` works everywhere.
import sys, os
_shared = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shared"))
if _shared not in sys.path:
    sys.path.insert(0, _shared)