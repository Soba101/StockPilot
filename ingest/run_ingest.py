"""Wrapper so `python ingest/run_ingest.py data/` works.

Ensures project root is on sys.path so `rag` package is importable.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from rag.ingest.run_ingest import main as inner_main  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"Failed to import ingestion module: {e}")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest/run_ingest.py <data_dir>")
        sys.exit(1)
    data_dir = sys.argv[1]
    if not Path(data_dir).exists():
        print(f"Data dir not found: {data_dir}")
        sys.exit(1)
    inner_main(data_dir)
