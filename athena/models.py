"""
Athena data models.

Pure data structures for vector search results and query responses.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SourceDocument:
    """
    A chunk of text retrieved from the vector store.
    
    Pure data class: no methods, no side effects.
    """

    text: str
    file_name: str
    page_number: Optional[int] = None
    subject: Optional[str] = None
    module: Optional[str] = None
    chunk_id: Optional[str] = None
    similarity_score: float = 0.0


@dataclass
class QueryResult:
    """
    Response from AthenaService.query().
    
    Contains sources only; no LLM-generated answer.
    Hestia decides whether to invoke LLM with this context.
    """

    question: str
    sources: list[SourceDocument]
    total_indexed: int = 0
    search_time_ms: float = 0.0
    metadata: dict = None

    def __post_init__(self):
        """Ensure metadata is initialized."""
        if self.metadata is None:
            self.metadata = {}

    def __bool__(self) -> bool:
        """True if any sources were found."""
        return len(self.sources) > 0

    @property
    def has_sources(self) -> bool:
        """Check if query returned any sources."""
        return len(self.sources) > 0

    @property
    def source_count(self) -> int:
        """Number of sources returned."""
        return len(self.sources)
