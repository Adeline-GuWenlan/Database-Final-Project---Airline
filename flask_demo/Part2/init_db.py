from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from init_db import init_database  # noqa: E402


if __name__ == "__main__":
    init_database()
