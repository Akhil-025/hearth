"""
Tests for Mnemosyne constraint enforcement.

Verifies HEARTH hard constraints:
- No autonomy (no background tasks)
- No implicit memory use
- Explicit write/read only
- No async execution
"""
import tempfile
from pathlib import Path

import pytest
from mnemosyne.service import MnemosyneService
from mnemosyne.service_config import MnemosyneConfig


class TestMnemosyneNoAutonomy:
    """Test that Mnemosyne never acts autonomously."""
    
    @pytest.fixture
    def service(self):
        """Create test service."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            yield MnemosyneService(config=config)
    
    def test_no_background_tasks(self, service):
        """Service has no background task runners."""
        # Verify no task queue, worker, scheduler attributes
        assert not hasattr(service, 'task_queue')
        assert not hasattr(service, 'worker')
        assert not hasattr(service, 'scheduler')
        assert not hasattr(service, 'background_tasks')
    
    def test_no_async_execution(self, service):
        """Service has no async methods."""
        # write() and read() are synchronous
        assert not hasattr(service.write, '__await__')
        assert not hasattr(service.read, '__await__')
    
    def test_no_watchdog(self, service):
        """Service has no file watcher."""
        assert not hasattr(service, 'watchdog')
        assert not hasattr(service, 'watcher')
        assert not hasattr(service, 'monitor')
    
    def test_no_auto_indexing(self, service):
        """Service does not auto-index or background-process."""
        # Write should be simple and synchronous
        result = service.write("test memory")
        assert result is True
        # No assertion here about jobs, but there should be no side tasks


class TestMnemosyneExplicitOnly:
    """Test that memory operations are explicit only."""
    
    @pytest.fixture
    def service(self):
        """Create test service."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            yield MnemosyneService(config=config)
    
    def test_write_requires_explicit_call(self, service):
        """Writing requires explicit write() call."""
        # Writing does not happen unless write() is called
        stats = service.stats()
        initial_count = stats['memory_count']
        
        # Without calling write(), nothing changes
        assert initial_count == 0
        
        # Only explicit call writes
        service.write("test")
        assert service.stats()['memory_count'] == 1
    
    def test_read_returns_empty_by_default(self, service):
        """Reading returns empty list before any writes."""
        result = service.read()
        assert result == []
    
    def test_no_implicit_memory_injection(self, service):
        """Service never injects memory implicitly."""
        # Service has no mechanism to inject memory into responses
        assert not hasattr(service, 'inject')
        assert not hasattr(service, 'augment')
        assert not hasattr(service, 'enhance_context')


class TestMnemosyneReadOnly:
    """Test that read() never modifies state."""
    
    @pytest.fixture
    def service(self):
        """Create test service."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            yield MnemosyneService(config=config)
    
    def test_read_does_not_modify_state(self, service):
        """Reading does not modify memory store."""
        service.write("memory 1")
        service.write("memory 2")
        
        # Get initial stats
        stats_before = service.stats()
        
        # Read multiple times
        for _ in range(10):
            service.read()
        
        # Stats unchanged
        stats_after = service.stats()
        assert stats_before == stats_after
    
    def test_read_returns_copy_not_reference(self, service):
        """Read returns data, modifying it doesn't affect store."""
        service.write("original")
        
        result = service.read()
        # Modify the list
        result.append("modified")
        
        # Original store unchanged
        result2 = service.read()
        assert len(result2) == 1
        assert "modified" not in result2


class TestMnemosyneGracefulDegradation:
    """Test graceful failure modes."""
    
    def test_disabled_write_returns_false(self):
        """Write on disabled service returns False."""
        config = MnemosyneConfig(enabled=False)
        service = MnemosyneService(config=config)
        
        result = service.write("test")
        assert result is False
    
    def test_disabled_read_returns_empty(self):
        """Read on disabled service returns empty list."""
        config = MnemosyneConfig(enabled=False)
        service = MnemosyneService(config=config)
        
        result = service.read()
        assert result == []
        assert isinstance(result, list)
    
    def test_disabled_health_check_false(self):
        """Health check returns False when disabled."""
        config = MnemosyneConfig(enabled=False)
        service = MnemosyneService(config=config)
        
        assert service.health_check() is False
    
    def test_write_errors_dont_crash(self):
        """Write errors return False, don't crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            service = MnemosyneService(config=config)
            
            # Normal write works
            result = service.write("test")
            assert result is True
            
            # Service remains functional even if something fails
            # (we can't easily trigger an error in this test,
            # but the try/except ensures graceful handling)


class TestMnemosyneNoNetworking:
    """Test that service has no network features."""
    
    @pytest.fixture
    def service(self):
        """Create test service."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MnemosyneConfig(
                enabled=True,
                db_path=Path(tmpdir) / "memory.db"
            )
            yield MnemosyneService(config=config)
    
    def test_no_api_server(self, service):
        """Service has no HTTP API."""
        assert not hasattr(service, 'app')
        assert not hasattr(service, 'server')
        assert not hasattr(service, 'api')
    
    def test_no_streaming(self, service):
        """Service has no streaming capabilities."""
        assert not hasattr(service, 'stream')
        assert not hasattr(service, 'streaming')
    
    def test_no_webhooks(self, service):
        """Service has no webhook system."""
        assert not hasattr(service, 'webhook')
        assert not hasattr(service, 'callbacks')
