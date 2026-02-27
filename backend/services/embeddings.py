"""
Embeddings and Vector Store Service

Manages document embeddings and similarity search for RAG.
Uses Firestore's built-in vector search for storage.
"""

import os
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from core.config import get_firestore_client


@dataclass
class DocumentChunk:
    """A chunk of a document with metadata."""
    id: str
    content: str
    source: str
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """Result from similarity search."""
    content: str
    source: str
    score: float
    metadata: Dict[str, Any]


class EmbeddingsService:
    """
    Service for generating embeddings and managing vector store.

    Uses OpenAI embeddings and Firestore vector search for storage.
    """

    COLLECTION_NAME = "advising_embeddings"
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536
    CHUNK_SIZE = 500  # characters per chunk
    CHUNK_OVERLAP = 50

    def __init__(self):
        self._openai_client = None
        self._db = None
        self._collection = None
        self._initialized = False

    def _ensure_initialized(self):
        """Initialize clients on first use."""
        if self._initialized:
            return

        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI package not installed. Run: pip install openai")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")

        self._openai_client = OpenAI(api_key=api_key)

        # Use Firestore for vector storage
        self._db = get_firestore_client()
        self._collection = self._db.collection(self.COLLECTION_NAME)

        self._initialized = True

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        self._ensure_initialized()

        response = self._openai_client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        self._ensure_initialized()

        response = self._openai_client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=texts
        )
        return [item.embedding for item in response.data]

    def _chunk_text(self, text: str, source: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Split text into overlapping chunks."""
        chunks = []
        metadata = metadata or {}

        # Simple chunking by character count with overlap
        start = 0
        chunk_num = 0

        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk_text = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind(". ")
                if last_period > self.CHUNK_SIZE // 2:
                    chunk_text = chunk_text[:last_period + 1]
                    end = start + last_period + 1

            # Generate unique ID
            chunk_id = hashlib.md5(f"{source}:{chunk_num}:{chunk_text[:50]}".encode()).hexdigest()

            chunks.append(DocumentChunk(
                id=chunk_id,
                content=chunk_text.strip(),
                source=source,
                metadata={**metadata, "chunk_num": chunk_num}
            ))

            chunk_num += 1
            start = end - self.CHUNK_OVERLAP

        return chunks

    def add_document(self, content: str, source: str, metadata: Dict[str, Any] = None):
        """Add a document to the vector store."""
        self._ensure_initialized()

        chunks = self._chunk_text(content, source, metadata)

        if not chunks:
            return

        # Generate embeddings for all chunks
        texts = [c.content for c in chunks]
        embeddings = self.generate_embeddings(texts)

        # Add each chunk to Firestore with its embedding vector
        batch = self._db.batch()

        for chunk, embedding in zip(chunks, embeddings):
            doc_ref = self._collection.document(chunk.id)
            batch.set(doc_ref, {
                "content": chunk.content,
                "source": chunk.source,
                "metadata": chunk.metadata,
                "embedding": Vector(embedding)
            })

        batch.commit()

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Add multiple documents to the vector store.

        Args:
            documents: List of dicts with 'content', 'source', and optional 'metadata'
        """
        for doc in documents:
            self.add_document(
                content=doc["content"],
                source=doc["source"],
                metadata=doc.get("metadata", {})
            )

    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        """
        Search for similar documents using Firestore vector search.

        Args:
            query: Search query
            n_results: Number of results to return

        Returns:
            List of SearchResult ordered by relevance
        """
        self._ensure_initialized()

        query_embedding = self.generate_embedding(query)

        # Use Firestore's find_nearest for vector similarity search
        vector_query = self._collection.find_nearest(
            vector_field="embedding",
            query_vector=Vector(query_embedding),
            distance_measure=DistanceMeasure.COSINE,
            limit=n_results
        )

        search_results = []

        for doc in vector_query.stream():
            data = doc.to_dict()
            # Firestore returns distance, convert to similarity score
            # For cosine distance: similarity = 1 - distance
            distance = getattr(doc, 'distance', 0) if hasattr(doc, 'distance') else 0

            search_results.append(SearchResult(
                content=data.get("content", ""),
                source=data.get("source", "unknown"),
                score=1 - distance,
                metadata=data.get("metadata", {})
            ))

        return search_results

    def get_document_count(self) -> int:
        """Get number of documents in the vector store."""
        self._ensure_initialized()

        # Count documents in collection
        # Note: For large collections, consider using a counter document
        docs = self._collection.limit(10000).stream()
        return sum(1 for _ in docs)

    def clear(self):
        """Clear all documents from the vector store."""
        self._ensure_initialized()

        # Delete all documents in batches
        batch_size = 500
        docs = self._collection.limit(batch_size).stream()
        deleted = 0

        while True:
            batch = self._db.batch()
            doc_count = 0

            for doc in docs:
                batch.delete(doc.reference)
                doc_count += 1

            if doc_count == 0:
                break

            batch.commit()
            deleted += doc_count

            if doc_count < batch_size:
                break

            docs = self._collection.limit(batch_size).stream()

        return deleted

    def document_exists(self, doc_id: str) -> bool:
        """Check if a document with the given ID exists."""
        self._ensure_initialized()
        doc = self._collection.document(doc_id).get()
        return doc.exists


# Singleton instance
_embeddings_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    """Get singleton instance of EmbeddingsService."""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service
