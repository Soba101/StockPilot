"""RAG retriever that integrates with existing RAG system."""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import os
from pathlib import Path
import sys

# Add the rag directory to Python path to import existing RAG components
rag_path = Path(__file__).resolve().parents[4] / "rag"
if str(rag_path) not in sys.path:
    sys.path.insert(0, str(rag_path))

from app.core.config import settings
from app.core.llm_lmstudio import lmstudio_client


class RAGRetriever:
    """Retriever that uses existing RAG system for document search."""
    
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.embedder = None
        self._initialized = False
        
        # Use existing RAG configuration
        self.chroma_db_dir = os.getenv("CHROMA_DB_DIR", "./rag/vector_store")
        self.embeddings_model = os.getenv("EMBEDDINGS_MODEL", "BAAI/bge-small-en-v1.5")
        self.collection_name = "documents"
        self.top_k = int(os.getenv("RAG_TOP_K", "6"))
        self.max_context_chars = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "8000"))
    
    async def _ensure_initialized(self):
        """Lazy initialization of existing RAG components."""
        if self._initialized:
            return
        
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            from sentence_transformers import SentenceTransformer
            
            # Initialize with existing configuration
            self.chroma_client = chromadb.Client(ChromaSettings(persist_directory=self.chroma_db_dir))
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name, 
                metadata={"hnsw:space": "cosine"}
            )
            self.embedder = SentenceTransformer(self.embeddings_model)
            self._initialized = True
            
        except ImportError as e:
            if "chromadb" in str(e):
                raise RuntimeError("chromadb not installed. Run: pip install chromadb")
            elif "sentence_transformers" in str(e):
                raise RuntimeError("sentence-transformers not installed. Run: pip install sentence-transformers")
            else:
                raise RuntimeError(f"Failed to import dependencies: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize RAG retriever: {e}")
    
    async def search(self, question: str, top_k: Optional[int] = None, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for relevant document snippets."""
        await self._ensure_initialized()
        
        if not question.strip():
            return []
        
        k = top_k or self.top_k
        
        try:
            # Generate embedding for question
            q_emb = self.embedder.encode([question], normalize_embeddings=True)[0]
            
            # Search in existing collection
            results = self.collection.query(
                query_embeddings=[q_emb.tolist()], 
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results for hybrid chat system
            snippets = []
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
                    
                    # Apply filters if provided
                    if filters:
                        skip = False
                        for key, value in filters.items():
                            meta_value = meta.get(key)
                            if isinstance(value, list):
                                if meta_value not in value:
                                    skip = True
                                    break
                            else:
                                if meta_value != value:
                                    skip = True
                                    break
                        if skip:
                            continue
                    
                    # Convert to hybrid chat format
                    filename = str(meta.get('filename', 'unknown'))
                    line_start = int(meta.get('line_start', 0) or 0)
                    line_end = int(meta.get('line_end', 0) or 0)
                    score = 1 - float(dist)  # Convert distance to similarity
                    
                    # Create citation URL
                    url = f"/docs/{filename}"
                    if line_start > 0:
                        url += f"#lines-{line_start}-{line_end}"
                    
                    snippet = {
                        "title": f"{filename} (lines {line_start}-{line_end})",
                        "url": url,
                        "quote": doc[:400].strip(),  # Truncate for display
                        "score": score,
                        "effective_date": meta.get("effective_date"),
                        "doc_type": meta.get("doc_type", "document"),
                        "owner": meta.get("owner", "system")
                    }
                    snippets.append(snippet)
                    
                except Exception:
                    continue
            
            return snippets
            
        except Exception as e:
            raise RuntimeError(f"RAG search failed: {e}")
    
    async def generate_answer(self, question: str, snippets: List[Dict[str, Any]]) -> str:
        """Generate answer using retrieved snippets and LM Studio."""
        if not snippets:
            return "I don't have enough information in the indexed documents to answer that accurately."
        
        # Build context from snippets
        context_parts = []
        total_chars = 0
        
        for snippet in snippets:
            block = f"FILE: {snippet['title']}\n{snippet['quote']}"
            if total_chars + len(block) > self.max_context_chars:
                break
            context_parts.append(block)
            total_chars += len(block)
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Generate answer using LM Studio
        try:
            messages = [
                {
                    "role": "system", 
                    "content": "You are a helpful StockPilot assistant. Answer questions using only the provided context. Always include inline citations using [source: filename] format."
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nContext:\n{context}\n\nAnswer the question using only the provided context. Include citations."
                }
            ]
            
            answer = await lmstudio_client.get_chat_response(messages, temperature=0.2, max_tokens=800)
            
            if not answer:
                return "Unable to generate answer from the retrieved documents."
            
            return answer
            
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    async def health_check(self) -> Dict[str, Any]:
        """Check RAG system health."""
        try:
            await self._ensure_initialized()
            
            # Check collection status
            count = self.collection.count()
            
            # Test embedding generation
            test_embedding = self.embedder.encode(["test"], normalize_embeddings=True)
            
            return {
                "status": "healthy",
                "document_count": count,
                "embeddings_model": self.embeddings_model,
                "chroma_db_dir": self.chroma_db_dir,
                "embedding_dimension": len(test_embedding[0]) if test_embedding else 0
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global retriever instance
_retriever = None

def get_rag_retriever() -> RAGRetriever:
    """Get the global RAG retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever