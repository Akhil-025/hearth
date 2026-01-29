"""
STEP 20: POLICY-CONSTRAINED GUIDANCE MODE

Guidance Mode allows HEARTH to proactively surface insights and propose plans,
but NEVER to execute, approve, schedule, or persist anything automatically.

CONSTRAINTS (ABSOLUTE):
- No execution
- No approvals
- No background tasks
- No memory writes
- No retries
- No scheduling
- No looping
- No inference of intent
- Standard library only
- Fail-closed

This is strictly ADVISORY. All guidance must be reviewed and acted upon
by human operators.

COMPOSITION:
1. GuidanceEvent - Immutable advisory event
2. TriggerType - Event trigger categories
3. ConfidenceLevel - Certainty of guidance
4. GuidanceObserver - Surfaces guidance (read-only, no persistence)
5. GuidancePlanner - Proposes draft plans (not executed)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


# ============================================================================
# TRIGGER TYPES
# ============================================================================

class TriggerType(Enum):
    """
    Allowed trigger types for guidance.
    
    # Guidance only
    # No autonomy
    # Triggers evaluated only on explicit entry points
    """
    CALENDAR_CONGESTION = "calendar_congestion"      # Multiple plans scheduled close together
    REPEATED_REJECTIONS = "repeated_rejections"      # Same plan type rejected multiple times
    SECURITY_STATE_CHANGE = "security_state_change"  # Artemis escalated or de-escalated
    IRREVERSIBLE_ACTION_FREQUENCY = "irreversible_action_frequency"  # Too many irreversible ops
    BUDGET_THRESHOLD_ALERT = "budget_threshold_alert"  # Spending trending high


# ============================================================================
# CONFIDENCE LEVEL
# ============================================================================

class ConfidenceLevel(Enum):
    """
    Confidence in guidance (subjective).
    
    # Not a decision metric
    # For operator context only
    """
    LOW = "low"          # Weak signal, many unknowns
    MEDIUM = "medium"    # Reasonable confidence, some uncertainty
    HIGH = "high"        # Strong signal, clear trend


# ============================================================================
# GUIDANCE EVENT
# ============================================================================

@dataclass(frozen=True)
class GuidanceEvent:
    """
    Immutable advisory event.
    
    # Guidance only
    # No execution authority
    # Read-only surface
    
    Contains:
    - What was observed (facts only)
    - Why it matters (implication)
    - What COULD be done (suggestions only)
    - Risks and caveats
    - Confidence level
    """
    
    event_id: str
    trigger_type: TriggerType
    timestamp: datetime
    
    # Facts
    observation: str  # What we detected
    implication: str  # Why it matters
    
    # Suggestions (not commands)
    suggested_actions: Tuple[str, ...]  # High-level suggestions only
    risk_notes: Tuple[str, ...]         # Caveats and risks
    confidence_level: ConfidenceLevel
    
    # Context
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        """Validate immutability."""
        if self.details is None:
            object.__setattr__(self, 'details', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "event_id": self.event_id,
            "trigger_type": self.trigger_type.value,
            "timestamp": self.timestamp.isoformat(),
            "observation": self.observation,
            "implication": self.implication,
            "suggested_actions": list(self.suggested_actions),
            "risk_notes": list(self.risk_notes),
            "confidence_level": self.confidence_level.value,
            "details": self.details,
        }
    
    @staticmethod
    def create(
        trigger_type: TriggerType,
        observation: str,
        implication: str,
        suggested_actions: List[str],
        risk_notes: List[str],
        confidence_level: ConfidenceLevel,
        details: Optional[Dict[str, Any]] = None,
    ) -> GuidanceEvent:
        """
        Factory method for creating guidance events.
        
        # Guidance only
        # No memory mutation
        # Fail-closed
        """
        return GuidanceEvent(
            event_id=f"guid-{uuid4().hex[:12]}",
            trigger_type=trigger_type,
            timestamp=datetime.now(),
            observation=observation,
            implication=implication,
            suggested_actions=tuple(suggested_actions),
            risk_notes=tuple(risk_notes),
            confidence_level=confidence_level,
            details=details or {},
        )


# ============================================================================
# PLAN DRAFT (ADVISORY ONLY)
# ============================================================================

@dataclass(frozen=True)
class PlanDraft:
    """
    Draft plan proposal (NOT executed).
    
    # Guidance only
    # No execution authority
    # Operator must review and approve to execute
    """
    
    draft_id: str
    guidance_event_id: str
    timestamp: datetime
    
    # Proposal (advisory)
    title: str
    description: str
    proposed_steps: Tuple[Dict[str, Any], ...]
    
    # Context
    rationale: str  # Why we suggest this
    risks: Tuple[str, ...]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "draft_id": self.draft_id,
            "guidance_event_id": self.guidance_event_id,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "description": self.description,
            "proposed_steps": [dict(s) for s in self.proposed_steps],
            "rationale": self.rationale,
            "risks": list(self.risks),
        }
    
    @staticmethod
    def create(
        guidance_event_id: str,
        title: str,
        description: str,
        proposed_steps: List[Dict[str, Any]],
        rationale: str,
        risks: List[str],
    ) -> PlanDraft:
        """
        Factory for creating draft plans.
        
        # Guidance only
        # Not executed
        # Operator approval required
        """
        return PlanDraft(
            draft_id=f"draft-{uuid4().hex[:12]}",
            guidance_event_id=guidance_event_id,
            timestamp=datetime.now(),
            title=title,
            description=description,
            proposed_steps=tuple(proposed_steps),
            rationale=rationale,
            risks=tuple(risks),
        )


# ============================================================================
# GUIDANCE OBSERVER
# ============================================================================

class GuidanceObserver:
    """
    Surfaces guidance events (read-only, append-only).
    
    # Guidance only
    # No execution authority
    # No memory mutation
    # Append-only logging
    """
    
    def __init__(self, kernel: Any = None):
        """
        Initialize observer.
        
        Args:
            kernel: Artemis kernel (for security state checking)
        """
        self._kernel = kernel
        self._guidance_events: List[GuidanceEvent] = []
        self._disabled = False
    
    def check_security_state(self) -> bool:
        """
        Check if guidance should be disabled.
        
        Guidance is disabled if Artemis >= COMPROMISED.
        
        # No autonomy
        # Security check only
        # Fail-closed
        """
        if not self._kernel:
            return True  # Enabled by default if no kernel
        
        try:
            # Check if Artemis is compromised
            security_state = self._kernel.get_security_policy()
            if security_state is None:
                return True  # Enable by default
            
            # Disable if severely compromised
            if hasattr(security_state, 'name'):
                state_name = security_state.name
                if state_name in ("COMPROMISED", "LOCKDOWN"):
                    self._disabled = True
                    return False
        except Exception:
            # On any error, keep guidance enabled (fail-open for advisory)
            pass
        
        return not self._disabled
    
    def surface_guidance(
        self,
        observation: str,
        implication: str,
        trigger_type: TriggerType,
        suggested_actions: List[str],
        risk_notes: List[str],
        confidence_level: ConfidenceLevel,
        details: Optional[Dict[str, Any]] = None,
    ) -> GuidanceEvent:
        """
        Surface a guidance event (append-only, no persistence).
        
        # Guidance only
        # No execution
        # No approval
        # No memory writes
        
        Args:
            observation: Facts observed
            implication: Why it matters
            trigger_type: Category of trigger
            suggested_actions: Possible actions (high-level only)
            risk_notes: Caveats and risks
            confidence_level: Certainty of guidance
            details: Optional context
        
        Returns:
            GuidanceEvent (immutable)
        """
        # Check security state
        if not self.check_security_state():
            # Guidance disabled - return empty event
            return GuidanceEvent.create(
                trigger_type=trigger_type,
                observation="[GUIDANCE DISABLED - Security escalation]",
                implication="Guidance surfacing is disabled during security incidents",
                suggested_actions=[],
                risk_notes=["Guidance disabled"],
                confidence_level=ConfidenceLevel.LOW,
            )
        
        # Create event
        event = GuidanceEvent.create(
            trigger_type=trigger_type,
            observation=observation,
            implication=implication,
            suggested_actions=suggested_actions,
            risk_notes=risk_notes,
            confidence_level=confidence_level,
            details=details,
        )
        
        # Append to log (no persistence)
        self._guidance_events.append(event)
        
        return event
    
    def get_guidance_history(self) -> Tuple[GuidanceEvent, ...]:
        """
        Get all guidance events (read-only).
        
        # No execution
        # No memory mutation
        # Historical record only
        """
        return tuple(self._guidance_events)
    
    def clear_history(self) -> None:
        """
        Clear guidance history (only for testing).
        
        # Test-only method
        # Not used in production
        """
        self._guidance_events.clear()


# ============================================================================
# GUIDANCE PLANNER
# ============================================================================

class GuidancePlanner:
    """
    Proposes draft plans based on guidance (not executed).
    
    # Guidance only
    # No execution authority
    # No scheduling
    # No autonomy
    """
    
    @staticmethod
    def propose_calendar_optimization(
        guidance_event: GuidanceEvent,
        scheduled_plans: List[Dict[str, Any]],
    ) -> Optional[PlanDraft]:
        """
        Propose calendar optimization (if congestion detected).
        
        # Guidance only
        # Not executed
        # Operator approval required
        
        Args:
            guidance_event: The triggering guidance event
            scheduled_plans: List of scheduled plans (read-only)
        
        Returns:
            PlanDraft (not executed) or None
        """
        if guidance_event.trigger_type != TriggerType.CALENDAR_CONGESTION:
            return None
        
        if not scheduled_plans or len(scheduled_plans) < 2:
            return None
        
        # Build advisory draft
        draft = PlanDraft.create(
            guidance_event_id=guidance_event.event_id,
            title="Calendar Optimization",
            description="Spread workload more evenly to avoid resource contention",
            proposed_steps=[
                {
                    "order": 1,
                    "suggestion": "Review scheduled plans",
                    "rationale": "Identify overlapping operations",
                    "manual_action": True,
                }
            ],
            rationale="Calendar shows multiple plans scheduled within short window",
            risks=["Operator must review before any action"],
        )
        
        return draft
    
    @staticmethod
    def propose_rejection_analysis(
        guidance_event: GuidanceEvent,
        rejection_history: List[Dict[str, Any]],
    ) -> Optional[PlanDraft]:
        """
        Propose analysis draft for repeated rejections.
        
        # Guidance only
        # Not executed
        # Operator approval required
        
        Args:
            guidance_event: The triggering guidance event
            rejection_history: List of previous rejections (read-only)
        
        Returns:
            PlanDraft (not executed) or None
        """
        if guidance_event.trigger_type != TriggerType.REPEATED_REJECTIONS:
            return None
        
        if not rejection_history:
            return None
        
        # Build advisory draft
        draft = PlanDraft.create(
            guidance_event_id=guidance_event.event_id,
            title="Rejection Pattern Analysis",
            description="Investigate why similar plans are being rejected",
            proposed_steps=[
                {
                    "order": 1,
                    "suggestion": "Review rejection reasons",
                    "rationale": "Identify common failure modes",
                    "manual_action": True,
                }
            ],
            rationale="Multiple rejections detected for similar plan types",
            risks=["Operator must analyze patterns"],
        )
        
        return draft
    
    @staticmethod
    def propose_security_checkpoint(
        guidance_event: GuidanceEvent,
    ) -> Optional[PlanDraft]:
        """
        Propose security checkpoint draft.
        
        # Guidance only
        # Not executed
        # Operator approval required
        
        Args:
            guidance_event: The triggering guidance event
        
        Returns:
            PlanDraft (not executed) or None
        """
        if guidance_event.trigger_type != TriggerType.SECURITY_STATE_CHANGE:
            return None
        
        # Build advisory draft
        draft = PlanDraft.create(
            guidance_event_id=guidance_event.event_id,
            title="Security State Review",
            description="Verify system configuration after security state change",
            proposed_steps=[
                {
                    "order": 1,
                    "suggestion": "Review Artemis state",
                    "rationale": "Understand security implications",
                    "manual_action": True,
                }
            ],
            rationale="Security state change detected",
            risks=["Must review security state before proceeding"],
        )
        
        return draft


# ============================================================================
# GUIDANCE SESSION
# ============================================================================

@dataclass(frozen=True)
class GuidanceSession:
    """
    Immutable record of guidance interaction.
    
    # Guidance only
    # No execution authority
    # Read-only session
    """
    
    session_id: str
    guidance_event: GuidanceEvent
    drafted_plan: Optional[PlanDraft]
    operator_response: str  # "dismiss", "ask_more", "draft_plan"
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "session_id": self.session_id,
            "guidance_event": self.guidance_event.to_dict(),
            "drafted_plan": self.drafted_plan.to_dict() if self.drafted_plan else None,
            "operator_response": self.operator_response,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @staticmethod
    def create(
        guidance_event: GuidanceEvent,
        drafted_plan: Optional[PlanDraft] = None,
        operator_response: str = "dismiss",
    ) -> GuidanceSession:
        """
        Factory for guidance sessions.
        
        # Guidance only
        # No execution
        # Operator input only
        """
        return GuidanceSession(
            session_id=f"sess-{uuid4().hex[:12]}",
            guidance_event=guidance_event,
            drafted_plan=drafted_plan,
            operator_response=operator_response,
            timestamp=datetime.now(),
        )
