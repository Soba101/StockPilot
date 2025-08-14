"""Document ingestion system for RAG."""
from __future__ import annotations
import argparse
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone
import re

from app.core.llm_lmstudio import lmstudio_client
from app.tools.rag.store import get_vector_store


def chunk_text(text: str, chunk_size: int = 750, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings in the last 100 chars
            search_start = max(start + chunk_size - 100, start)
            sentence_end = -1
            
            for i in range(end, search_start, -1):
                if text[i:i+1] in '.!?':
                    sentence_end = i + 1
                    break
            
            if sentence_end > start:
                end = sentence_end
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start <= 0:
            start = end
    
    return chunks


def extract_text_from_file(file_path: Path) -> str:
    """Extract text from various file formats."""
    suffix = file_path.suffix.lower()
    
    if suffix in ('.txt', '.md'):
        return file_path.read_text(encoding='utf-8')
    
    elif suffix == '.pdf':
        try:
            import pymupdf  # fitz
            doc = pymupdf.open(file_path)
            text = ""
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text += f"\n[Page {page_num + 1}]\n"
                text += page.get_text()
            doc.close()
            return text
        except ImportError:
            raise RuntimeError("PyMuPDF not installed. Run: pip install pymupdf")
    
    elif suffix == '.csv':
        import csv
        content = ""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                content += ', '.join(row) + '\n'
        return content
    
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def extract_metadata_from_path(file_path: Path, doc_type: str, owner: str, effective_date: Optional[str]) -> Dict[str, Any]:
    """Extract metadata from file path and parameters."""
    metadata = {
        "title": file_path.stem,
        "url": str(file_path),
        "doc_type": doc_type,
        "owner": owner,
        "file_extension": file_path.suffix.lower(),
        "file_size": file_path.stat().st_size,
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }
    
    if effective_date:
        metadata["effective_date"] = effective_date
    
    # Try to extract version from filename
    version_match = re.search(r'v?(\d+\.\d+)', file_path.stem)
    if version_match:
        metadata["version"] = version_match.group(1)
    
    # Extract department from path
    path_parts = file_path.parts
    if len(path_parts) > 1:
        # Look for common department names in path
        departments = ['ops', 'operations', 'finance', 'hr', 'legal', 'marketing', 'sales']
        for part in path_parts:
            if part.lower() in departments:
                metadata["department"] = part.lower()
                break
    
    return metadata


async def ingest_file(file_path: Path, doc_type: str = "document", owner: str = "system", 
                     effective_date: Optional[str] = None, store=None) -> List[str]:
    """Ingest a single file into the vector store."""
    print(f"Processing {file_path}...")
    
    # Extract text
    text = extract_text_from_file(file_path)
    if not text.strip():
        print(f"  Warning: No text extracted from {file_path}")
        return []
    
    # Extract metadata
    base_metadata = extract_metadata_from_path(file_path, doc_type, owner, effective_date)
    
    # Chunk text
    chunks = chunk_text(text)
    print(f"  Created {len(chunks)} chunks")
    
    # Generate embeddings for chunks
    try:
        embeddings = await lmstudio_client.embed([chunk for chunk in chunks])
        if not embeddings or len(embeddings) != len(chunks):
            print(f"  Warning: Embedding generation failed for {file_path}")
            embeddings = [[] for _ in chunks]  # Empty embeddings as fallback
    except Exception as e:
        print(f"  Warning: Embedding error for {file_path}: {e}")
        embeddings = [[] for _ in chunks]
    
    # Prepare documents for storage
    docs = []
    doc_ids = []
    
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        doc_id = f"{file_path.stem}_{i}_{uuid.uuid4().hex[:8]}"
        doc_ids.append(doc_id)
        
        # Create chunk-specific metadata
        chunk_metadata = base_metadata.copy()
        chunk_metadata.update({
            "chunk_index": i,
            "chunk_count": len(chunks),
            "content_preview": chunk[:100] + "..." if len(chunk) > 100 else chunk
        })
        
        # Add page number if PDF
        if file_path.suffix.lower() == '.pdf' and '[Page ' in chunk:
            page_match = re.search(r'\[Page (\d+)\]', chunk)
            if page_match:
                page_num = int(page_match.group(1))
                chunk_metadata["page_number"] = page_num
                chunk_metadata["url"] = f"{base_metadata['url']}#page={page_num}"
        
        docs.append({
            "id": doc_id,
            "content": chunk,
            "embedding": embedding,
            **chunk_metadata
        })
    
    # Store in vector store
    if store:
        stored_ids = await store.upsert(docs)
        print(f"  Stored {len(stored_ids)} chunks")
        return stored_ids
    
    return doc_ids


async def ingest_directory(dir_path: Path, doc_type: str = "document", owner: str = "system",
                          effective_date: Optional[str] = None, recursive: bool = True) -> int:
    """Ingest all supported files from a directory."""
    print(f"Ingesting documents from {dir_path}...")
    
    store = get_vector_store()
    supported_extensions = {'.txt', '.md', '.pdf', '.csv'}
    total_files = 0
    
    # Get file pattern
    pattern = "**/*" if recursive else "*"
    
    for file_path in dir_path.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            try:
                await ingest_file(file_path, doc_type, owner, effective_date, store)
                total_files += 1
            except Exception as e:
                print(f"  Error processing {file_path}: {e}")
    
    print(f"Completed ingestion: {total_files} files processed")
    return total_files


async def main():
    """CLI entry point for document ingestion."""
    parser = argparse.ArgumentParser(description="Ingest documents into RAG vector store")
    parser.add_argument("--path", required=True, help="Path to file or directory")
    parser.add_argument("--doc-type", default="document", help="Document type (policy, sop, guide, etc.)")
    parser.add_argument("--owner", default="system", help="Document owner/department")
    parser.add_argument("--effective-date", help="Effective date (YYYY-MM-DD)")
    parser.add_argument("--recursive", action="store_true", help="Process directories recursively")
    
    args = parser.parse_args()
    
    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path {path} does not exist")
        return 1
    
    try:
        if path.is_file():
            store = get_vector_store()
            await ingest_file(path, args.doc_type, args.owner, args.effective_date, store)
        else:
            await ingest_directory(path, args.doc_type, args.owner, args.effective_date, args.recursive)
        
        print("Ingestion completed successfully!")
        return 0
    
    except Exception as e:
        print(f"Error during ingestion: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))