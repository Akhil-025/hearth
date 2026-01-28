"""
Tests for Mnemosyne service functionality.

Verifies pure function behavior, determinism, and no side effects.
"""
import tempfile
from pathlib import Path

import pytest
from mnemosyne.service import MnemosyneService
from mnemosyne.service_config import MnemosyneConfig


class TestMnemosyneServiceBasics:
    """Test basic Mnemosyne service properties."""
    
    @pytest.fixture
    def service_disabled(self):
        """Create service with disabled config."""
        config = MnemosyneConfig(enabled=False)
        return MnemosyneService(config=config)
    
    @pytest.fixture
    def service_enabled(self):
        """Create service with enabled config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            yield MnemosyneService(config=config)
    
    def test_service_initialization(self, service_disabled):
        """Service initializes without errors."""
        assert service_disabled is not None
        assert service_disabled.config is not None
    
    def test_disabled_service_returns_false_on_write(self, service_disabled):
        """Disabled service write() returns False."""
        result = service_disabled.write("test memory")
        assert result is False
    
    def test_disabled_service_returns_empty_on_read(self, service_disabled):
        """Disabled service read() returns empty list."""
        result = service_disabled.read()
        assert result == []
        assert isinstance(result, list)
    
    def test_enabled_service_writes_memory(self, service_enabled):
        """Enabled service can write memory."""
        result = service_enabled.write("test memory content")
        assert result is True
    
    def test_enabled_service_reads_memory(self, service_enabled):
        """Enabled service can read memory."""
        service_enabled.write("memory 1")
        service_enabled.write("memory 2")
        
        result = service_enabled.read(limit=10)
        assert len(result) == 2
        # Should be most recent first
        assert result[0] == "memory 2"
        assert result[1] == "memory 1"
    
    def test_write_returns_true_on_success(self, service_enabled):
        """Write returns True on successful write."""
        assert service_enabled.write("test") is True
    
    def test_write_with_metadata(self, service_enabled):
        """Write accepts optional metadata."""
        result = service_enabled.write(
            "test",
            memory_type="note",
            metadata={"source": "test"}
        )
        assert result is True
    
    def test_read_respects_limit(self, service_enabled):
        """Read respects the limit parameter."""
        # Write 5 memories
        for i in range(5):
            service_enabled.write(f"memory {i}")
        
        # Read with limit
        result = service_enabled.read(limit=2)
        assert len(result) == 2
    
    def test_read_returns_strings(self, service_enabled):
        """Read returns list of strings, not record objects."""
        service_enabled.write("test memory")
        result = service_enabled.read()
        
        assert len(result) > 0
        assert isinstance(result[0], str)


class TestMnemosyneStats:
    """Test service statistics."""
    
    def test_disabled_service_stats(self):
        """Stats for disabled service."""
        config = MnemosyneConfig(enabled=False)
        service = MnemosyneService(config=config)
        
        stats = service.stats()
        assert stats["enabled"] is False
        assert stats["memory_count"] == 0
    
    def test_enabled_service_stats(self):
        """Stats for enabled service."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            service = MnemosyneService(config=config)
            service.write("test 1")
            service.write("test 2")
            
            stats = service.stats()
            assert stats["enabled"] is True
            assert stats["memory_count"] == 2


class TestMnemosyneHealthCheck:
    """Test service health checking."""
    
    def test_disabled_service_not_healthy(self):
        """Disabled service reports not healthy."""
        config = MnemosyneConfig(enabled=False)
        service = MnemosyneService(config=config)
        
        assert service.health_check() is False
    
    def test_enabled_service_is_healthy(self):
        """Enabled service reports healthy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            service = MnemosyneService(config=config)
            
            assert service.health_check() is True


class TestMnemosyneBackwardCompat:
    """Test v0.1 backward compatibility methods."""
    
    def test_save_method_exists(self):
        """Legacy save() method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            service = MnemosyneService(config=config)
            
            assert hasattr(service, 'save')
            assert callable(service.save)
    
    def test_save_redirects_to_write(self):
        """Legacy save() redirects to write()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            service = MnemosyneService(config=config)
            
            result = service.save("test memory", memory_type="note")
            assert result is True
            
            # Verify it was written
            memories = service.read()
            assert len(memories) == 1
            assert "test memory" in memories
    
    def test_query_recent_exists(self):
        """Legacy query_recent() method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            service = MnemosyneService(config=config)
            
            assert hasattr(service, 'query_recent')
            assert callable(service.query_recent)
    
    def test_query_recent_redirects_to_read(self):
        """Legacy query_recent() redirects to read()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            service = MnemosyneService(config=config)
            service.write("test 1")
            service.write("test 2")
            
            result = service.query_recent(limit=10)
            assert len(result) == 2
            assert isinstance(result, list)


class TestMnemosyneDeterminism:
    """Test deterministic behavior."""
    
    def test_same_read_same_result(self):
        """Same read query gives same result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"
            
            config = MnemosyneConfig(enabled=True, db_path=db_path)
            service = MnemosyneService(config=config)
            
            # Write some data
            service.write("memory 1")
            service.write("memory 2")
            
            # Read twice
            result1 = service.read(limit=5)
            result2 = service.read(limit=5)
            
            # Should be identical
            assert result1 == result2
    
    def test_read_no_side_effects(self):
        """Reading has no side effects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            service = MnemosyneService(config=config)
            
            service.write("test")
            stats_before = service.stats()
            
            # Read multiple times
            service.read()
            service.read()
            service.read()
            
            stats_after = service.stats()
            
            # Stats should not change
            assert stats_before == stats_after
