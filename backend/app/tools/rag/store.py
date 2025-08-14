"""Vector store implementation supporting Chroma and pgvector."""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import uuid
from app.core.config import settings

class VectorStore(ABC):
    """Abstract base class for vector stores."""
    
    @abstractmethod
    async def upsert(self, docs: List[Dict[str, Any]]) -> List[str]:
        """Store documents with metadata. Returns document IDs."""
        pass
    
    @abstractmethod
    async def search(self, query_embedding: List[float], top_k: int = 6, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieve candidates by vector similarity."""
        pass
    
    @abstractmethod
    async def delete(self, doc_ids: List[str]) -> bool:
        """Remove documents by IDs."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check store connectivity and status."""
        pass


class ChromaStore(VectorStore):
    """Chroma-based vector store implementation."""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of Chroma client."""
        if self._initialized:
            return
            
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            # Use persistent directory from config
            self.client = chromadb.PersistentClient(
                path=settings.RAG_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="stockpilot_docs",
                metadata={"hnsw:space": "cosine"}
            )
            self._initialized = True
            
        except ImportError:
            raise RuntimeError("chromadb not installed. Run: pip install chromadb")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Chroma: {e}")
    
    async def upsert(self, docs: List[Dict[str, Any]]) -> List[str]:
        """Store documents with embeddings and metadata."""
        await self._ensure_initialized()
        
        if not docs:
            return []
        
        doc_ids = []
        texts = []
        metadatas = []
        embeddings = []
        
        for doc in docs:
            doc_id = doc.get('id') or str(uuid.uuid4())
            doc_ids.append(doc_id)
            texts.append(doc.get('content', ''))
            
            # Prepare metadata (exclude content and embedding)
            metadata = {k: v for k, v in doc.items() if k not in ('content', 'embedding', 'id')}
            metadatas.append(metadata)
            
            # Use provided embedding or empty list (will need to be generated externally)
            embeddings.append(doc.get('embedding', []))
        
        # Only add if we have embeddings
        if all(emb for emb in embeddings):
            self.collection.upsert(
                ids=doc_ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings
            )
        else:
            # Store without embeddings for now (can be updated later)
            self.collection.upsert(
                ids=doc_ids,
                documents=texts,
                metadatas=metadatas
            )
        
        return doc_ids
    
    async def search(self, query_embedding: List[float], top_k: int = 6, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search by vector similarity."""
        await self._ensure_initialized()
        
        if not query_embedding:
            return []
        
        # Build Chroma where clause from filters
        where_clause = None
        if filters:
            where_clause = {}
            for key, value in filters.items():
                if isinstance(value, list):
                    where_clause[key] = {"$in": value}
                else:
                    where_clause[key] = value
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause
        )
        
        # Format results
        candidates = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                candidate = {
                    'id': doc_id,
                    'content': results['documents'][0][i] if results['documents'] else '',
                    'score': 1.0 - results['distances'][0][i] if results['distances'] else 0.0,  # Convert distance to similarity
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                }
                candidates.append(candidate)
        
        return candidates
    
    async def delete(self, doc_ids: List[str]) -> bool:
        """Remove documents by IDs."""
        await self._ensure_initialized()
        
        if not doc_ids:
            return True
        
        try:
            self.collection.delete(ids=doc_ids)
            return True
        except Exception:
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Chroma connectivity."""
        try:
            await self._ensure_initialized()
            count = self.collection.count()
            return {
                "status": "healthy",
                "store_type": "chroma",
                "document_count": count,
                "persist_dir": settings.RAG_PERSIST_DIR
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "store_type": "chroma",
                "error": str(e)
            }


class PgVectorStore(VectorStore):
    """PostgreSQL + pgvector implementation (placeholder for future)."""
    
    async def upsert(self, docs: List[Dict[str, Any]]) -> List[str]:
        raise NotImplementedError("pgvector store not yet implemented")
    
    async def search(self, query_embedding: List[float], top_k: int = 6, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError("pgvector store not yet implemented")
    
    async def delete(self, doc_ids: List[str]) -> bool:
        raise NotImplementedError("pgvector store not yet implemented")
    
    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "not_implemented",
            "store_type": "pgvector",
            "error": "pgvector implementation pending"
        }


def get_vector_store() -> VectorStore:
    """Factory function to get the configured vector store."""
    if settings.RAG_STORE.lower() == "chroma":
        return ChromaStore()
    elif settings.RAG_STORE.lower() == "pgvector":
        return PgVectorStore()
    else:
        raise ValueError(f"Unknown RAG_STORE: {settings.RAG_STORE}")