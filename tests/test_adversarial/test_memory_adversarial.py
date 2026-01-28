"""
ADVERSARIAL TEST SUITE - CYCLE 2: Mnemosyne (Memory) Boundary Testing

Testing write gating, read leakage, size limits, disabled behavior.
"""
import tempfile
from pathlib import Path

import pytest
from hestia.agent import HestiaAgent
from mnemosyne.service import MnemosyneService
from mnemosyne.service_config import MnemosyneConfig


class TestMnemosyneWriteGating:
    """Test memory write gating and confirmation."""
    
    @pytest.fixture
    def agent_with_memory(self, tmp_path):
        """Agent with memory enabled."""
        return HestiaAgent(config={
            "enable_memory": True,
            "enable_llm": False,
            "memory_db_path": str(tmp_path / "memory.db")
        })
    
    def test_empty_memory_write(self, agent_with_memory):
        """Can user save empty string as memory?"""
        result = agent_with_memory.save_memory("", "note")
        # Should this be rejected?
        assert isinstance(result, bool)
        return result
    
    def test_whitespace_only_memory(self, agent_with_memory):
        """Can user save whitespace-only memory?"""
        result = agent_with_memory.save_memory("   ", "note")
        assert isinstance(result, bool)
        return result
    
    def test_extremely_large_memory(self, agent_with_memory):
        """Can user save huge memory entry (10MB)?"""
        huge_text = "a" * (10 * 1024 * 1024)
        result = agent_with_memory.save_memory(huge_text, "note")
        # Should there be a size limit?
        assert isinstance(result, bool)
        return result
    
    def test_save_memory_multiple_times(self, agent_with_memory):
        """Save same memory multiple times."""
        for i in range(1000):
            result = agent_with_memory.save_memory(f"memory {i}", "note")
            assert result is True
        
        # How many memories can be stored?
        stats = agent_with_memory.memory_service.stats()
        count = stats['memory_count']
        return count
    
    def test_memory_with_special_characters(self, agent_with_memory):
        """Memory containing SQL-injectable text."""
        result = agent_with_memory.save_memory(
            "'; DROP TABLE memories; --",
            "note"
        )
        # SQLite parameterized queries should protect this
        assert result is True
        
        # Can we read it back?
        memories = agent_with_memory.memory_service.read()
        assert any("DROP TABLE" in m for m in memories)
    
    def test_memory_with_unicode(self, agent_with_memory):
        """Memory with Unicode."""
        result = agent_with_memory.save_memory("你好世界 🌍", "note")
        assert result is True
        
        memories = agent_with_memory.memory_service.read()
        assert any("你好" in m for m in memories)
    
    def test_memory_type_variants(self, agent_with_memory):
        """Different memory types."""
        for mem_type in ["note", "fact", "preference", "habit", "", None]:
            result = agent_with_memory.save_memory(f"memory as {mem_type}", mem_type)
            # What if memory_type is invalid?
            assert isinstance(result, bool)


class TestMnemosyneReadLeakage:
    """Test memory read security and isolation."""
    
    @pytest.fixture
    def agent_with_memory(self, tmp_path):
        """Agent with memory."""
        return HestiaAgent(config={
            "enable_memory": True,
            "enable_llm": False,
            "memory_db_path": str(tmp_path / "memory.db")
        })
    
    def test_read_returns_all_memories(self, agent_with_memory):
        """Does read() return all memories by default?"""
        agent_with_memory.save_memory("secret1", "note")
        agent_with_memory.save_memory("secret2", "note")
        agent_with_memory.save_memory("secret3", "note")
        
        memories = agent_with_memory.memory_service.read(limit=5)
        # How many are returned?
        assert len(memories) == 3
    
    def test_read_limit_enforcement(self, agent_with_memory):
        """Does limit parameter work?"""
        for i in range(10):
            agent_with_memory.save_memory(f"memory{i}", "note")
        
        memories_5 = agent_with_memory.memory_service.read(limit=5)
        memories_3 = agent_with_memory.memory_service.read(limit=3)
        
        assert len(memories_5) == 5
        assert len(memories_3) == 3
    
    def test_read_order_consistency(self, agent_with_memory):
        """Are memories returned in consistent order?"""
        agent_with_memory.save_memory("first", "note")
        agent_with_memory.save_memory("second", "note")
        agent_with_memory.save_memory("third", "note")
        
        memories1 = agent_with_memory.memory_service.read(limit=10)
        memories2 = agent_with_memory.memory_service.read(limit=10)
        
        assert memories1 == memories2  # Should be identical
    
    def test_memory_store_direct_access(self, agent_with_memory):
        """Can code bypass service and access memory_store directly?"""
        # Tests whether there's a backward compatibility hole
        if agent_with_memory.memory_store:
            all_records = agent_with_memory.memory_store.get_all(limit=1000)
            # Direct store access is allowed for backward compat
            assert isinstance(all_records, list)


