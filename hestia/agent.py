"""
HEARTH Hestia Agent - Minimal Stub (v0.1)

DISABLED IN v0.1:
- Domain routing and intelligence
- LLM reasoning
- Memory proposals
- Action execution
- Context building
- Planner FSM
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

# DISABLED IN v0.1 — not part of execution spine
# from ..core.kernel import IService, ServiceInfo, ServiceStatus
# from .planner_fsm import PlannerFSM
# from .context_builder import ContextBuilder
# from .ollama_client import OllamaClient
# from .action_router import ActionRouter
# from .memory_proposal import MemoryProposalEngine
# from .domain_router import DomainRouter

from .intent_classifier import IntentClassifier


class AgentResponse(BaseModel):
    """Minimal agent response."""
    response_id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    intent: str = "general"
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    timestamp: datetime = Field(default_factory=datetime.now)


class HestiaAgent:
    """
    Minimal Hestia agent - classifies intent and echoes.
    
    FUTURE: Will include planning, reasoning, memory, actions, domains.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.intent_classifier = IntentClassifier()
    
    async def process(self, user_input: str) -> AgentResponse:
        """
        Minimal processing: classify intent and produce response.
        
        Args:
            user_input: Raw text input from user
            
        Returns:
            AgentResponse with classified intent and echo
        """
        # Classify intent
        classification = await self.intent_classifier.classify(user_input)
        
        # Generate simple response based on intent
        intent = classification["intent"]
        confidence = classification["confidence"]
        
        response_text = self._generate_response(intent, user_input)
        
        return AgentResponse(
            text=response_text,
            intent=intent,
            confidence=confidence
        )
    
    def _generate_response(self, intent: str, user_input: str) -> str:
        """Generate a simple deterministic response."""
        if intent == "greeting":
            return "Hello! HEARTH v0.1 is running in minimal mode."
        elif intent == "help_request":
            return "HEARTH v0.1 - Minimal execution spine. Type any text to see intent classification."
        elif intent == "question":
            return f"You asked: '{user_input}'. Full reasoning is disabled in v0.1."
        elif intent == "information_request":
            return f"Information request received: '{user_input}'. Knowledge retrieval is disabled in v0.1."
        else:
            return f"Received: '{user_input}' (classified as: {intent})"
