import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from rag.load_env import load as load_env
load_env()
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

RAW_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234")
# Normalized base without trailing slash; we will prepend endpoint variants explicitly
BASE_URL = RAW_BASE_URL.rstrip('/')
MODEL_NAME = os.getenv("LMSTUDIO_MODEL", "gpt-oss-20b")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "BAAI/bge-small-en-v1.5")
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./rag/vector_store")
TOP_K = int(os.getenv("RAG_TOP_K", 5))
MAX_CTX = int(os.getenv("RAG_MAX_CONTEXT_CHARS", 8000))
COLLECTION_NAME = "documents"

SYSTEM_PROMPT_PATH = os.getenv("SYSTEM_PROMPT_PATH", "./rag/prompts/system.md")
BUSINESS_RULES_PATH = os.getenv("BUSINESS_RULES_PATH", "./rag/config/business_rules.md")

client_chroma = chromadb.Client(Settings(persist_directory=CHROMA_DB_DIR))
collection = client_chroma.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
embedder = SentenceTransformer(EMBEDDINGS_MODEL)

app = FastAPI(title="Local RAG Chat")

class ChatRequest(BaseModel):
    question: str

class SourceChunk(BaseModel):
    filename: str
    line_start: int
    line_end: int
    score: float
    snippet: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]


def load_text(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""


def retrieve(question: str):
    q_emb = embedder.encode([question], normalize_embeddings=True)[0]
    results = collection.query(query_embeddings=[q_emb.tolist()], n_results=TOP_K, include=["documents", "metadatas", "distances"])
    chunks = []
    if not results.get('ids'):
        return []
    ids_raw = results.get('ids') or [[]]
    metas_raw = results.get('metadatas') or [[]]
    docs_raw = results.get('documents') or [[]]
    dists_raw = results.get('distances') or [[]]
    ids = ids_raw[0] if ids_raw else []
    metas = metas_raw[0] if metas_raw else []
    docs = docs_raw[0] if docs_raw else []
    dists = dists_raw[0] if dists_raw else []
    for i in range(len(ids)):
        try:
            meta = metas[i] or {}
            doc = docs[i] or ""
            dist = dists[i] if dists else 0.0
            filename = str(meta.get('filename', 'unknown'))
            ls = int(meta.get('line_start', 0) or 0)
            le = int(meta.get('line_end', 0) or 0)
            score = 1 - float(dist)
            chunks.append(SourceChunk(
                filename=filename,
                line_start=ls,
                line_end=le,
                score=score,
                snippet=doc[:400]
            ))
        except Exception:
            continue
    return chunks


def build_context(chunks: List[SourceChunk]) -> str:
    context_parts = []
    total = 0
    for c in chunks:
        block = f"FILE: {c.filename} LINES: {c.line_start}-{c.line_end}\n{c.snippet.strip()}".strip()
        if total + len(block) > MAX_CTX:
            break
        context_parts.append(block)
        total += len(block)
    return "\n\n---\n\n".join(context_parts)


def _parse_llm_response(data: dict) -> str:
    try:
        # OpenAI chat format
        return data['choices'][0]['message']['content']
    except Exception:
        # Fallback: classic completion format
        try:
            return data['choices'][0].get('text', '').strip()
        except Exception:
            return str(data)


def call_llm(question: str, context: str, rules: str, system_prompt: str) -> str:
    system = f"{system_prompt}\n\nBusiness Rules:\n{rules.strip()}".strip()
    user_content = (
        "You MUST answer only using the provided context below. If it is empty or irrelevant, say you don't have enough information and ask for clarification.\n"
        f"Question: {question}\n\nRetrieved Context:\n{context if context else '[NO CONTEXT]'}\n\nConstruct answer with inline citations and final 'Next recommended step:' line."
    )
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }
    # Build endpoint matrix depending on whether user supplied /v1 already.
    # Build endpoints preferring versioned forms first to avoid LM Studio noisy warnings.
    if BASE_URL.endswith('/v1'):
        roots = [BASE_URL.rstrip('/'), BASE_URL[:-3].rstrip('/')]
    else:
        roots = [BASE_URL.rstrip('/'), f"{BASE_URL.rstrip('/')}/v1"]
    cleaned = []
    seen_roots = set()
    for r in roots:
        if r not in seen_roots:
            seen_roots.add(r)
            cleaned.append(r)
    endpoints: list[str] = []
    for r in cleaned:
        has_v1 = r.endswith('/v1')
        base_no_v1 = r[:-3] if has_v1 else r
        # Always try versioned endpoints first
        endpoints.append((r if has_v1 else base_no_v1 + '/v1') + '/chat/completions')
        endpoints.append((r if has_v1 else base_no_v1 + '/v1') + '/completions')
        # Fallback unversioned only if base root (may produce warnings but only after versioned attempts fail)
        if not has_v1:
            endpoints.append(base_no_v1 + '/chat/completions')
            endpoints.append(base_no_v1 + '/completions')
    # Deduplicate preserving order
    dedup = []
    seen = set()
    for e in endpoints:
        if e not in seen:
            seen.add(e)
            dedup.append(e)
    endpoints = dedup
    last_error = None
    debug = os.getenv('RAG_DEBUG') == '1'
    with httpx.Client(timeout=120) as client:
        for url in endpoints:
            try:
                if debug: print(f"[RAG] Trying LLM endpoint: {url}")
                resp = client.post(url, json=payload)
                text = resp.text
                # Attempt JSON parse; some servers return plain text on error
                try:
                    data = resp.json()
                except Exception:
                    if 'Unexpected endpoint' in text:
                        last_error = f"Server text error at {url}: {text[:120]}"; continue
                    # Treat whole text as content if non-empty
                    if text.strip():
                        return text.strip()
                    last_error = f"Non-JSON empty response at {url}"; continue
                if ('Unexpected endpoint' in str(data) or ('error' in data and 'choices' not in data)) and 'choices' not in data:
                    last_error = f"Server rejected {url}: {data}"; continue
                if 'choices' not in data:
                    last_error = f"Malformed response from {url}: {data}"; continue
                content = _parse_llm_response(data)
                if not content:
                    last_error = f"Empty content from {url}"; continue
                return content
            except Exception as e:  # collect error and try next
                last_error = e
                if debug: print(f"[RAG] Endpoint failed {url}: {e}")
    raise HTTPException(status_code=500, detail=f"LLM error: {last_error}")

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    system_prompt = load_text(SYSTEM_PROMPT_PATH)
    business_rules = load_text(BUSINESS_RULES_PATH)
    chunks = retrieve(req.question)
    context = build_context(chunks)
    answer = call_llm(req.question, context, business_rules, system_prompt)
    if not chunks:
        # Override if model attempted an answer without context.
        if "[NO CONTEXT]" in context or "[source:" not in answer:
            answer = (
                "I don't have enough information in the indexed documents to answer that accurately yet. "
                "Please clarify, narrow the topic, or add relevant documents to the data directory and re-run ingestion."
            )
        if "Next recommended step:" not in answer:
            answer += "\nNext recommended step: Provide a clarifying detail or add a related document, then ask again."
        return ChatResponse(answer=answer, sources=[])
    if "Next recommended step:" not in answer:
        answer += "\nNext recommended step: Verify the cited sources and decide on a follow-up question."
    if chunks and "[source:" not in answer:
        answer += "\n(Note: Model failed to cite sources properly; please verify.)"
    return ChatResponse(answer=answer, sources=chunks)

