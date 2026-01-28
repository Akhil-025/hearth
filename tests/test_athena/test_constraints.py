"""
Tests for Athena constraint enforcement.

Verifies HEARTH hard constraints:
- No LLM calls
- No memory writes
- No side effects
- Read-only at runtime
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from athena.service import AthenaService
from athena.config import AthenaConfig


class TestAthenaConstraints:
    """Test that Athena enforces HEARTH constraints."""
    
    @pytest.fixture
    def athena(self):
        """Create Athena service."""
        config = AthenaConfig(enabled=False)
        return AthenaService(config=config)
    
    def test_athena_never_calls_ollama(self, athena):
        """Athena never invokes LLM."""
        # Even if we somehow enable indexing, query should never call LLM
        result = athena.query("test question")
        
        # Verify no LLM-related attributes
        assert not hasattr(athena, 'llm_client')
        assert not hasattr(athena.retriever, 'llm')
        assert not hasattr(athena.ingestor, 'llm')
    
    def test_athena_never_writes_memory(self, athena):
        """Athena never writes to Mnemosyne."""
        # Query should not touch memory
        result = athena.query("test question")
        
        # Verify no memory-related attributes
        assert not hasattr(athena, 'memory_store')
        assert not hasattr(athena.retriever, 'memory')
        assert not hasattr(athena.ingestor, 'memory')
    
    def test_athena_never_reads_memory(self, athena):
        """Athena never reads from Mnemosyne."""
        result = athena.query("test question")
        
        # Service has no memory dependency
        assert not hasattr(athena, 'memory_store')
    
    def test_query_is_pure_function(self, athena):
        """Query is a pure function - same input gives same output."""
        # Two queries with same input
        result1 = athena.query("test")
        result2 = athena.query("test")
        
        # Should be identical
        assert result1.question == result2.question
        assert len(result1.sources) == len(result2.sources)
        assert result1.metadata == result2.metadata
    
    def test_query_has_no_side_effects(self, athena):
        """Query does not modify state."""
        # Get initial state
        initial_stats = athena.get_stats()
        
        # Run multiple queries
        athena.query("question 1")
        athena.query("question 2")
        athena.query("question 3")
        
        # State should not change from queries alone
        # (only from explicit ingestion)
        final_stats = athena.get_stats()
        assert initial_stats == final_stats
    
    def test_ingestor_explicit_only(self, athena):
        """Ingestor requires explicit user call."""
        # No background indexing should happen
        # Just verify ingestor exists and is callable
        assert hasattr(athena, 'ingestor')
        assert callable(athena.ingest_pdf)
        assert callable(athena.ingest_directory)


class TestAthenaReadOnly:
    """Test that Athena is read-only at runtime."""
    
    @pytest.fixture
    def athena(self):
        """Create Athena service."""
        config = AthenaConfig(enabled=False)
        return AthenaService(config=config)
    
    def test_query_does_not_modify_index(self, athena):
        """Querying should not modify the index."""
        stats_before = athena.get_stats()
        
        # Run queries
        athena.query("test 1")
        athena.query("test 2")
        
        stats_after = athena.get_stats()
        
        # Stats should be identical
        assert stats_before == stats_after
    
    def test_retriever_has_no_write_methods_in_query(self):
        """Retriever.query() should not write."""
        from athena.retriever import AthenaRetriever
        from athena.config import AthenaConfig
        
        config = AthenaConfig(enabled=False)
        retriever = AthenaRetriever(config)
        
        # Query method should not have side effects
        result = retriever.query("test")
        
        # Verify result is read-only
        assert isinstance(result.sources, list)
        # Trying to modify should work on our copy, not affect internal state
        result.sources.append("dummy")
        
        # Query again - should still be empty
        result2 = retriever.query("test")
        assert len(result2.sources) == 0


class TestAthenaExplicitActivation:
    """Test that Athena only activates on explicit intent."""
    
    def test_athena_disabled_by_default(self):
        """Athena disabled by default."""
        config = AthenaConfig()
        assert config.enabled is False
    
    def test_athena_requires_explicit_enable(self):
        """Athena requires explicit configuration to enable."""
        config = AthenaConfig(enabled=True)
        assert config.enabled is True
    
    def test_intent_gating_in_classifier(self):
        """Intent classifier has explicit Athena patterns."""
        from hestia.intent_classifier import IntentClassifier
        
        classifier = IntentClassifier()
        
        # Should have athena_patterns defined
        assert hasattr(classifier, 'athena_patterns')
        assert len(classifier.athena_patterns) > 0
        
        # Patterns should be explicit
        assert "search my notes" in classifier.athena_patterns
        assert "look up in my" in classifier.athena_patterns


class TestAthenaGracefulDegradation:
    """Test Athena graceful failure modes."""
    
    @pytest.fixture
    def athena(self):
        """Create Athena service."""
        config = AthenaConfig(enabled=False)
        return AthenaService(config=config)
    
    def test_empty_index_returns_empty_result(self, athena):
        """Empty index returns no sources (not error)."""
        result = athena.query("test question")
        
        assert result.has_sources is False
        assert len(result.sources) == 0
        assert result.question == "test question"
    
    def test_disabled_service_returns_empty_gracefully(self, athena):
        """Disabled service doesn't error."""
        # Should not raise exception
        result = athena.query("anything")
        assert isinstance(result.sources, list)
    
    def test_invalid_query_returns_empty(self, athena):
        """Invalid or empty query returns empty result."""
        result = athena.query("")
        assert isinstance(result.sources, list)
        
        result = athena.query("   ")
        assert isinstance(result.sources, list)