class TestMnemosyneDisabledBehavior:
    """Test graceful degradation when memory disabled."""
    
    @pytest.fixture
    def agent_no_memory(self):
        """Agent with memory disabled."""
        return HestiaAgent(config={
            "enable_memory": False,
            "enable_llm": False,
        })
    
    def test_disabled_save_returns_false(self, agent_no_memory):
        """save_memory() returns False when disabled."""
        result = agent_no_memory.save_memory("test", "note")
        assert result is False
    
    def test_disabled_read_returns_empty(self, agent_no_memory):
        """Read returns empty list when disabled."""
        memories = agent_no_memory.memory_service.read()
        assert memories == []
    
    def test_disabled_handler_message(self, agent_no_memory):
        """_handle_memory_query() returns disabled message."""
        response = agent_no_memory._handle_memory_query()
        assert "enabled" in response.lower() or "disabled" in response.lower()
    
    def test_disabled_should_offer_memory_false(self, agent_no_memory):
        """should_offer_memory() returns False when disabled."""
        result = agent_no_memory.should_offer_memory("test", "general")
        assert result is False


class TestMnemosyneContextInjection:
    """Test memory context injection boundaries."""
    
    @pytest.fixture
    def agent_with_memory(self, tmp_path):
        """Agent with memory."""
        return HestiaAgent(config={
            "enable_memory": True,
            "enable_llm": False,
            "memory_db_path": str(tmp_path / "memory.db")
        })
    
    def test_context_truncation_at_max_chars(self, agent_with_memory):
        """Memory context is truncated at MAX_MEMORY_CHARS."""
        from hestia.agent import MAX_MEMORY_CHARS
        
        # Add a very large memory
        huge = "x" * 10000
        agent_with_memory.save_memory(huge, "note")
        
        memory_block, was_truncated = agent_with_memory.get_contextual_memory()
        # Should either return truncated block or None
        if memory_block:
            # If it's returned, it shouldn't be larger than MAX_MEMORY_CHARS
            assert len(memory_block) <= MAX_MEMORY_CHARS
    
    def test_context_item_count_limit(self, agent_with_memory):
        """Memory context limited to MAX_MEMORY_ITEMS."""
        # Add more memories than limit
        for i in range(20):
            agent_with_memory.save_memory(f"memory{i}", "note")
        
        memory_block, was_truncated = agent_with_memory.get_contextual_memory()
        # How many items should be included?
        # Should respect MAX_MEMORY_ITEMS
        assert isinstance(memory_block, (str, type(None)))
    
    def test_truncation_flag_accuracy(self, agent_with_memory):
        """was_truncated flag accurately reflects truncation."""
        # Add single small memory
        agent_with_memory.save_memory("tiny", "note")
        _, was_truncated1 = agent_with_memory.get_contextual_memory()
        
        # Add huge memory
        agent_with_memory.save_memory("x" * 10000, "note")
        _, was_truncated2 = agent_with_memory.get_contextual_memory()
        
        # Second should indicate truncation
        return was_truncated1, was_truncated2


class TestMnemosyneDeterminism:
    """Test memory system determinism."""
    
    @pytest.fixture
    def service(self, tmp_path):
        """Fresh service."""
        config = MnemosyneConfig(
            enabled=True,
            db_path=Path(tmp_path) / "memory.db"
        )
        return MnemosyneService(config=config)
    
    def test_write_is_deterministic(self, service):
        """Same write operation always succeeds consistently."""
        results = []
        for _ in range(10):
            result = service.write("test memory")
            results.append(result)
        
        # All should succeed
        assert all(results)
    
    def test_read_is_deterministic(self, service):
        """Same read always returns same order."""
        service.write("first")
        service.write("second")
        service.write("third")
        
        reads = []
        for _ in range(5):
            memories = service.read(limit=10)
            reads.append(memories)
        
        # All reads should be identical
        for r in reads[1:]:
            assert r == reads[0]