@app.get("/", response_class=HTMLResponse)
async def ui_root():
    return """<!DOCTYPE html><html><head><meta charset='utf-8'><title>Local RAG Chat</title></head>
<body style='font-family: Arial, sans-serif; margin:40px;'>
<h2>Local RAG Chat</h2>
<form id='f'>
<input style='width:70%;' name='q' id='q' placeholder='Ask a question...' />
<button type='submit'>Ask</button>
</form>
<pre id='answer' style='background:#f5f5f5;padding:12px;white-space:pre-wrap;'></pre>
<div id='sources'></div>
<script>
const f=document.getElementById('f');
const q=document.getElementById('q');
const ans=document.getElementById('answer');
const srcDiv=document.getElementById('sources');
f.addEventListener('submit', async (e)=>{
  e.preventDefault();
  ans.textContent='Loading...';
  srcDiv.innerHTML='';
  const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q.value})});
  const j=await r.json();
  ans.textContent=j.answer;
  if(j.sources){
    const list=j.sources.map(s=>`<li><strong>${s.filename}</strong> [${s.line_start}-${s.line_end}] score=${s.score.toFixed(3)}</li>`).join('');
    srcDiv.innerHTML='<h4>Sources</h4><ul>'+list+'</ul>';
  }
});
</script>
</body></html>"""
