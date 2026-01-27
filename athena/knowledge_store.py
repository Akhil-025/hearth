"""
Athena Knowledge Store - Extended with versioning and retrieval states.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import chromadb
from chromadb.config import Settings
from pydantic import BaseModel, Field

from ..shared.logging.structured_logger import StructuredLogger
from ..shared.schemas.knowledge import DocumentMetadata, DocumentType
from .document_ingestor import DocumentChunk


class KnowledgeVersion(BaseModel):
    """Version information for knowledge documents."""
    version_id: UUID = Field(default_factory=uuid4)
    document_id: str
    version_number: int
    checksum: str
    previous_version_id: Optional[UUID] = None
    superseded_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.now)
    change_description: Optional[str] = None
    
    # Metadata
    source_path: Optional[str] = None
    file_size: int
    chunk_count: int = 0


class RetrievalState(Enum):
    """Explicit retrieval states."""
    SUCCESS = "success"
    NO_KNOWLEDGE_FOUND = "no_knowledge_found"
    LOW_RELEVANCE_RESULT = "low_relevance_result"
    PARTIAL_MATCH = "partial_match"
    VERSION_CONFLICT = "version_conflict"
    ACCESS_DENIED = "access_denied"


class RetrievalResult(BaseModel):
    """Structured retrieval result with state."""
    state: RetrievalState
    documents: List[DocumentChunk] = Field(default_factory=list)
    relevance_scores: List[float] = Field(default_factory=list)
    version_info: Optional[KnowledgeVersion] = None
    alternative_suggestions: List[str] = Field(default_factory=list)
    
    # Diagnostic information
    query_terms: List[str] = Field(default_factory=list)
    search_duration_ms: float = 0.0
    total_documents_considered: int = 0
    
    class Config:
        use_enum_values = True


class KnowledgeStore:
    """
    Knowledge store with versioning and explicit retrieval states.
    
    Extends ChromaDB with:
    - Document versioning
    - Superseded document tracking
    - Explicit retrieval failure states
    - Checksum validation
    """
    
    def __init__(self, persist_directory: str = "./data/knowledge"):
        self.logger = StructuredLogger(__name__)
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory
        ))
        
        # Collections
        self.documents_collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"description": "Document chunks with embeddings"}
        )
        
        self.versions_collection = self.client.get_or_create_collection(
            name="versions",
            metadata={"description": "Document version tracking"}
        )
        
        # In-memory version index
        self.version_index: Dict[str, KnowledgeVersion] = {}
        self._load_version_index()
        
        # Statistics
        self.stats = {
            "retrievals": 0,
            "retrieval_states": {},
            "version_checks": 0,
            "superseded_documents": 0
        }
        
        self.logger.info(
            "Knowledge store initialized with versioning",
            persist_directory=persist_directory
        )
    
    def _load_version_index(self) -> None:
        """Load version index from storage."""
        try:
            # Load from versions collection
            results = self.versions_collection.get(
                include=["metadatas", "documents"]
            )
            
            for metadata, doc in zip(results["metadatas"], results["documents"]):
                if metadata and doc:
                    version = KnowledgeVersion(**metadata)
                    self.version_index[version.document_id] = version
            
            self.logger.debug(
                "Version index loaded",
                versions=len(self.version_index)
            )
            
        except Exception as e:
            self.logger.warning(
                "Failed to load version index",
                error=str(e)
            )
    
    def store_document(
        self,
        document_id: str,
        chunks: List[DocumentChunk],
        metadata: DocumentMetadata,
        checksum: str,
        previous_version_id: Optional[UUID] = None
    ) -> KnowledgeVersion:
        """
        Store document with version tracking.
        
        Args:
            document_id: Document identifier
            chunks: Document chunks with embeddings
            metadata: Document metadata
            checksum: Document checksum
            previous_version_id: Previous version ID if updating
        
        Returns:
            KnowledgeVersion for the stored document
        """
        # Check for existing version
        existing_version = self.version_index.get(document_id)
        
        if existing_version:
            # Check if document has changed
            if existing_version.checksum == checksum:
                self.logger.debug(
                    "Document unchanged, skipping storage",
                    document_id=document_id,
                    version=existing_version.version_number
                )
                return existing_version
            
            # Create new version
            version_number = existing_version.version_number + 1
            
            # Mark previous version as superseded
            existing_version.superseded_by = uuid4()
            self._update_version(existing_version)
            
            self.logger.info(
                "Document updated, creating new version",
                document_id=document_id,
                old_version=existing_version.version_number,
                new_version=version_number
            )
            
        else:
            # First version
            version_number = 1
        
        # Create new version
        version = KnowledgeVersion(
            document_id=document_id,
            version_number=version_number,
            checksum=checksum,
            previous_version_id=previous_version_id or (existing_version.version_id if existing_version else None),
            source_path=metadata.source_path,
            file_size=metadata.file_size,
            chunk_count=len(chunks),
            change_description=f"Stored via knowledge store"
        )
        
        # Store chunks in ChromaDB
        chunk_ids = []
        embeddings = []
        metadatas = []
        documents = []
        
        for chunk in chunks:
            chunk_id = f"{document_id}_{chunk.chunk_index}"
            chunk_ids.append(chunk_id)
            embeddings.append(chunk.embedding)
            
            chunk_metadata = {
                "document_id": document_id,
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "version_id": str(version.version_id),
                "start_position": chunk.start_position,
                "end_position": chunk.end_position,
                "page_number": chunk.page_number or 0,
                "checksum": chunk.checksum,
                **chunk.metadata
            }
            metadatas.append(chunk_metadata)
            documents.append(chunk.content)
        
        # Store in ChromaDB
        self.documents_collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        
        # Store version information
        self._store_version(version)
        
        # Update index
        self.version_index[document_id] = version
        
        self.logger.info(
            "Document stored with versioning",
            document_id=document_id,
            version=version.version_number,
            chunks=len(chunks)
        )
        
        return version
    
    def _store_version(self, version: KnowledgeVersion) -> None:
        """Store version information in ChromaDB."""
        self.versions_collection.add(
            ids=[str(version.version_id)],
            embeddings=[[0.0]],  # Dummy embedding
            metadatas=[version.dict()],
            documents=[f"Version {version.version_number} of {version.document_id}"]
        )
    
    def _update_version(self, version: KnowledgeVersion) -> None:
        """Update version information in ChromaDB."""
        # ChromaDB doesn't support updates directly, so we remove and re-add
        self.versions_collection.delete(ids=[str(version.version_id)])
        self._store_version(version)
    
    def retrieve(
        self,
        query: str,
        embedding: List[float],
        document_ids: Optional[List[str]] = None,
        min_relevance: float = 0.5,
        max_results: int = 10
    ) -> RetrievalResult:
        """
        Retrieve knowledge with explicit state reporting.
        
        Args:
            query: Query text
            embedding: Query embedding
            document_ids: Optional list of document IDs to search
            min_relevance: Minimum relevance threshold
            max_results: Maximum number of results
        
        Returns:
            RetrievalResult with explicit state
        """
        import time
        start_time = time.time()
        
        self.stats["retrievals"] += 1
        
        # Build query
        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}}
        
        try:
            # Query ChromaDB
            results = self.documents_collection.query(
                query_embeddings=[embedding],
                n_results=max_results * 2,  # Get more for filtering
                where=where,
                include=["metadatas", "documents", "distances"]
            )
            
            if not results["ids"] or not results["ids"][0]:
                duration = (time.time() - start_time) * 1000
                
                # Update statistics
                state_str = RetrievalState.NO_KNOWLEDGE_FOUND.value
                self.stats["retrieval_states"][state_str] = self.stats["retrieval_states"].get(state_str, 0) + 1
                
                return RetrievalResult(
                    state=RetrievalState.NO_KNOWLEDGE_FOUND,
                    query_terms=query.split(),
                    search_duration_ms=duration,
                    total_documents_considered=0,
                    alternative_suggestions=self._generate_alternative_suggestions(query)
                )
            
            # Process results
            documents = []
            relevance_scores = []
            considered_count = 0
            
            for i, (chunk_id, metadata, document, distance) in enumerate(zip(
                results["ids"][0],
                results["metadatas"][0],
                results["documents"][0],
                results["distances"][0]
            )):
                considered_count += 1
                
                # Convert distance to relevance score (0-1)
                # ChromaDB returns cosine distance, so 0 = most relevant, 2 = least
                relevance = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
                
                if relevance >= min_relevance:
                    # Get version info
                    version = None
                    if metadata and "document_id" in metadata:
                        doc_id = metadata["document_id"]
                        version = self.version_index.get(doc_id)
                    
                    # Create chunk
                    chunk = DocumentChunk(
                        chunk_id=metadata.get("chunk_id", str(uuid4())) if metadata else str(uuid4()),
                        document_id=metadata.get("document_id", "unknown") if metadata else "unknown",
                        content=document,
                        chunk_index=metadata.get("chunk_index", 0) if metadata else 0,
                        start_position=metadata.get("start_position", 0) if metadata else 0,
                        end_position=metadata.get("end_position", len(document)) if metadata else len(document),
                        page_number=metadata.get("page_number") if metadata else None,
                        metadata=metadata or {},
                        embedding=None,  # Not returning embeddings for performance
                        checksum=metadata.get("checksum", "") if metadata else ""
                    )
                    
                    documents.append(chunk)
                    relevance_scores.append(relevance)
                
                # Stop if we have enough results
                if len(documents) >= max_results:
                    break
            
            duration = (time.time() - start_time) * 1000
            
            # Determine retrieval state
            state = self._determine_retrieval_state(
                documents_found=len(documents),
                max_expected=max_results,
                min_relevance=min_relevance,
                average_relevance=sum(relevance_scores) / max(len(relevance_scores), 1)
            )
            
            # Get version info if available
            version_info = None
            if documents and documents[0].document_id in self.version_index:
                version_info = self.version_index[documents[0].document_id]
            
            # Update statistics
            state_str = state.value
            self.stats["retrieval_states"][state_str] = self.stats["retrieval_states"].get(state_str, 0) + 1
            
            return RetrievalResult(
                state=state,
                documents=documents,
                relevance_scores=relevance_scores,
                version_info=version_info,
                query_terms=query.split(),
                search_duration_ms=duration,
                total_documents_considered=considered_count,
                alternative_suggestions=self._generate_alternative_suggestions(query) if state != RetrievalState.SUCCESS else []
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Retrieval failed",
                error=str(e),
                query=query[:100]
            )
            
            return RetrievalResult(
                state=RetrievalState.NO_KNOWLEDGE_FOUND,
                query_terms=query.split(),
                search_duration_ms=duration,
                alternative_suggestions=["Try a different query", "Check if relevant documents are indexed"]
            )
    
    def _determine_retrieval_state(
        self,
        documents_found: int,
        max_expected: int,
        min_relevance: float,
        average_relevance: float
    ) -> RetrievalState:
        """Determine the appropriate retrieval state."""
        if documents_found == 0:
            return RetrievalState.NO_KNOWLEDGE_FOUND
        
        if documents_found < max_expected / 2:
            return RetrievalState.PARTIAL_MATCH
        
        if average_relevance < min_relevance * 1.5:  # Low relative to threshold
            return RetrievalState.LOW_RELEVANCE_RESULT
        
        return RetrievalState.SUCCESS
    
    def _generate_alternative_suggestions(self, query: str) -> List[str]:
        """Generate alternative search suggestions."""
        suggestions = []
        
        # Simple suggestion generation
        words = query.lower().split()
        
        if len(words) > 3:
            suggestions.append("Try a shorter, more specific query")
        
        if any(word in ["how", "what", "why", "when", "where"] for word in words[:2]):
            suggestions.append("Try rephrasing as a statement rather than a question")
        
        suggestions.append("Check if the topic is covered in your knowledge base")
        suggestions.append("Consider adding relevant documents to the knowledge base")
        
        return suggestions
    
    def get_document_version(self, document_id: str) -> Optional[KnowledgeVersion]:
        """Get current version of a document."""
        self.stats["version_checks"] += 1
        return self.version_index.get(document_id)
    
    def get_document_history(self, document_id: str) -> List[KnowledgeVersion]:
        """Get version history for a document."""
        # Note: This is simplified - would need proper version chain traversal
        current = self.version_index.get(document_id)
        if not current:
            return []
        
        # Build history (simplified - would query versions collection properly)
        history = [current]
        
        # In a full implementation, we would traverse the version chain
        # using previous_version_id and superseded_by fields
        
        return history
    
    def get_superseded_documents(self) -> List[KnowledgeVersion]:
        """Get documents that have been superseded by newer versions."""
        superseded = []
        
        for version in self.version_index.values():
            if version.superseded_by:
                superseded.append(version)
        
        self.stats["superseded_documents"] = len(superseded)
        return superseded
    
    def cleanup_old_versions(self, keep_versions: int = 3) -> Dict[str, int]:
        """
        Clean up old versions of documents.
        
        Args:
            keep_versions: Number of recent versions to keep
        
        Returns:
            Statistics of cleanup operation
        """
        # Note: This is a placeholder implementation
        # Actual implementation would need to:
        # 1. Identify old versions
        # 2. Remove their chunks from ChromaDB
        # 3. Update version tracking
        
        self.logger.info(
            "Version cleanup requested",
            keep_versions=keep_versions
        )
        
        # In a real implementation, we would:
        # - Group versions by document_id
        # - Sort by version_number
        # - Keep only the most recent keep_versions
        # - Delete chunks for older versions
        
        return {
            "documents_checked": len(self.version_index),
            "versions_removed": 0,  # Placeholder
            "chunks_removed": 0     # Placeholder
        }
    
    def get_statistics(self) -> Dict[str, any]:
        """Get knowledge store statistics."""
        # Get collection stats
        doc_count = self.documents_collection.count()
        version_count = self.versions_collection.count()
        
        # Calculate state distribution
        state_dist = {}
        total_retrievals = sum(self.stats["retrieval_states"].values())
        
        for state, count in self.stats["retrieval_states"].items():
            if total_retrievals > 0:
                percentage = (count / total_retrievals) * 100
                state_dist[state] = {
                    "count": count,
                    "percentage": round(percentage, 1)
                }
        
        return {
            "documents": {
                "total_chunks": doc_count,
                "unique_documents": len(self.version_index),
                "total_versions": version_count
            },
            "retrieval_stats": {
                "total_retrievals": self.stats["retrievals"],
                "state_distribution": state_dist,
                "version_checks": self.stats["version_checks"],
                "superseded_documents": self.stats["superseded_documents"]
            },
            "versioning": {
                "documents_with_versions": len(self.version_index),
                "average_versions_per_doc": version_count / max(len(self.version_index), 1)
            }
        }