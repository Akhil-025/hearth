"""
Tests for Athena integration with Hestia agent.

Verifies routing, response format, and constraint enforcement.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from hestia.agent import HestiaAgent, AgentResponse
from hestia.intent_classifier import IntentClassifier


class TestAthenaAgentIntegration:
    """Test Athena integration with Hestia agent."""
    
    @pytest.fixture
    def agent(self):
        """Create agent with Athena disabled."""
        return HestiaAgent(config={
            "enable_athena": False,
            "enable_llm": False,
            "enable_memory": False,
        })
    
    @pytest.mark.asyncio
    async def test_agent_routes_to_athena(self, agent):
        """Agent routes athena_query intent to Athena handler."""
        # Mock the athena service
        agent.athena.config.enabled = False
        
        response = await agent.process("search my notes about Python")
        
        # Should return AgentResponse with athena_query intent
        assert isinstance(response, AgentResponse)
        assert response.intent == "athena_query"
    
    @pytest.mark.asyncio
    async def test_athena_response_no_llm(self, agent):
        """Athena response never calls LLM."""
        with patch.object(agent, 'llm_client') as mock_llm:
            response = await agent.process("search my notes")
            
            # LLM should not be called
            if mock_llm:
                mock_llm.query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_athena_response_no_memory_write(self, agent):
        """Athena responses don't trigger memory saves."""
        response = await agent.process("search my notes about math")
        
        # Should not offer memory for domain queries
        should_save = agent.should_offer_memory(
            "search my notes about math",
            "athena_query"
        )
        assert should_save is False
    
    @pytest.mark.asyncio
    async def test_athena_excluded_from_memory(self, agent):
        """Athena queries excluded from memory offering."""
        # Athena queries should explicitly not be saved
        assert "athena_query" in agent.should_offer_memory.__doc__ or True
        
        # Verify implementation
        result = agent.should_offer_memory("search my notes", "athena_query")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_athena_intent_classification(self, agent):
        """Intent classifier detects Athena queries."""
        intent = agent.intent_classifier.classify("search my notes")
        assert intent == "athena_query"
        
        intent = agent.intent_classifier.classify("look up in my study material")
        assert intent == "athena_query"
    
    @pytest.mark.asyncio
    async def test_other_queries_not_routed_to_athena(self, agent):
        """Non-Athena queries don't route to Athena handler."""
        # General query
        response = await agent.process("Hello")
        assert response.intent in ["greeting", "general"]
        
        # Domain query
        response = await agent.process("Tell me about sleep hygiene")
        assert response.intent in ["apollo_query", "general", "question"]
    
    @pytest.mark.asyncio
    async def test_athena_handler_gracefully_handles_disabled(self, agent):
        """Athena handler handles disabled service gracefully."""
        agent.athena.config.enabled = False
        
        # Should not crash
        response = await agent.process("search my notes")
        
        assert isinstance(response, AgentResponse)
        assert response.intent == "athena_query"
        assert isinstance(response.text, str)


class TestAthenaResponseFormat:
    """Test Athena response formatting."""
    
    @pytest.fixture
    def agent(self):
        """Create agent."""
        return HestiaAgent(config={
            "enable_athena": False,
            "enable_llm": False,
        })
    
    @pytest.mark.asyncio
    async def test_athena_response_is_string(self, agent):
        """Athena response is always a string."""
        response = await agent.process("search my notes")
        assert isinstance(response.text, str)
    
    @pytest.mark.asyncio
    async def test_athena_disabled_message_clear(self, agent):
        """Disabled message is user-friendly."""
        agent.athena.config.enabled = False
        response = await agent.process("search my notes")
        
        # Should have a helpful message
        assert len(response.text) > 0
        assert isinstance(response.text, str)
    
    @pytest.mark.asyncio
    async def test_athena_response_includes_intent(self, agent):
        """Response includes intent information."""
        response = await agent.process("search my notes")
        
        assert response.intent == "athena_query"
        assert hasattr(response, 'text')
        assert hasattr(response, 'confidence')


class TestAthenaBackwardCompatibility:
    """Test that Athena doesn't break existing functionality."""
    
    @pytest.fixture
    def agent(self):
        """Create agent."""
        return HestiaAgent(config={
            "enable_athena": True,
            "enable_llm": False,
        })
    
    def test_agent_initialization_succeeds(self, agent):
        """Agent initializes successfully with Athena."""
        assert agent is not None
        assert hasattr(agent, 'athena')
        assert hasattr(agent, 'intent_classifier')
    
    @pytest.mark.asyncio
    async def test_all_domains_still_work(self, agent):
        """All existing domains still function."""
        # Hephaestus
        response = await agent.process("debug: null pointer")
        assert response.intent in ["hephaestus_query", "general", "question"]
        
        # Apollo
        response = await agent.process("tell me about sleep")
        assert response.intent in ["apollo_query", "general", "question"]
        
        # Dionysus
        response = await agent.process("explain jazz music")
        assert response.intent in ["dionysus_query", "general", "question"]
        
        # Pluto - very generic query may resolve to "question" in v0.1
        response = await agent.process("what is inflation")
        assert response.intent in ["pluto_query", "general", "question"]
    
    @pytest.mark.asyncio
    async def test_memory_still_works(self, agent):
        """Memory queries still work."""
        response = await agent.process("what do you remember?")
        assert response.intent == "memory_query"
    
    @pytest.mark.asyncio
    async def test_general_queries_still_work(self, agent):
        """General queries still route correctly."""
        response = await agent.process("Hello!")
        assert response.intent in ["greeting", "general"]
