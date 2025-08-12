import os
import sys
import hashlib
from pathlib import Path
from typing import List, Tuple
import uuid

from rag.load_env import load as load_env
load_env()

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

CHUNK_SIZE = int(os.getenv("INGEST_CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.getenv("INGEST_CHUNK_OVERLAP", 120))
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "BAAI/bge-small-en-v1.5")
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./rag/vector_store")
COLLECTION_NAME = "documents"

SUPPORTED_EXT = {".md", ".txt", ".pdf", ".csv"}

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
    

def load_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        if PdfReader is None:
            raise RuntimeError("pypdf not installed: pip install pypdf")
        reader = PdfReader(str(path))
        text = []
        for page in reader.pages:
            text.append(page.extract_text() or "")
        return "\n".join(text)
    else:
        return path.read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str) -> List[Tuple[str, int, int]]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_SIZE)
        chunk = text[start:end]
        # approximate line numbers by counting newlines
        line_start = text[:start].count("\n") + 1
        line_end = line_start + chunk.count("\n")
        chunks.append((chunk, line_start, line_end))
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


def main(data_dir: str):
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"Data dir not found: {data_dir}")
        sys.exit(1)
    client = chromadb.Client(Settings(persist_directory=CHROMA_DB_DIR))
    collection = client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    model = SentenceTransformer(EMBEDDINGS_MODEL)

    docs_added = 0
    for file_path in data_path.rglob('*'):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXT:
            continue
        try:
            raw = load_file(file_path)
        except Exception as e:
            print(f"Skip {file_path}: {e}")
            continue
        chunks = chunk_text(raw)
        embeddings = model.encode([c[0] for c in chunks], normalize_embeddings=True)
        ids = []
        metadatas = []
        documents = []
        for i, ((chunk, ls, le), emb) in enumerate(zip(chunks, embeddings)):
            h = hashlib.sha256(f"{file_path}:{i}:{len(chunk)}".encode()).hexdigest()[:24]
            ids.append(h)
            metadatas.append({
                "filename": file_path.name,
                "path": str(file_path),
                "line_start": ls,
                "line_end": le,
            })
            documents.append(chunk)
        collection.upsert(ids=ids, embeddings=embeddings.tolist(), metadatas=metadatas, documents=documents)
        docs_added += len(ids)
        print(f"Indexed {file_path} -> {len(ids)} chunks")

    client.persist()
    print(f"Done. Total chunks: {docs_added}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest/run_ingest.py <data_dir>")
        sys.exit(1)
    main(sys.argv[1])
