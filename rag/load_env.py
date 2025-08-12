from pathlib import Path
from dotenv import load_dotenv

def load():
    # Load project root .env if exists
    for candidate in [Path('.env'), Path('rag/.env')]:
        if candidate.exists():
            load_dotenv(candidate)
