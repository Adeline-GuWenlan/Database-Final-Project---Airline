import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARED_INIT = ROOT / "init_db.py"


def load_init_database():
    spec = importlib.util.spec_from_file_location("airline_shared_init_db", SHARED_INIT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load database initializer from {SHARED_INIT}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.init_database


init_database = load_init_database()


if __name__ == "__main__":
    init_database()
