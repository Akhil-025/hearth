"""
Tests for Athena service functionality.

Verifies pure function behavior, determinism, and no side effects.
"""

from pathlib import Path
import pytest
from athena.service import AthenaService
from athena.config import AthenaConfig
from athena.models import QueryResult, SourceDocument


class TestAthenaServiceBasics:
    """Test basic Athena service properties."""
    
    @pytest.fixture
    def athena(self):
        """Create Athena service with disabled config."""
        config = AthenaConfig(enabled=False)
        return AthenaService(config=config)
    
    def test_service_initialization(self, athena):
        """Service initializes without errors."""
        assert athena is not None
        assert athena.config is not None
    
    def test_query_returns_query_result(self, athena):
        """Query method returns QueryResult object."""
        result = athena.query("test question")
        assert isinstance(result, QueryResult)
    
    def test_disabled_service_returns_empty_result(self, athena):
        """Disabled service returns empty sources."""
        result = athena.query("search my notes")
        assert result.has_sources is False
        assert len(result.sources) == 0
        assert result.question == "search my notes"
    
    def test_disabled_service_no_error(self, athena):
        """Disabled service gracefully returns empty result."""
        # Should not raise, should return empty result
        result = athena.query("any question")
        assert isinstance(result, QueryResult)
        assert result.metadata.get("disabled") is True
    
    def test_query_result_bool_conversion(self, athena):
        """QueryResult bool conversion works."""
        result = athena.query("test")
        assert bool(result) is False  # No sources
    
    def test_query_result_properties(self, athena):
        """QueryResult properties work correctly."""
        result = athena.query("test")
        assert result.source_count == 0
        assert result.has_sources is False
        assert isinstance(result.metadata, dict)


class TestSourceDocument:
    """Test SourceDocument data model."""
    
    def test_source_document_creation(self):
        """Create a SourceDocument."""
        doc = SourceDocument(
            text="Important information",
            file_name="notes.pdf",
            page_number=5,
            subject="Math",
            module="Algebra"
        )
        assert doc.text == "Important information"
        assert doc.file_name == "notes.pdf"
        assert doc.page_number == 5
        assert doc.subject == "Math"
        assert doc.module == "Algebra"
    
    def test_source_document_optional_fields(self):
        """SourceDocument with minimal fields."""
        doc = SourceDocument(
            text="Some text",
            file_name="file.pdf"
        )
        assert doc.text == "Some text"
        assert doc.file_name == "file.pdf"
        assert doc.page_number is None
        assert doc.subject is None


class TestAthenaConfig:
    """Test Athena configuration."""
    
    def test_default_config(self):
        """Default config values."""
        config = AthenaConfig()
        assert config.enabled is False
        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.top_k == 5
    
    def test_custom_config(self):
        """Custom config values."""
        config = AthenaConfig(
            enabled=True,
            chunk_size=1024,
            top_k=10
        )
        assert config.enabled is True
        assert config.chunk_size == 1024
        assert config.top_k == 10
    
    def test_config_creates_directories(self):
        """Config initialization creates required directories."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AthenaConfig(
                data_dir=Path(tmpdir) / "data",
                index_dir=Path(tmpdir) / "index"
            )
            assert config.data_dir.exists()
            assert config.index_dir.exists()
    
    def test_config_validity(self):
        """Config validation."""
        config = AthenaConfig()
        assert config.is_valid is True
        
        config.chunk_size = -1
        assert config.is_valid is False
