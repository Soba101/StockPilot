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

BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
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
    for i in range(len(results['ids'][0])):
        meta = results['metadatas'][0][i]
        doc = results['documents'][0][i]
        dist = results['distances'][0][i]
        score = 1 - dist  # cosine distance -> similarity
        chunks.append(SourceChunk(
            filename=meta['filename'],
            line_start=meta['line_start'],
            line_end=meta['line_end'],
            score=score,
            snippet=doc[:400]
        ))
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


def call_llm(question: str, context: str, rules: str, system_prompt: str) -> str:
    system = f"{system_prompt}\n\nBusiness Rules:\n{rules.strip()}".strip()
    user_content = (
        f"You MUST answer only using the provided context below. If it is empty or irrelevant, say you don't have enough information and ask for clarification.\n"  # noqa: E501
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
    try:
        with httpx.Client(base_url=BASE_URL, timeout=120) as client:
            resp = client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data['choices'][0]['message']['content']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

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
