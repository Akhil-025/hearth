"""
Athena configuration management.

Local-only, explicit configuration. No cloud, no auto-loading.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AthenaConfig:
    """
    Configuration for Athena subsystem.
    
    All paths are local. No cloud features.
    No environment variables; explicit initialization only.
    """

    # Activation
    enabled: bool = False

    # Paths
    data_dir: Path = field(default_factory=lambda: Path("./data/notes"))
    index_dir: Path = field(default_factory=lambda: Path("./.athena_index"))

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"  # Local, offline

    # Search
    top_k: int = 5  # Sources per query

    # Internal
    collection_name: str = "hearth_knowledge"

    def __post_init__(self):
        """Validate and normalize paths."""
        self.data_dir = Path(self.data_dir).resolve()
        self.index_dir = Path(self.index_dir).resolve()

        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)

    @property
    def chroma_db_path(self) -> Path:
        """Path to ChromaDB persistent storage."""
        return self.index_dir / "chroma_db"

    @property
    def is_valid(self) -> bool:
        """Check if configuration is usable."""
        return (
            self.data_dir.is_dir()
            and self.index_dir.is_dir()
            and self.chunk_size > 0
            and self.chunk_overlap >= 0
            and self.top_k > 0
        )
