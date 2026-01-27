"""
Hermes - Communication & Social Intelligence Domain
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from ...shared.logging.structured_logger import StructuredLogger
from ...shared.schemas.memory import MemoryType
from ..base import (
    BaseDomainService,
    DomainCapability,
    DomainCapabilityInfo,
    DomainRequest,
    DomainResult
)

from .message_planner import MessagePlanner, MessageType, MessagePurpose
from .tone_engine import ToneEngine, ToneProfile
from .conversation_analyzer import ConversationAnalyzer
from .schedule_synthesizer import ScheduleSynthesizer
from .communication_advisor import CommunicationAdvisor


class HermesCapability(Enum):
    """Hermes-specific capabilities."""
    DRAFT_MESSAGE = DomainCapability.DRAFT_MESSAGE
    ANALYZE_TONE = DomainCapability.ANALYZE_TONE
    SCHEDULE_PLANNING = DomainCapability.SCHEDULE_PLANNING
    CONVERSATION_ANALYSIS = DomainCapability.CONVERSATION_ANALYSIS
    ANALYZE_COMMUNICATION_PATTERNS = "analyze_communication_patterns"


class DraftMessageRequest(BaseModel):
    """Request for message drafting."""
    message_type: str  # email, chat, formal, informal
    recipient: str
    purpose: str  # request, inform, negotiate, etc.
    key_points: List[str]
    constraints: List[str] = Field(default_factory=list)
    previous_context: Optional[str] = None
    desired_tone: Optional[str] = None
    length_preference: Optional[str] = None  # short, medium, detailed


class ToneAnalysisRequest(BaseModel):
    """Request for tone analysis."""
    text: str
    context: Optional[str] = None
    analyze_for: List[str] = Field(default_factory=list)  # clarity, politeness, etc.


class SchedulePlanningRequest(BaseModel):
    """Request for schedule planning."""
    participants: List[str]
    purpose: str
    constraints: List[Dict[str, Any]] = Field(default_factory=list)
    duration_minutes: int = 30
    preferred_times: List[str] = Field(default_factory=list)


class HermesService(BaseDomainService):
    """
    Hermes - Communication intelligence domain.
    
    Handles: Message drafting, tone analysis, schedule logic, conversation analysis.
    Does NOT: Send messages, access calendars, spoof identities.
    """
    
    def __init__(self):
        super().__init__("hermes", "1.0.0")
        
        # Initialize subcomponents
        self.message_planner = MessagePlanner()
        self.tone_engine = ToneEngine()
        self.conversation_analyzer = ConversationAnalyzer()
        self.schedule_synthesizer = ScheduleSynthesizer()
        self.communication_advisor = CommunicationAdvisor()
        
        self.logger = StructuredLogger("domain.hermes")
    
    def _register_capabilities(self) -> None:
        """Register Hermes capabilities."""
        
        # Message drafting
        self.register_capability(
            DomainCapabilityInfo(
                capability=DomainCapability.DRAFT_MESSAGE,
                description="Draft messages for various contexts and tones",
                input_schema={
                    "type": "object",
                    "required": ["message_type", "recipient", "purpose", "key_points"],
                    "properties": {
                        "message_type": {"type": "string", "enum": ["email", "chat", "formal", "informal"]},
                        "recipient": {"type": "string"},
                        "purpose": {"type": "string"},
                        "key_points": {"type": "array", "items": {"type": "string"}},
                        "constraints": {"type": "array", "items": {"type": "string"}},
                        "previous_context": {"type": "string"},
                        "desired_tone": {"type": "string"},
                        "length_preference": {"type": "string", "enum": ["short", "medium", "detailed"]}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "drafts": {"type": "array", "items": {"type": "object"}},
                        "tone_analysis": {"type": "object"},
                        "suggested_improvements": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
        )
        
        # Tone analysis
        self.register_capability(
            DomainCapabilityInfo(
                capability=DomainCapability.ANALYZE_TONE,
                description="Analyze tone, clarity, and effectiveness of communication",
                input_schema={
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "text": {"type": "string"},
                        "context": {"type": "string"},
                        "analyze_for": {"type": "array", "items": {"type": "string"}}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "tone_score": {"type": "number"},
                        "clarity_score": {"type": "number"},
                        "politeness_score": {"type": "number"},
                        "key_observations": {"type": "array", "items": {"type": "string"}},
                        "suggestions": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
        )
        
        # Schedule planning
        self.register_capability(
            DomainCapabilityInfo(
                capability=DomainCapability.SCHEDULE_PLANNING,
                description="Plan schedules and meeting times based on constraints",
                input_schema={
                    "type": "object",
                    "required": ["participants", "purpose"],
                    "properties": {
                        "participants": {"type": "array", "items": {"type": "string"}},
                        "purpose": {"type": "string"},
                        "constraints": {"type": "array", "items": {"type": "object"}},
                        "duration_minutes": {"type": "integer", "minimum": 15, "maximum": 480},
                        "preferred_times": {"type": "array", "items": {"type": "string"}}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "schedule_options": {"type": "array", "items": {"type": "object"}},
                        "constraint_analysis": {"type": "object"},
                        "success_probability": {"type": "number"},
                        "recommendations": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
        )
        
        # Conversation analysis
        self.register_capability(
            DomainCapabilityInfo(
                capability=DomainCapability.CONVERSATION_ANALYSIS,
                description="Analyze conversation patterns and effectiveness",
                input_schema={
                    "type": "object",
                    "required": ["conversation_history"],
                    "properties": {
                        "conversation_history": {"type": "array", "items": {"type": "object"}},
                        "participants": {"type": "array", "items": {"type": "string"}},
                        "analysis_focus": {"type": "array", "items": {"type": "string"}}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "engagement_analysis": {"type": "object"},
                        "balance_metrics": {"type": "object"},
                        "topic_flow": {"type": "array", "items": {"type": "object"}},
                        "improvement_suggestions": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
        )
        
        # Communication patterns
        self.register_capability(
            DomainCapabilityInfo(
                capability=HermesCapability.ANALYZE_COMMUNICATION_PATTERNS,
                description="Analyze communication patterns over time",
                input_schema={
                    "type": "object",
                    "required": ["communication_samples"],
                    "properties": {
                        "communication_samples": {"type": "array", "items": {"type": "object"}},
                        "time_range_days": {"type": "integer", "minimum": 1, "maximum": 365},
                        "participants": {"type": "array", "items": {"type": "string"}}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "pattern_analysis": {"type": "object"},
                        "frequency_distribution": {"type": "object"},
                        "tone_trends": {"type": "object"},
                        "relationship_insights": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
        )
    
    async def _process_capability(self, request: DomainRequest) -> DomainResult:
        """Process Hermes capability requests."""
        
        if request.capability == DomainCapability.DRAFT_MESSAGE:
            return await self._process_draft_message(request)
        elif request.capability == DomainCapability.ANALYZE_TONE:
            return await self._process_tone_analysis(request)
        elif request.capability == DomainCapability.SCHEDULE_PLANNING:
            return await self._process_schedule_planning(request)
        elif request.capability == DomainCapability.CONVERSATION_ANALYSIS:
            return await self._process_conversation_analysis(request)
        elif request.capability.value == HermesCapability.ANALYZE_COMMUNICATION_PATTERNS.value:
            return await self._process_communication_patterns(request)
        else:
            raise ValueError(f"Unknown capability: {request.capability}")
    
    async def _process_draft_message(self, request: DomainRequest) -> DomainResult:
        """Process message drafting request."""
        input_data = DraftMessageRequest(**request.input_data)
        
        # Generate message drafts
        drafts = self.message_planner.generate_drafts(
            message_type=input_data.message_type,
            recipient=input_data.recipient,
            purpose=input_data.purpose,
            key_points=input_data.key_points,
            constraints=input_data.constraints,
            previous_context=input_data.previous_context
        )
        
        # Analyze tone of drafts
        tone_analysis = []
        for draft in drafts:
            analysis = self.tone_engine.analyze(
                draft["content"],
                context=input_data.previous_context
            )
            tone_analysis.append({
                "draft_id": draft["draft_id"],
                "tone_profile": analysis.tone_profile.value,
                "confidence": analysis.confidence,
                "suggestions": analysis.suggestions
            })
        
        # Get advisor suggestions
        suggestions = self.communication_advisor.get_message_suggestions(
            message_type=input_data.message_type,
            recipient=input_data.recipient,
            purpose=input_data.purpose
        )
        
        # Create memory proposal for communication pattern
        memory_proposal = self._create_memory_proposal(
            memory_type=MemoryType.STRUCTURED,
            data={
                "user_id": request.user_id,
                "category": "communication_patterns",
                "key": f"message_draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "value": {
                    "recipient": input_data.recipient,
                    "message_type": input_data.message_type,
                    "purpose": input_data.purpose,
                    "timestamp": datetime.now().isoformat()
                }
            },
            reason="Record communication pattern for future optimization",
            confidence=0.7
        )
        
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=request.capability,
            analysis={
                "draft_count": len(drafts),
                "tone_variety": len(set(a["tone_profile"] for a in tone_analysis))
            },
            structured_output={
                "drafts": drafts,
                "tone_analysis": tone_analysis,
                "suggested_improvements": suggestions
            },
            confidence=0.85,
            memory_proposals=[memory_proposal]
        )
    
    async def _process_tone_analysis(self, request: DomainRequest) -> DomainResult:
        """Process tone analysis request."""
        input_data = ToneAnalysisRequest(**request.input_data)
        
        # Analyze tone
        analysis = self.tone_engine.analyze(
            input_data.text,
            context=input_data.context
        )
        
        # Get detailed analysis
        detailed_analysis = self.tone_engine.detailed_analysis(
            input_data.text,
            focus_areas=input_data.analyze_for if input_data.analyze_for else None
        )
        
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=request.capability,
            analysis={
                "text_length": len(input_data.text),
                "analysis_depth": len(detailed_analysis)
            },
            structured_output={
                "tone_score": analysis.confidence,
                "clarity_score": detailed_analysis.get("clarity_score", 0.0),
                "politeness_score": detailed_analysis.get("politeness_score", 0.0),
                "key_observations": detailed_analysis.get("observations", []),
                "suggestions": analysis.suggestions
            },
            confidence=analysis.confidence
        )
    
    async def _process_schedule_planning(self, request: DomainRequest) -> DomainResult:
        """Process schedule planning request."""
        input_data = SchedulePlanningRequest(**request.input_data)
        
        # Generate schedule options
        options = self.schedule_synthesizer.generate_options(
            participants=input_data.participants,
            purpose=input_data.purpose,
            constraints=input_data.constraints,
            duration_minutes=input_data.duration_minutes,
            preferred_times=input_data.preferred_times
        )
        
        # Analyze constraints
        constraint_analysis = self.schedule_synthesizer.analyze_constraints(
            input_data.constraints
        )
        
        # Calculate success probability
        success_prob = self.schedule_synthesizer.estimate_success_probability(
            options,
            input_data.constraints
        )
        
        # Generate recommendations
        recommendations = self.communication_advisor.get_scheduling_recommendations(
            participants=input_data.participants,
            purpose=input_data.purpose
        )
        
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=request.capability,
            analysis={
                "option_count": len(options),
                "constraint_count": len(input_data.constraints),
                "participant_count": len(input_data.participants)
            },
            structured_output={
                "schedule_options": options,
                "constraint_analysis": constraint_analysis,
                "success_probability": success_prob,
                "recommendations": recommendations
            },
            confidence=min(0.9, success_prob * 1.1)  # Cap confidence at 0.9
        )
    
    async def _process_conversation_analysis(self, request: DomainRequest) -> DomainResult:
        """Process conversation analysis request."""
        conversation_history = request.input_data.get("conversation_history", [])
        participants = request.input_data.get("participants", [])
        analysis_focus = request.input_data.get("analysis_focus", [])
        
        # Analyze conversation
        analysis = self.conversation_analyzer.analyze(
            conversation_history,
            participants=participants,
            focus_areas=analysis_focus
        )
        
        # Create memory proposal for conversation insights
        if analysis.get("key_insights"):
            memory_proposal = self._create_memory_proposal(
                memory_type=MemoryType.EPISODIC,
                data={
                    "user_id": request.user_id,
                    "title": f"Conversation analysis with {', '.join(participants[:2])}",
                    "description": f"Analysis of conversation patterns and effectiveness",
                    "occurred_at": datetime.now(),
                    "event_type": "conversation_analysis",
                    "participants": participants,
                    "key_insights": analysis.get("key_insights", [])[:3]
                },
                reason="Record conversation analysis for pattern recognition",
                confidence=0.75
            )
            
            memory_proposals = [memory_proposal]
        else:
            memory_proposals = []
        
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=request.capability,
            analysis={
                "conversation_turns": len(conversation_history),
                "participant_count": len(participants),
                "analysis_depth": len(analysis_focus) or 5  # default depth
            },
            structured_output={
                "engagement_analysis": analysis.get("engagement", {}),
                "balance_metrics": analysis.get("balance", {}),
                "topic_flow": analysis.get("topics", []),
                "improvement_suggestions": analysis.get("suggestions", [])
            },
            confidence=analysis.get("confidence", 0.8),
            memory_proposals=memory_proposals
        )
    
    async def _process_communication_patterns(self, request: DomainRequest) -> DomainResult:
        """Process communication pattern analysis."""
        samples = request.input_data.get("communication_samples", [])
        time_range = request.input_data.get("time_range_days", 30)
        participants = request.input_data.get("participants", [])
        
        # Analyze patterns
        pattern_analysis = self.conversation_analyzer.analyze_patterns(
            samples,
            time_range_days=time_range,
            participants=participants
        )
        
        # Analyze tone trends
        tone_trends = self.tone_engine.analyze_trends(
            [s.get("content", "") for s in samples if s.get("content")],
            time_range_days=time_range
        )
        
        # Generate relationship insights
        insights = self.communication_advisor.generate_relationship_insights(
            pattern_analysis,
            participants
        )
        
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=HermesCapability.ANALYZE_COMMUNICATION_PATTERNS,
            analysis={
                "sample_count": len(samples),
                "time_range_days": time_range,
                "unique_participants": len(set(participants))
            },
            structured_output={
                "pattern_analysis": pattern_analysis,
                "frequency_distribution": pattern_analysis.get("frequency", {}),
                "tone_trends": tone_trends,
                "relationship_insights": insights
            },
            confidence=min(0.9, len(samples) / 100.0)  # More samples = more confidence
        )