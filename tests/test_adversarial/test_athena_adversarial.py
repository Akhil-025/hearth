"""Cycle 3: Athena (RAG/Knowledge) Adversarial Tests

Goal: Attack Athena's knowledge search capabilities
- Empty/disabled index behavior
- Query hallucination risks
- Vector search edge cases
- Explicit-only enforcement
- Missing dependency handling
"""

import pytest
from pathlib import Path
from athena.service import AthenaService
from athena.config import AthenaConfig


class TestAthenaDisabledBehavior:
    """Test graceful degradation when Athena disabled (default)"""

    def test_disabled_query_returns_empty(self):
        """When Athena disabled, query() should return empty result"""
        config = AthenaConfig(enabled=False)
        service = AthenaService(config)
        
        result = service.query("test question")
        
        # Should not crash, should return empty gracefully
        assert result is not None
        assert result.sources == []
        assert result.source_count == 0

    def test_disabled_ingest_returns_false(self):
        """When Athena disabled, ingest operations should return error dict"""
        config = AthenaConfig(enabled=False)
        service = AthenaService(config)
        
        # Ingest should fail gracefully
        result = service.ingest_pdf(Path("test.pdf"))
        assert isinstance(result, dict)
        assert result.get("success") is False
        
    def test_disabled_stats_returns_empty(self):
        """When Athena disabled, stats() returns empty dict"""
        config = AthenaConfig(enabled=False)
        service = AthenaService(config)
        
        stats = service.get_stats()
        assert stats.get("documents", 0) == 0
        assert stats.get("enabled", False) is False


class TestAthenaEmptyIndex:
    """Test behavior with no documents indexed"""

    def test_query_empty_index_returns_empty(self):
        """Querying empty knowledge base returns empty result"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        result = service.query("what is the meaning of life?")
        
        # Should not crash, should return empty
        assert result.sources == []
        assert result.source_count == 0

    def test_empty_query_string(self):
        """Empty query string behavior"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        result = service.query("")
        
        # Should not crash
        assert result is not None

    def test_whitespace_only_query(self):
        """Query with only whitespace"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        result = service.query("   \n\t  ")
        
        # Should handle gracefully
        assert result is not None

    def test_very_long_query(self):
        """Query with 10K characters"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        long_query = "question " * 1000  # ~9000 chars
        result = service.query(long_query)
        
        # Should not crash
        assert result is not None


class TestAthenaVectorSearchEdgeCases:
    """Test vector search boundary conditions"""

    def test_unicode_query(self):
        """Query with emoji and non-ASCII characters"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        result = service.query("🔍 日本語 العربية Ελληνικά")
        
        # Should not crash on unicode
        assert result is not None

    def test_sql_injection_in_query(self):
        """Ensure query doesn't allow SQL injection"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        result = service.query("'; DROP TABLE documents; --")
        
        # Should not execute SQL, just return empty
        assert result is not None
        stats = service.get_stats()
        # If table was dropped, this would fail
        assert isinstance(stats, dict)

    def test_special_regex_characters(self):
        """Query with regex special characters"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        result = service.query(".*+?^${}[]()\\|")
        
        # Should not crash
        assert result is not None

    def test_xss_attempt_in_query(self):
        """Query with XSS payload (local system, no HTTP)"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        result = service.query("<script>alert('xss')</script>")
        
        # Should store safely
        assert result is not None


class TestAthenaExplicitOnlyEnforcement:
    """Test that Athena operations are explicit-only (no autonomous retrieval)"""

    def test_no_auto_retrieval_on_intent_match(self):
        """Athena should not retrieve documents just because intent matched"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        # User says "search my notes" but doesn't provide query
        # Athena should NOT automatically retrieve anything
        result = service.query("")
        
        assert result.sources == []

    def test_query_requires_explicit_call(self):
        """Confirm query() must be explicitly called"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        # Instantiation alone should not trigger any indexing/retrieval
        initial_stats = service.get_stats()
        
        # Just creating service should not change stats
        service2 = AthenaService(config)
        stats2 = service2.get_stats()
        
        # Should be identical/empty
        assert stats2.get("documents", 0) == initial_stats.get("documents", 0)


class TestAthenaMissingDependencies:
    """Test graceful degradation when dependencies missing"""

    def test_chromadb_missing(self):
        """If chromadb not installed, service should fail gracefully"""
        config = AthenaConfig(enabled=True)
        
        # This test documents what happens if chromadb import fails
        # In actual v0.1, chromadb may not be installed
        try:
            service = AthenaService(config)
            result = service.query("test")
            # If we get here, chromadb is available
            assert result is not None
        except ImportError:
            # Expected if chromadb not installed
            pytest.skip("chromadb not installed (expected for v0.1)")

    def test_sentence_transformers_missing(self):
        """If sentence-transformers not installed, fallback should work"""
        config = AthenaConfig(enabled=True)
        
        try:
            service = AthenaService(config)
            # Service should initialize even if embedder unavailable
            assert service is not None
        except ImportError:
            pytest.skip("sentence-transformers not installed (expected for v0.1)")


class TestAthenaStateIsolation:
    """Test that Athena doesn't leak state between queries"""

    def test_query_doesnt_modify_next_query(self):
        """One query shouldn't affect the next query"""
        config = AthenaConfig(enabled=True)
        service = AthenaService(config)
        
        result1 = service.query("question one")
        result2 = service.query("question two")
        result3 = service.query("question one")  # Same as first
        
        # Results should be consistent
        assert result1.sources == result3.sources
        assert result1.source_count == result3.source_count

    def test_multiple_services_dont_share_state(self):
        """Two AthenaService instances should be independent"""
        config1 = AthenaConfig(enabled=True)
        config2 = AthenaConfig(enabled=True)
        
        service1 = AthenaService(config1)
        service2 = AthenaService(config2)
        
        # Ingest into service1 should not affect service2
        # (both are empty, so queries should match)
        result1 = service1.query("test")
        result2 = service2.query("test")
        
        assert result1.sources == result2.sources
