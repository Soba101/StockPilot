# Wrapper script so command `python ingest/run_ingest.py data/` works per acceptance criteria.
from pathlib import Path
import sys

from rag.ingest.run_ingest import main as inner_main  # type: ignore

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest/run_ingest.py <data_dir>")
        sys.exit(1)
    data_dir = sys.argv[1]
    if not Path(data_dir).exists():
        print(f"Data dir not found: {data_dir}")
        sys.exit(1)
    inner_main(data_dir)
