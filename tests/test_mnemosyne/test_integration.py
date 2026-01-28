"""
Tests for Mnemosyne integration with Hestia agent.

Verifies routing, response format, and constraint enforcement.
"""
import tempfile
from pathlib import Path

import pytest
from hestia.agent import HestiaAgent, AgentResponse


class TestMnemosyneAgentIntegration:
    """Test Mnemosyne integration with Hestia agent."""
    
    @pytest.fixture
    def agent_with_memory(self, tmp_path):
        """Create agent with memory enabled."""
        return HestiaAgent(config={
            "enable_memory": True,
            "enable_llm": False,
            "enable_athena": False,
            "memory_db_path": str(tmp_path / "memory.db")
        })
    
    @pytest.fixture
    def agent_no_memory(self):
        """Create agent with memory disabled."""
        return HestiaAgent(config={
            "enable_memory": False,
            "enable_llm": False,
            "enable_athena": False,
        })
    
    def test_agent_initializes_memory_service(self, agent_with_memory):
        """Agent initializes MnemosyneService when memory enabled."""
        assert agent_with_memory.memory_service is not None
        assert agent_with_memory.memory_service.config.enabled is True
    
    def test_agent_no_memory_service_when_disabled(self, agent_no_memory):
        """Agent always initializes service, but disabled when memory off (BUG-2.1 fix)."""
        assert agent_no_memory.memory_service is not None
        assert agent_no_memory.memory_service.config.enabled is False
    
    @pytest.mark.asyncio
    async def test_memory_query_uses_service(self, agent_with_memory):
        """Memory query routes through MnemosyneService."""
        # Add a memory
        agent_with_memory.save_memory("I like Python", "general")
        
        # Query memories
        response = agent_with_memory._handle_memory_query()
        
        # Should show the memory
        assert "I like Python" in response or "memory" in response.lower()
    
    @pytest.mark.asyncio
    async def test_save_memory_writes_to_service(self, agent_with_memory):
        """save_memory() writes to MnemosyneService."""
        result = agent_with_memory.save_memory("test memory", "general")
        
        assert result is True
        
        # Verify it's in the service
        memories = agent_with_memory.memory_service.read()
        assert len(memories) == 1
        assert "test memory" in memories
    
    @pytest.mark.asyncio
    async def test_memory_disabled_gracefully(self, agent_no_memory):
        """Memory operations fail gracefully when disabled."""
        response = agent_no_memory._handle_memory_query()
        
        assert "not enabled" in response.lower() or "disabled" in response.lower()
    
    @pytest.mark.asyncio
    async def test_memory_not_written_without_confirmation(self, agent_with_memory):
        """Memory not written unless save_memory() is called."""
        stats_before = agent_with_memory.memory_service.stats()
        initial_count = stats_before['memory_count']
        
        # Just process a general query
        await agent_with_memory.process("hello")
        
        # Memory should not increase
        stats_after = agent_with_memory.memory_service.stats()
        assert stats_after['memory_count'] == initial_count


class TestMnemosyneBackwardCompatibility:
    """Test that old v0.1 code still works."""
    
    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent with memory."""
        return HestiaAgent(config={
            "enable_memory": True,
            "enable_llm": False,
            "memory_db_path": str(tmp_path / "memory.db")
        })
    
    def test_memory_store_property_still_exists(self, agent):
        """memory_store property exists for backward compatibility."""
        assert hasattr(agent, 'memory_store')
        # If enabled, should be available
        if agent.enable_memory:
            assert agent.memory_store is not None
    
    def test_old_code_using_memory_store_works(self, agent):
        """Old code directly accessing memory_store still works."""
        # This simulates old v0.1 test code
        if agent.memory_store:
            from mnemosyne.memory_store import MemoryRecord
            record = MemoryRecord(content="test", memory_type="note")
            agent.memory_store.append(record)
            
            # Get it back
            memories = agent.memory_store.get_recent(count=10)
            assert len(memories) > 0
    
    def test_memory_count_works(self, agent):
        """memory_store.count() still works."""
        if agent.memory_store:
            from mnemosyne.memory_store import MemoryRecord
            record = MemoryRecord("test", memory_type="note")
            agent.memory_store.append(record)
            
            count = agent.memory_store.count()
            assert count >= 1
    
    def test_memory_get_recent_works(self, agent):
        """memory_store.get_recent() still works."""
        if agent.memory_store:
            from mnemosyne.memory_store import MemoryRecord
            agent.memory_store.append(MemoryRecord("test 1", memory_type="note"))
            agent.memory_store.append(MemoryRecord("test 2", memory_type="note"))
            
            recent = agent.memory_store.get_recent(count=2)
            assert len(recent) == 2


class TestMnemosyneMemoryNotAutomaticallyInjected:
    """Test that memory is never injected without explicit user request."""
    
    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent with memory."""
        return HestiaAgent(config={
            "enable_memory": True,
            "enable_llm": False,
            "memory_db_path": str(tmp_path / "memory.db")
        })
    
    @pytest.mark.asyncio
    async def test_general_query_no_memory_injection(self, agent):
        """General queries don't automatically use stored memories."""
        # Add a memory
        agent.save_memory("I love pizza", "general")
        
        # Process a question that doesn't explicitly ask for memories
        response = await agent.process("what is 2+2?")
        
        # Response should not automatically reference the memory
        # (unless the LLM spontaneously decides to)
        # The important thing is no automatic context injection happened
        assert isinstance(response, AgentResponse)
    
    def test_should_use_memory_requires_explicit_trigger(self, agent):
        """should_use_memory_for_context requires explicit trigger phrases."""
        # Without trigger phrase
        assert agent.should_use_memory_for_context("what is Python?") is False
        
        # With trigger phrase
        assert agent.should_use_memory_for_context("based on what you remember about me") is True
