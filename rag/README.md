# Local RAG Chat

Minimal local Retrieval Augmented Generation stack using FastAPI + Chroma + sentence-transformers + LM Studio.

## Features
- Local ingestion of MD/TXT/PDF/CSV into Chroma vector store
- bge-small (BAAI/bge-small-en-v1.5) embeddings
- OpenAI-compatible chat call to LM Studio model gpt-oss-20b
- Business rules automatically injected
- Citations with filename and line ranges
- Simple HTML UI listing sources and answer
- Deterministic (temperature=0.2) grounded responses

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r rag/requirements-rag.txt
```

## Ingest Documents
```bash
python rag/ingest/run_ingest.py data/
```
Place your source docs under `data/` (can nest folders). Supported: .md .txt .pdf .csv

## Run Server
```bash
uvicorn rag.app.main:app --reload
```
Visit http://localhost:8000/

## Example
```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"What are the key priorities?"}'
```

## Environment Variables
See `.env.example`. Copy to `.env` and adjust if needed.

## Acceptance Criteria Notes
- If no relevant chunks, response states lack of info and asks for clarification.
- Every answer ends with `Next recommended step:` line.
- All factual claims must have a `[source:` citation.

## Troubleshooting
- If citations missing: model may ignore instructions; try lowering temperature further.
- If import errors for chroma/sentence-transformers: ensure `rag/requirements-rag.txt` installed.
- Re-run ingest after changing documents.
