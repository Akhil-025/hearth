"""
Athena service - single public entry point.

Pure, deterministic, read-only query interface.
No LLM calls, no memory writes, no side effects.
"""

from typing import Optional

from .config import AthenaConfig
from .ingestor import AthenaIngestor
from .models import QueryResult, SourceDocument
from .retriever import AthenaRetriever


class AthenaService:
    """
    Single public API for Athena subsystem.
    
    - Deterministic: same question → same sources
    - Read-only: no writes at runtime
    - Pure function: no side effects
    - No LLM: returns raw context only
    - Intent-gated: only called if user matches patterns
    """

    def __init__(self, config: Optional[AthenaConfig] = None):
        """
        Initialize Athena service.
        
        Args:
            config: AthenaConfig (uses defaults if None)
        """
        self.config = config or AthenaConfig()
        self.retriever = AthenaRetriever(self.config)
        self.ingestor = AthenaIngestor(self.config, self.retriever)

    def query(
        self,
        question: str,
        subject_filter: Optional[str] = None,
        module_filter: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> QueryResult:
        """
        Query the knowledge base.
        
        Pure function: no side effects, deterministic output.
        
        Args:
            question: User's question
            subject_filter: Optional filter by subject
            module_filter: Optional filter by module
            top_k: Number of results (uses config default if None)
        
        Returns:
            QueryResult with sources, no LLM-generated answer
        """
        return self.retriever.query(
            question=question,
            subject_filter=subject_filter,
            module_filter=module_filter,
            top_k=top_k,
        )

    def ingest_pdf(
        self,
        pdf_path: str,
        subject: Optional[str] = None,
        module: Optional[str] = None,
    ) -> dict:
        """
        Manually ingest a PDF file (explicit command only).
        
        Args:
            pdf_path: Path to PDF
            subject: Optional subject category
            module: Optional module category
        
        Returns:
            Dict with ingestion result
        """
        return self.ingestor.ingest_pdf(
            pdf_path=pdf_path,
            subject=subject,
            module=module,
        )

    def ingest_directory(
        self,
        directory: Optional[str] = None,
        subject: Optional[str] = None,
        module: Optional[str] = None,
    ) -> dict:
        """
        Manually ingest all PDFs in a directory (explicit command only).
        
        Args:
            directory: Directory path (uses config.data_dir if None)
            subject: Optional subject for all files
            module: Optional module for all files
        
        Returns:
            Dict with aggregated result
        """
        return self.ingestor.ingest_directory(
            directory=directory,
            subject=subject,
            module=module,
        )

    def get_stats(self) -> dict:
        """
        Get index statistics.
        
        Returns:
            Dict with index info
        """
        return self.ingestor.get_ingestion_stats()
