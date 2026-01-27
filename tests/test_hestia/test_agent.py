"""
Test Hestia agent functionality.
"""
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ...hestia.agent import HestiaAgent, UserInput
from ...hestia.intent_classifier import IntentClassifier
from ...hestia.ollama_client import OllamaClient


@pytest.mark.asyncio
async def test_agent_initialization():
    """Test agent initialization."""
    agent = HestiaAgent()
    
    assert agent.state.current_session is None
    assert not agent.state.active_conversation
    assert len(agent.state.context_window) == 0


@pytest.mark.asyncio
async def test_agent_start_stop(hestia_agent: HestiaAgent):
    """Test agent startup and shutdown."""
    # Already started by fixture
    info = hestia_agent.get_service_info()
    assert info.status.value == "running"
    
    # Health check should pass
    healthy = await hestia_agent.health_check()
    assert healthy
    
    # Stop agent
    await hestia_agent.stop()
    info = hestia_agent.get_service_info()
    assert info.status.value == "stopped"


@pytest.mark.asyncio
async def test_process_input_with_mocks():
    """Test input processing with mocked components."""
    # Create agent with mocked components
    agent = HestiaAgent()
    
    # Mock components
    agent.intent_classifier.classify = AsyncMock(return_value="greeting")
    agent.planner.create_plan = AsyncMock()
    agent.context_builder.build = AsyncMock(return_value={"context": "test"})
    agent.llm_client.reason = AsyncMock()
    agent.action_router.execute = AsyncMock()
    agent.memory_proposal_engine.create_proposals = AsyncMock(return_value=[])
    
    # Mock LLM response
    mock_response = Mock()
    mock_response.response = "Hello! I'm doing well."
    mock_response.confidence = 0.9
    mock_response.actions = []
    agent.llm_client.reason.return_value = mock_response
    
    # Create user input
    user_input = UserInput(
        text="Hello, how are you?",
        session_id="test_session",
        user_id="test_user"
    )
    
    # Process input
    response = await agent.process_input(user_input)
    
    # Verify response
    assert response.session_id == "test_session"
    assert response.user_id == "test_user"
    assert "Hello" in response.text
    assert response.confidence == 0.9
    
    # Verify component calls
    agent.intent_classifier.classify.assert_called_once_with("Hello, how are you?")
    agent.llm_client.reason.assert_called_once()


@pytest.mark.asyncio
async def test_conversation_history(hestia_agent: HestiaAgent):
    """Test conversation history management."""
    user_input = UserInput(
        text="Test message",
        session_id="test_session",
        user_id="test_user"
    )
    
    # Mock processing to avoid actual LLM calls
    with patch.object(hestia_agent.llm_client, 'reason'):
        mock_response = Mock()
        mock_response.response = "Test response"
        mock_response.confidence = 0.8
        mock_response.actions = []
        hestia_agent.llm_client.reason.return_value = mock_response
        
        await hestia_agent.process_input(user_input)
    
    # Check context window
    assert len(hestia_agent.state.context_window) == 1
    assert hestia_agent.state.context_window[0]["user_input"] == "Test message"
    
    # Get conversation history
    history = await hestia_agent.get_conversation_history("test_session")
    assert len(history) == 1
    
    # Clear session
    success = await hestia_agent.clear_session("test_session")
    assert success
    assert len(hestia_agent.state.context_window) == 0


@pytest.mark.asyncio
async def test_agent_with_actions():
    """Test agent with action execution."""
    agent = HestiaAgent()
    
    # Mock components
    agent.intent_classifier.classify = AsyncMock(return_value="query_memory")
    agent.planner.create_plan = AsyncMock()
    agent.context_builder.build = AsyncMock(return_value={"context": "test"})
    
    # Mock LLM response with actions
    mock_response = Mock()
    mock_response.response = "I'll check your memories."
    mock_response.confidence = 0.8
    mock_response.actions = [
        {
            "type": "query_memory",
            "parameters": {"category": "preferences"},
            "confidence": 0.9
        }
    ]
    agent.llm_client.reason.return_value = mock_response
    
    # Mock action execution
    agent.action_router.execute = AsyncMock(return_value={"success": True, "results": []})
    agent.memory_proposal_engine.create_proposals = AsyncMock(return_value=[])
    
    # Create user input
    user_input = UserInput(
        text="What are my preferences?",
        session_id="test_session",
        user_id="test_user"
    )
    
    # Process input
    response = await agent.process_input(user_input)
    
    # Verify actions were executed
    assert len(response.actions_executed) == 1
    assert response.actions_executed[0]["action"]["type"] == "query_memory"
    assert agent.action_router.execute.called


@pytest.mark.asyncio
async def test_error_handling():
    """Test agent error handling."""
    agent = HestiaAgent()
    
    # Mock component to raise exception
    agent.intent_classifier.classify = AsyncMock(side_effect=Exception("Test error"))
    
    user_input = UserInput(
        text="Test message",
        session_id="test_session",
        user_id="test_user"
    )
    
    # Should raise exception
    with pytest.raises(Exception):
        await agent.process_input(user_input)