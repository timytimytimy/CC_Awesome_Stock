import sys
from pathlib import Path


DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
if str(DATA_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_ROOT))
