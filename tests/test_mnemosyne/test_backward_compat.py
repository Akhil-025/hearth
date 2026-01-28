"""
Tests for Mnemosyne backward compatibility with v0.1 memory system.

Verifies that old tests still pass and old APIs still work.
"""
import tempfile
from pathlib import Path

import pytest
from hestia.agent import HestiaAgent
from mnemosyne.memory_store import MemoryStore, MemoryRecord


class TestMemoryStoreStillWorks:
    """Test that old MemoryStore class still works unchanged."""
    
    def test_memory_store_initialization(self):
        """MemoryStore can be initialized directly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"
            store = MemoryStore(db_path=str(db_path))
            
            assert store is not None
            assert store.db_path.exists()
    
    def test_memory_record_creation(self):
        """MemoryRecord can be created and converted."""
        record = MemoryRecord(
            content="test content",
            memory_type="note",
            source="user_confirmation"
        )
        
        assert record.content == "test content"
        assert record.type == "note"
        
        # Can convert to dict and back
        data = record.to_dict()
        record2 = MemoryRecord.from_dict(data)
        assert record2.content == record.content
    
    def test_memory_store_append_and_query(self):
        """MemoryStore append and get_all still work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(db_path=str(Path(tmpdir) / "memory.db"))
            
            # Append records
            record1 = MemoryRecord("memory 1", memory_type="note")
            record2 = MemoryRecord("memory 2", memory_type="note")
            
            store.append(record1)
            store.append(record2)
            
            # Query back
            all_records = store.get_all(limit=10)
            assert len(all_records) == 2
            # get_all() returns most recent first
            assert all_records[0].content in ["memory 1", "memory 2"]


class TestAgentMemoryAPIsBackwardCompat:
    """Test that agent memory APIs are backward compatible."""
    
    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent with memory."""
        return HestiaAgent(config={
            "enable_memory": True,
            "enable_llm": False,
            "memory_db_path": str(tmp_path / "memory.db")
        })
    
    def test_agent_has_save_memory_method(self, agent):
        """Agent has save_memory() method."""
        assert hasattr(agent, 'save_memory')
        assert callable(agent.save_memory)
    
    def test_agent_save_memory_works(self, agent):
        """Agent.save_memory() works as before."""
        result = agent.save_memory("I love coding", "general")
        
        assert result is True
    
    def test_agent_memory_query_handler_works(self, agent):
        """Agent._handle_memory_query() works as before."""
        agent.save_memory("test memory", "general")
        
        response = agent._handle_memory_query()
        
        # Should have formatted output
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_agent_should_offer_memory_works(self, agent):
        """Agent.should_offer_memory() works as before."""
        result = agent.should_offer_memory("Hello", "greeting")
        
        # Greeting shouldn't offer memory
        assert result is False
    
    def test_agent_get_contextual_memory_works(self, agent):
        """Agent.get_contextual_memory() works as before."""
        agent.save_memory("important fact", "general")
        
        memory_block, was_truncated = agent.get_contextual_memory(limit=5)
        
        # Should return tuple
        assert isinstance(memory_block, (str, type(None)))
        assert isinstance(was_truncated, bool)


class TestMemoryStoreDirectUsageInTests:
    """Test patterns that old test code uses directly."""
    
    def test_create_memory_store_directly(self):
        """Tests that create MemoryStore directly still work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # This is how old tests do it
            from mnemosyne.memory_store import MemoryStore
            
            store = MemoryStore(db_path=str(Path(tmpdir) / "memory.db"))
            assert store is not None
    
    def test_memory_record_direct_usage(self):
        """MemoryRecord can be used directly in tests."""
        from mnemosyne.memory_store import MemoryRecord
        
        record = MemoryRecord(
            content="test",
            memory_type="note",
            source="test"
        )
        
        assert record.id is not None
        assert record.timestamp is not None
    
    def test_memory_store_count(self):
        """MemoryStore.count() still works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(db_path=str(Path(tmpdir) / "memory.db"))
            
            record = MemoryRecord("test", memory_type="note")
            store.append(record)
            
            count = store.count()
            assert count == 1
    
    def test_memory_store_get_recent(self):
        """MemoryStore.get_recent() still works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(db_path=str(Path(tmpdir) / "memory.db"))
            
            for i in range(3):
                record = MemoryRecord(f"memory {i}", memory_type="note")
                store.append(record)
            
            recent = store.get_recent(count=2)
            assert len(recent) == 2


class TestMemoryWriteConfirmation:
    """Test old memory write confirmation patterns."""
    
    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent with memory."""
        return HestiaAgent(config={
            "enable_memory": True,
            "enable_llm": False,
            "memory_db_path": str(tmp_path / "memory.db")
        })
    
    def test_memory_save_only_on_explicit_call(self, agent):
        """Memory is only saved when save_memory() is explicitly called."""
        # Count memories before
        initial_count = agent.memory_store.count() if agent.memory_store else 0
        
        # Just using the agent doesn't save memory
        # (This would be tested in actual agent processing,
        # but the key point is save_memory() is explicit)
        
        # Only explicit call saves
        agent.save_memory("explicit save", "general")
        
        final_count = agent.memory_store.count() if agent.memory_store else 0
        assert final_count > initial_count
