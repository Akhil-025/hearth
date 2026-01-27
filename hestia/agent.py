"""
Hestia - Updated with Domain Intelligence Integration
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from ..core.kernel import IService, ServiceInfo, ServiceStatus
from ..shared.logging.structured_logger import StructuredLogger
from ..shared.schemas.memory import MemoryProposal, MemoryType

from .intent_classifier import IntentClassifier
from .planner_fsm import PlannerFSM, PlannerState
from .context_builder import ContextBuilder
from .ollama_client import OllamaClient
from .action_router import ActionRouter
from .memory_proposal import MemoryProposalEngine
from .domain_router import DomainRouter, DomainCapability  # NEW


class DomainIntent(BaseModel):
    """Intent classification with domain routing."""
    primary_intent: str
    domain_capability: Optional[DomainCapability] = None
    requires_domain: bool = False
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    class Config:
        use_enum_values = True


class AgentResponse(BaseModel):
    """Updated agent response with domain results."""
    response_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    user_id: str
    text: str
    actions_executed: List[Dict[str, Any]] = Field(default_factory=list)
    domain_results: List[Dict[str, Any]] = Field(default_factory=list)  # NEW
    memory_proposals: List[MemoryProposal] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    processing_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class HestiaAgent(IService):
    """
    Hestia Personal Agent - Updated with domain intelligence routing.
    
    Now integrates domain modules for specialized intelligence.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = StructuredLogger(__name__)
        
        # Core components
        self.intent_classifier = IntentClassifier()
        self.planner = PlannerFSM()
        self.context_builder = ContextBuilder()
        self.llm_client = OllamaClient()
        self.action_router = ActionRouter()
        self.memory_proposal_engine = MemoryProposalEngine()
        
        # NEW: Domain router
        self.domain_router: Optional[DomainRouter] = None
        
        # State
        self.state = AgentState()
        self.service_info = ServiceInfo(
            name="hestia",
            version="0.2.0",  # Updated version
            dependencies=["mnemosyne", "athena", "pluto"]
        )
        
        self.logger.info("Hestia agent initialized with domain support")
    
    async def start(self) -> None:
        """Start the agent service with domain discovery."""
        self.service_info.status = ServiceStatus.STARTING
        
        # Initialize components
        await self.llm_client.initialize()
        await self.action_router.initialize()
        
        # Initialize domain router
        from ..core.service_registry import ServiceRegistry
        service_registry = ServiceRegistry()  # TODO: Get from kernel
        
        self.domain_router = DomainRouter(service_registry)
        await self.domain_router.discover_domains()
        
        self.service_info.status = ServiceStatus.RUNNING
        self.logger.info(
            "Hestia agent started with domains",
            domain_count=len(self.domain_router.domains)
        )
    
    async def stop(self) -> None:
        """Stop the agent service."""
        self.service_info.status = ServiceStatus.STOPPING
        
        # Cleanup
        await self.llm_client.cleanup()
        await self.action_router.cleanup()
        
        self.service_info.status = ServiceStatus.STOPPED
        self.state = AgentState()
        self.logger.info("Hestia agent stopped")
    
    def get_service_info(self) -> ServiceInfo:
        return self.service_info
    
    async def health_check(self) -> bool:
        checks = [
            await self.llm_client.health_check(),
            await self.action_router.health_check(),
        ]
        return all(checks)
    
    async def process_input(self, user_input: UserInput) -> AgentResponse:
        """
        Updated processing pipeline with domain intelligence.
        
        New pipeline:
        1. Intent Classification (with domain detection)
        2. Domain Routing (if applicable)
        3. Planning (FSM)
        4. Context Assembly (including domain results)
        5. LLM Reasoning (synthesizing domain insights)
        6. Action Execution
        7. Memory Proposal (including domain proposals)
        """
        start_time = datetime.now()
        self.state.last_activity = start_time
        
        self.logger.info(
            "Processing user input with domain support",
            user_id=user_input.user_id,
            session_id=user_input.session_id
        )
        
        # 1. Intent Classification with domain detection
        domain_intent = await self._classify_intent_with_domain(user_input.text)
        
        # 2. Domain Processing (if applicable)
        domain_results = []
        if domain_intent.requires_domain and domain_intent.domain_capability:
            try:
                domain_result = await self._process_with_domain(
                    domain_intent.domain_capability,
                    user_input
                )
                domain_results.append(domain_result)
                
                self.logger.debug(
                    "Domain processing complete",
                    capability=domain_intent.domain_capability.value,
                    confidence=domain_result.confidence
                )
                
            except Exception as e:
                self.logger.error(
                    "Domain processing failed",
                    capability=domain_intent.domain_capability.value,
                    error=str(e)
                )
                # Continue without domain results
        
        # 3. Planning (updated with domain context)
        plan = await self.planner.create_plan(
            domain_intent.primary_intent,
            user_input,
            domain_context=domain_results
        )
        
        # 4. Context Assembly (including domain results)
        context = await self.context_builder.build(
            user_input=user_input,
            intent=domain_intent.primary_intent,
            plan=plan,
            domain_results=domain_results  # NEW
        )
        
        # Update state with domain context
        self.state.context_window.append({
            "timestamp": user_input.timestamp,
            "user_input": user_input.text,
            "intent": domain_intent.primary_intent,
            "domain_used": bool(domain_results)
        })
        
        # 5. LLM Reasoning (synthesize domain insights)
        llm_response = await self.llm_client.reason(
            user_input=user_input.text,
            context=context,
            intent=domain_intent.primary_intent,
            plan=plan,
            domain_insights=[r.structured_output for r in domain_results]  # NEW
        )
        
        # 6. Action Execution
        executed_actions = []
        if llm_response.actions:
            for action in llm_response.actions:
                result = await self.action_router.execute(action)
                executed_actions.append({
                    "action": action,
                    "result": result
                })
        
        # 7. Memory Proposals (including from domains)
        memory_proposals = await self.memory_proposal_engine.create_proposals(
            user_input=user_input,
            intent=domain_intent.primary_intent,
            llm_response=llm_response,
            executed_actions=executed_actions,
            context=context,
            domain_results=domain_results  # NEW
        )
        
        # Add domain memory proposals
        for domain_result in domain_results:
            memory_proposals.extend(domain_result.memory_proposals)
        
        # 8. Generate Response (synthesizing domain insights)
        response_text = self._synthesize_response(
            llm_response.response,
            domain_results,
            executed_actions
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Create response
        response = AgentResponse(
            session_id=user_input.session_id,
            user_id=user_input.user_id,
            text=response_text,
            actions_executed=executed_actions,
            domain_results=[r.dict() for r in domain_results],  # NEW
            memory_proposals=memory_proposals,
            confidence=llm_response.confidence * domain_intent.confidence,
            processing_time_ms=processing_time
        )
        
        self.logger.info(
            "Response generated with domain support",
            response_id=response.response_id,
            domain_results=len(domain_results),
            memory_proposals=len(memory_proposals)
        )
        
        return response
    
    async def _classify_intent_with_domain(self, text: str) -> DomainIntent:
        """
        Classify intent with domain capability detection.
        
        Uses rule-based matching to detect domain-specific requests.
        """
        # First, get basic intent
        basic_intent = await self.intent_classifier.classify(text)
        
        # Check for domain-specific patterns
        domain_capability = self._detect_domain_capability(text)
        
        return DomainIntent(
            primary_intent=basic_intent,
            domain_capability=domain_capability,
            requires_domain=domain_capability is not None,
            confidence=0.8
        )
    
    def _detect_domain_capability(self, text: str) -> Optional[DomainCapability]:
        """Detect domain capability from text using rule-based matching."""
        text_lower = text.lower()
        
        # Hermes patterns (communication)
        hermes_patterns = {
            DomainCapability.DRAFT_MESSAGE: [
                "draft", "write", "compose", "message", "email", "letter",
                "how to say", "what should i write"
            ],
            DomainCapability.ANALYZE_TONE: [
                "tone", "sounds rude", "too formal", "politeness",
                "how does this sound"
            ],
            DomainCapability.SCHEDULE_PLANNING: [
                "schedule", "meeting", "find time", "when to meet",
                "coordinate", "calendar"
            ],
            DomainCapability.CONVERSATION_ANALYSIS: [
                "conversation", "discussion", "talk", "chat analysis",
                "how did that go"
            ]
        }
        
        # Hephaestus patterns (engineering)
        hephaestus_patterns = {
            DomainCapability.CODE_ANALYSIS: [
                "code", "program", "function", "algorithm", "review code",
                "debug", "fix error"
            ],
            DomainCapability.SYSTEM_DESIGN: [
                "architecture", "design", "system", "scalability",
                "how to structure", "best approach"
            ],
            DomainCapability.TECH_STACK_PLANNING: [
                "tech stack", "framework", "library", "tools",
                "what should i use", "technology choice"
            ]
        }
        
        # Apollo patterns (health)
        apollo_patterns = {
            DomainCapability.HABIT_ANALYSIS: [
                "habit", "routine", "pattern", "consistent",
                "track my", "behavior"
            ],
            DomainCapability.ROUTINE_PLANNING: [
                "schedule", "daily routine", "plan my day",
                "time management", "productivity"
            ]
        }
        
        # Dionysus patterns (recreation)
        dionysus_patterns = {
            DomainCapability.MUSIC_RECOMMENDATION: [
                "music", "song", "playlist", "artist",
                "what to listen to", "recommend music"
            ],
            DomainCapability.LEISURE_PLANNING: [
                "weekend", "vacation", "relax", "fun",
                "what to do", "entertainment"
            ]
        }
        
        # Check all patterns
        all_patterns = {
            **hermes_patterns,
            **hephaestus_patterns,
            **apollo_patterns,
            **dionysus_patterns
        }
        
        for capability, patterns in all_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return capability
        
        return None
    
    async def _process_with_domain(
        self,
        capability: DomainCapability,
        user_input: UserInput
    ) -> DomainResult:
        """Process request with domain intelligence."""
        if not self.domain_router:
            raise RuntimeError("Domain router not initialized")
        
        # Extract relevant information from user input
        input_data = self._extract_domain_input(capability, user_input.text)
        
        # Get context from memory (via Hestia)
        context = await self._get_domain_context(
            user_input.user_id,
            capability
        )
        
        # Route to domain
        return await self.domain_router.route_to_domain(
            capability=capability,
            user_id=user_input.user_id,
            session_id=user_input.session_id,
            input_data=input_data,
            context=context
        )
    
    def _extract_domain_input(self, capability: DomainCapability, text: str) -> Dict[str, any]:
        """Extract structured input for domain processing."""
        # Simple extraction based on capability
        # In production, this would use more sophisticated NLP
        
        if capability == DomainCapability.DRAFT_MESSAGE:
            return self._extract_message_drafting_input(text)
        elif capability == DomainCapability.CODE_ANALYSIS:
            return self._extract_code_analysis_input(text)
        elif capability == DomainCapability.HABIT_ANALYSIS:
            return self._extract_habit_analysis_input(text)
        elif capability == DomainCapability.MUSIC_RECOMMENDATION:
            return self._extract_music_input(text)
        else:
            # Generic extraction
            return {"text": text, "raw_input": text}
    
    def _extract_message_drafting_input(self, text: str) -> Dict[str, any]:
        """Extract message drafting parameters."""
        # Simplified extraction - would be enhanced in production
        import re
        
        # Look for recipient
        recipient_match = re.search(r"(?:to|for)\s+([A-Za-z\s]+)(?:\s|$)", text, re.IGNORECASE)
        recipient = recipient_match.group(1).strip() if recipient_match else "someone"
        
        # Look for purpose
        purposes = ["request", "ask", "tell", "inform", "thank", "apologize", "invite"]
        purpose = "inform"
        for p in purposes:
            if p in text.lower():
                purpose = p
                break
        
        # Extract key points
        key_points = []
        sentences = text.split('.')
        for sentence in sentences:
            if len(sentence.strip()) > 10:  # Non-trivial sentences
                key_points.append(sentence.strip())
        
        return {
            "message_type": "email",  # Default
            "recipient": recipient,
            "purpose": purpose,
            "key_points": key_points[:3],  # Limit to 3 key points
            "raw_text": text
        }
    
    def _extract_code_analysis_input(self, text: str) -> Dict[str, any]:
        """Extract code analysis parameters."""
        # Look for code snippets (simplified)
        import re
        
        code_pattern = r"```(?:\w+)?\n(.*?)\n```"
        code_matches = re.findall(code_pattern, text, re.DOTALL)
        
        # Look for language
        language = "python"
        lang_pattern = r"```(\w+)"
        lang_match = re.search(lang_pattern, text)
        if lang_match:
            language = lang_match.group(1)
        
        return {
            "code": code_matches[0] if code_matches else "",
            "language": language,
            "analysis_focus": ["complexity", "readability"],
            "context": text
        }
    
    def _extract_habit_analysis_input(self, text: str) -> Dict[str, any]:
        """Extract habit analysis parameters."""
        habits = ["sleep", "exercise", "work", "study", "eat", "meditate"]
        detected_habits = []
        
        for habit in habits:
            if habit in text.lower():
                detected_habits.append(habit)
        
        return {
            "habits": detected_habits,
            "timeframe": "recent",  # Default
            "metrics": ["frequency", "consistency"],
            "raw_text": text
        }
    
    def _extract_music_input(self, text: str) -> Dict[str, any]:
        """Extract music recommendation parameters."""
        moods = ["happy", "sad", "energetic", "calm", "focused", "relaxed"]
        genres = ["rock", "jazz", "classical", "electronic", "pop", "folk"]
        
        detected_mood = None
        detected_genre = None
        
        for mood in moods:
            if mood in text.lower():
                detected_mood = mood
                break
        
        for genre in genres:
            if genre in text.lower():
                detected_genre = genre
                break
        
        return {
            "mood": detected_mood,
            "genre": detected_genre,
            "duration_minutes": 60,  # Default
            "variety_level": "balanced",
            "raw_text": text
        }
    
    async def _get_domain_context(
        self,
        user_id: str,
        capability: DomainCapability
    ) -> Dict[str, any]:
        """Get context from memory for domain processing."""
        # TODO: Implement memory context retrieval
        # This would query Mnemosyne via Hestia's memory interface
        # For now, return empty context
        
        return {
            "user_id": user_id,
            "capability": capability.value,
            "timestamp": datetime.now().isoformat()
        }
    
    def _synthesize_response(
        self,
        llm_response: str,
        domain_results: List[DomainResult],
        executed_actions: List[Dict[str, any]]
    ) -> str:
        """Synthesize response from LLM and domain results."""
        if not domain_results:
            return llm_response
        
        # Start with LLM response
        response = llm_response
        
        # Add domain insights if not already covered
        for domain_result in domain_results:
            domain_name = domain_result.domain_name
            
            # Check if domain insights are already mentioned
            if domain_name.lower() not in response.lower():
                # Add brief mention of domain analysis
                key_insights = list(domain_result.structured_output.keys())[:2]
                if key_insights:
                    response += f"\n\nBased on {domain_name} analysis, I've considered: {', '.join(key_insights)}."
        
        return response
    
    async def list_available_domains(self) -> Dict[str, List[str]]:
        """List available domains and their capabilities."""
        if not self.domain_router:
            return {}
        
        domains_info = {}
        
        for domain_name, domain_service in self.domain_router.domains.items():
            capabilities = domain_service.get_capabilities()
            domains_info[domain_name] = [
                f"{c.capability.value}: {c.description}"
                for c in capabilities
            ]
        
        return domains_info
    
    async def get_domain_capability_info(
        self,
        capability: DomainCapability
    ) -> Optional[Dict[str, any]]:
        """Get information about a specific capability."""
        if not self.domain_router:
            return None
        
        domain_name = self.domain_router.find_domain_for_capability(capability)
        if not domain_name:
            return None
        
        domain_service = self.domain_router.domains.get(domain_name)
        if not domain_service:
            return None
        
        capabilities = domain_service.get_capabilities()
        for cap_info in capabilities:
            if cap_info.capability == capability:
                return {
                    "domain": domain_name,
                    "capability": capability.value,
                    "description": cap_info.description,
                    "input_schema": cap_info.input_schema,
                    "output_schema": cap_info.output_schema
                }
        
        return None