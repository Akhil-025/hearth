"""
Vector search retriever for Athena.

Wraps ChromaDB for deterministic, read-only search.
"""

from pathlib import Path
from typing import Optional

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

from .config import AthenaConfig
from .models import SourceDocument, QueryResult
from .utils import chunk_text, clean_text


class AthenaRetriever:
    """
    Vector search engine for knowledge base.
    
    Read-only at runtime. No writes except during explicit indexing.
    Deterministic: same query → same results (within index bounds).
    """

    def __init__(self, config: AthenaConfig):
        """
        Initialize retriever with configuration.
        
        Args:
            config: AthenaConfig instance
        """
        self.config = config
        self._client = None
        self._collection = None
        self._doc_metadata = {}
        self._chromadb_available = chromadb is not None
        
        if not self._chromadb_available and config.enabled:
            # Only warn if Athena is actually enabled
            import warnings
            warnings.warn(
                "chromadb not available. Install with: "
                "pip install chromadb sentence-transformers"
            )

    def _ensure_client(self):
        """Lazy-load ChromaDB client."""
        if not self._chromadb_available:
            return False
        
        if self._client is None:
            if chromadb is None:
                return False
                
            settings = Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(self.config.chroma_db_path),
                anonymized_telemetry=False,
            )
            self._client = chromadb.Client(settings)
            self._collection = self._client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        
        return True

    def query(
        self,
        question: str,
        subject_filter: Optional[str] = None,
        module_filter: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> QueryResult:
        """
        Search knowledge base for relevant sources.
        
        Args:
            question: User's question
            subject_filter: Filter by subject (optional)
            module_filter: Filter by module (optional)
            top_k: Number of results (uses config default if None)
        
        Returns:
            QueryResult with sources, no LLM answer
        """
        if not self.config.enabled:
            # Return empty result if Athena disabled
            return QueryResult(
                question=question,
                sources=[],
                total_indexed=0,
                metadata={"disabled": True},
            )
        
        if not self._ensure_client():
            # ChromaDB not available
            return QueryResult(
                question=question,
                sources=[],
                total_indexed=0,
                metadata={"unavailable": True},
            )

        if not self._collection or self._collection.count() == 0:
            # No documents indexed
            return QueryResult(
                question=question,
                sources=[],
                total_indexed=0,
                metadata={"indexed": False},
            )

        # Build metadata filter
        where_filter = None
        if subject_filter or module_filter:
            where_filter = {}
            if subject_filter:
                where_filter["subject"] = subject_filter
            if module_filter:
                where_filter["module"] = module_filter

        top_k = top_k or self.config.top_k

        try:
            results = self._collection.query(
                query_texts=[question],
                n_results=top_k,
                where=where_filter if where_filter else None,
            )

            sources = self._format_results(results)

            return QueryResult(
                question=question,
                sources=sources,
                total_indexed=self._collection.count(),
                metadata={
                    "searched": True,
                    "filters": {"subject": subject_filter, "module": module_filter},
                },
            )

        except Exception as e:
            # Graceful degradation: return empty result on error
            return QueryResult(
                question=question,
                sources=[],
                total_indexed=self._collection.count(),
                metadata={"error": str(e)},
            )

    def add_documents(
        self,
        documents: list[dict],
        file_name: str,
        subject: Optional[str] = None,
        module: Optional[str] = None,
    ):
        """
        Add documents to index (explicit ingestion only).
        
        Args:
            documents: List of doc dicts with 'text', 'page_number'
            file_name: Source filename
            subject: Optional subject category
            module: Optional module category
        """
        if not self._collection:
            self._ensure_client()

        ids = []
        texts = []
        metadatas = []

        for idx, doc in enumerate(documents):
            doc_id = f"{file_name}_{idx}"
            ids.append(doc_id)
            texts.append(doc["text"])
            metadatas.append(
                {
                    "file_name": file_name,
                    "page_number": doc.get("page_number", 0),
                    "subject": subject or "uncategorized",
                    "module": module or "general",
                    "chunk_index": idx,
                }
            )

        self._collection.add(ids=ids, documents=texts, metadatas=metadatas)

    def get_index_stats(self) -> dict:
        """
        Get statistics about indexed documents.
        
        Returns:
            Dict with count, file list, etc.
        """
        if not self._ensure_client() or not self._collection:
            return {
                "total_chunks": 0,
                "collection_name": self.config.collection_name,
                "embedding_model": self.config.embedding_model,
                "available": False,
            }

        stats = {
            "total_chunks": self._collection.count(),
            "collection_name": self.config.collection_name,
            "embedding_model": self.config.embedding_model,
            "available": True,
        }

        return stats

    def _format_results(self, results: dict) -> list[SourceDocument]:
        """
        Format ChromaDB results into SourceDocument objects.
        
        Args:
            results: ChromaDB query result
        
        Returns:
            List of SourceDocument objects
        """
        sources = []

        if not results or not results["documents"]:
            return sources

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for text, metadata, distance in zip(documents, metadatas, distances):
            # Convert distance to similarity (cosine distance to similarity)
            similarity = 1 - distance if distance else 0.0

            source = SourceDocument(
                text=text,
                file_name=metadata.get("file_name", "unknown"),
                page_number=metadata.get("page_number"),
                subject=metadata.get("subject"),
                module=metadata.get("module"),
                chunk_id=metadata.get("chunk_id"),
                similarity_score=similarity,
            )
            sources.append(source)

        return sources
