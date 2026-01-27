"""
Planner Finite State Machine - Updated with refusal and uncertainty pathways.

Hestia must be able to refuse requests safely and express uncertainty clearly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID

from pydantic import BaseModel, Field

from ..shared.logging.structured_logger import StructuredLogger


class PlannerState(Enum):
    """Extended planner states with refusal and uncertainty."""
    # Normal flow states
    IDLE = "idle"
    INTENT_CLASSIFICATION = "intent_classification"
    CONTEXT_ASSEMBLY = "context_assembly"
    LLM_REASONING = "llm_reasoning"
    ACTION_PLANNING = "action_planning"
    EXECUTION = "execution"
    MEMORY_PROPOSAL = "memory_proposal"
    COMPLETE = "complete"
    
    # Safety states
    UNCERTAIN = "uncertain"      # Not enough information
    REFUSE = "refuse"            # Cannot or will not proceed
    ERROR = "error"              # System error occurred


class RefusalReason(Enum):
    """Reasons for refusing a request."""
    LOW_CONFIDENCE = "low_confidence"           # Intent classification confidence too low
    POLICY_VIOLATION = "policy_violation"       # Request violates system policies
    SAFETY_CONCERN = "safety_concern"           # Potential safety issue
    INSUFFICIENT_CONTEXT = "insufficient_context" # Not enough information
    CAPABILITY_LIMIT = "capability_limit"       # Beyond system capabilities
    PERMISSION_DENIED = "permission_denied"     # User lacks required permissions
    RESOURCE_UNAVAILABLE = "resource_unavailable" # Required resources not available
    CONTRADICTION_DETECTED = "contradiction_detected" # Conflicting information
    RISK_ENVELOPE_VIOLATION = "risk_envelope_violation" # Exceeds risk thresholds


class UncertaintyReason(Enum):
    """Reasons for being uncertain."""
    AMBIGUOUS_INTENT = "ambiguous_intent"       # Multiple possible intents
    INCOMPLETE_INFORMATION = "incomplete_information" # Missing critical information
    CONFLICTING_EVIDENCE = "conflicting_evidence" # Evidence points different ways
    NOVEL_SITUATION = "novel_situation"         # First time seeing this type of request
    CONTEXT_GAP = "context_gap"                 # Missing historical context
    LOW_RELEVANCE_KNOWLEDGE = "low_relevance_knowledge" # Knowledge base has poor matches


@dataclass
class SafetyCheck:
    """Safety check configuration."""
    check_type: str
    threshold: float = 0.7
    required: bool = True
    failure_state: PlannerState = PlannerState.REFUSE


class RefusalDecision(BaseModel):
    """Structured refusal decision."""
    decision_id: UUID = Field(default_factory=UUID)
    state: PlannerState = PlannerState.REFUSE
    reason: RefusalReason
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Metadata
    trigger_check: Optional[str] = None
    alternative_suggestions: List[str] = Field(default_factory=list)
    recovery_possible: bool = False
    recovery_requirements: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class UncertaintyDecision(BaseModel):
    """Structured uncertainty decision."""
    decision_id: UUID = Field(default_factory=UUID)
    state: PlannerState = PlannerState.UNCERTAIN
    reason: UncertaintyReason
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Information needed
    missing_information: List[str] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    
    # Fallback options
    fallback_actions: List[Dict[str, any]] = Field(default_factory=list)
    partial_assistance_possible: bool = False
    
    class Config:
        use_enum_values = True


class PlannerFSM:
    """
    Extended Finite State Machine with refusal and uncertainty pathways.
    
    Rules:
    - Low intent confidence → REFUSE
    - Policy violation → REFUSE  
    - Insufficient context → UNCERTAIN
    - Safety concern → REFUSE
    """
    
    def __init__(self, config: Optional[Dict[str, any]] = None):
        self.config = config or {}
        self.logger = StructuredLogger(__name__)
        
        # Current state
        self.current_state: PlannerState = PlannerState.IDLE
        self.state_history: List[Dict[str, any]] = []
        
        # Safety checks configuration
        self.safety_checks: List[SafetyCheck] = [
            SafetyCheck(
                check_type="intent_confidence",
                threshold=0.3,
                required=True,
                failure_state=PlannerState.REFUSE
            ),
            SafetyCheck(
                check_type="policy_compliance",
                threshold=1.0,  # Must pass 100%
                required=True,
                failure_state=PlannerState.REFUSE
            ),
            SafetyCheck(
                check_type="context_sufficiency",
                threshold=0.5,
                required=False,
                failure_state=PlannerState.UNCERTAIN
            ),
            SafetyCheck(
                check_type="safety_assessment",
                threshold=0.8,
                required=True,
                failure_state=PlannerState.REFUSE
            ),
            SafetyCheck(
                check_type="permission_check",
                threshold=1.0,
                required=True,
                failure_state=PlannerState.REFUSE
            )
        ]
        
        # Decision tracking
        self.refusal_decisions: List[RefusalDecision] = []
        self.uncertainty_decisions: List[UncertaintyDecision] = []
        
        self.logger.info("Planner FSM initialized with safety pathways")
    
    def transition(self, new_state: PlannerState, context: Dict[str, any]) -> bool:
        """
        Transition to a new state with safety checks.
        
        Returns:
            True if transition successful, False if refused/uncertain
        """
        # Record transition
        transition_record = {
            "from_state": self.current_state.value,
            "to_state": new_state.value,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "context": {k: v for k, v in context.items() if not isinstance(v, (bytes, type))}
        }
        self.state_history.append(transition_record)
        
        # Check if transition to refusal/uncertainty state
        if new_state in [PlannerState.REFUSE, PlannerState.UNCERTAIN]:
            self.current_state = new_state
            self.logger.warning(
                "Transitioned to safety state",
                state=new_state.value,
                context_keys=list(context.keys())
            )
            return True
        
        # Perform safety checks for normal transitions
        safety_result = self._perform_safety_checks(new_state, context)
        
        if safety_result["safe_to_proceed"]:
            self.current_state = new_state
            self.logger.debug(
                "State transition",
                from_state=transition_record["from_state"],
                to_state=new_state.value
            )
            return True
        else:
            # Transition to refusal or uncertain state based on checks
            failure_state = safety_result.get("failure_state", PlannerState.REFUSE)
            
            if failure_state == PlannerState.REFUSE:
                refusal = self._create_refusal_decision(
                    reason=RefusalReason.POLICY_VIOLATION,
                    explanation=safety_result.get("reason", "Safety check failed"),
                    confidence=safety_result.get("confidence", 0.9),
                    trigger_check=safety_result.get("failed_check")
                )
                self.refusal_decisions.append(refusal)
                self.current_state = PlannerState.REFUSE
                
                self.logger.warning(
                    "Transition refused by safety check",
                    check=safety_result.get("failed_check"),
                    reason=safety_result.get("reason")
                )
            
            elif failure_state == PlannerState.UNCERTAIN:
                uncertainty = self._create_uncertainty_decision(
                    reason=UncertaintyReason.INCOMPLETE_INFORMATION,
                    explanation=safety_result.get("reason", "Insufficient information"),
                    confidence=safety_result.get("confidence", 0.6),
                    missing_information=safety_result.get("missing_info", [])
                )
                self.uncertainty_decisions.append(uncertainty)
                self.current_state = PlannerState.UNCERTAIN
                
                self.logger.info(
                    "Transition uncertain due to missing information",
                    missing_info=safety_result.get("missing_info", [])
                )
            
            return False
    
    def _perform_safety_checks(
        self,
        target_state: PlannerState,
        context: Dict[str, any]
    ) -> Dict[str, any]:
        """Perform all relevant safety checks for a state transition."""
        results = {
            "safe_to_proceed": True,
            "failed_check": None,
            "reason": None,
            "confidence": 1.0,
            "missing_info": []
        }
        
        # Get checks relevant to target state
        relevant_checks = self._get_relevant_checks(target_state)
        
        for check in relevant_checks:
            check_result = self._execute_safety_check(check, context)
            
            if not check_result["passed"]:
                results["safe_to_proceed"] = False
                results["failed_check"] = check.check_type
                results["reason"] = check_result.get("reason", "Check failed")
                results["confidence"] = check_result.get("confidence", 0.0)
                results["failure_state"] = check.failure_state
                
                if "missing_info" in check_result:
                    results["missing_info"] = check_result["missing_info"]
                
                # Required checks cause immediate failure
                if check.required:
                    break
        
        return results
    
    def _get_relevant_checks(self, target_state: PlannerState) -> List[SafetyCheck]:
        """Get safety checks relevant to a target state."""
        # All checks apply to all states by default
        # In production, this would be more sophisticated
        return self.safety_checks
    
    def _execute_safety_check(
        self,
        check: SafetyCheck,
        context: Dict[str, any]
    ) -> Dict[str, any]:
        """Execute a specific safety check."""
        check_method = getattr(self, f"_check_{check.check_type}", None)
        
        if check_method:
            return check_method(context, check.threshold)
        else:
            # Default: assume check passes
            self.logger.warning(
                "Unknown safety check type",
                check_type=check.check_type
            )
            return {"passed": True, "confidence": 1.0}
    
    def _check_intent_confidence(
        self,
        context: Dict[str, any],
        threshold: float
    ) -> Dict[str, any]:
        """Check intent classification confidence."""
        intent_confidence = context.get("intent_confidence", 1.0)
        
        if intent_confidence < threshold:
            return {
                "passed": False,
                "reason": f"Intent confidence {intent_confidence:.2f} below threshold {threshold:.2f}",
                "confidence": intent_confidence
            }
        
        return {"passed": True, "confidence": intent_confidence}
    
    def _check_policy_compliance(
        self,
        context: Dict[str, any],
        threshold: float
    ) -> Dict[str, any]:
        """Check policy compliance."""
        # Get invariant registry
        try:
            from ...core.invariants import get_invariant_registry
            registry = get_invariant_registry()
            
            module = context.get("module", "unknown")
            operation = context.get("operation", "unknown")
            
            # Check invariants
            try:
                registry.enforce(module, operation, context)
                return {"passed": True, "confidence": 1.0}
            except Exception as e:
                return {
                    "passed": False,
                    "reason": f"Policy violation: {str(e)}",
                    "confidence": 0.0
                }
        
        except ImportError:
            # Invariant system not available
            return {"passed": True, "confidence": 1.0}
    
    def _check_context_sufficiency(
        self,
        context: Dict[str, any],
        threshold: float
    ) -> Dict[str, any]:
        """Check if sufficient context is available."""
        required_context = [
            "user_input",
            "user_id",
            "session_id"
        ]
        
        missing_context = []
        for item in required_context:
            if item not in context or not context[item]:
                missing_context.append(item)
        
        if missing_context:
            sufficiency_score = 1.0 - (len(missing_context) / len(required_context))
            
            if sufficiency_score < threshold:
                return {
                    "passed": False,
                    "reason": f"Missing context: {', '.join(missing_context)}",
                    "confidence": sufficiency_score,
                    "missing_info": missing_context,
                    "failure_state": PlannerState.UNCERTAIN
                }
        
        return {"passed": True, "confidence": 1.0}
    
    def _check_safety_assessment(
        self,
        context: Dict[str, any],
        threshold: float
    ) -> Dict[str, any]:
        """Perform safety assessment."""
        user_input = context.get("user_input", "")
        
        # Safety keywords that indicate potential issues
        safety_keywords = {
            "harm": 0.9,
            "danger": 0.8,
            "illegal": 0.9,
            "cheat": 0.7,
            "steal": 0.9,
            "hurt": 0.8,
            "kill": 1.0,
            "destroy": 0.8
        }
        
        # Calculate safety score
        safety_score = 1.0
        found_keywords = []
        
        for keyword, weight in safety_keywords.items():
            if keyword in user_input.lower():
                safety_score *= (1.0 - weight)
                found_keywords.append(keyword)
        
        if safety_score < threshold:
            return {
                "passed": False,
                "reason": f"Safety concerns detected: {', '.join(found_keywords)}",
                "confidence": safety_score
            }
        
        return {"passed": True, "confidence": safety_score}
    
    def _check_permission_check(
        self,
        context: Dict[str, any],
        threshold: float
    ) -> Dict[str, any]:
        """Check permissions."""
        # Get permission manager
        try:
            from ...core.permission_manager import PermissionManager
            # TODO: Integrate with actual permission system
            return {"passed": True, "confidence": 1.0}
        
        except ImportError:
            return {"passed": True, "confidence": 1.0}
    
    def _create_refusal_decision(
        self,
        reason: RefusalReason,
        explanation: str,
        confidence: float,
        trigger_check: Optional[str] = None
    ) -> RefusalDecision:
        """Create a structured refusal decision."""
        # Generate alternative suggestions based on reason
        alternatives = self._generate_alternatives(reason)
        
        return RefusalDecision(
            reason=reason,
            explanation=explanation,
            confidence=confidence,
            trigger_check=trigger_check,
            alternative_suggestions=alternatives,
            recovery_possible=self._is_recovery_possible(reason),
            recovery_requirements=self._get_recovery_requirements(reason)
        )
    
    def _create_uncertainty_decision(
        self,
        reason: UncertaintyReason,
        explanation: str,
        confidence: float,
        missing_information: List[str]
    ) -> UncertaintyDecision:
        """Create a structured uncertainty decision."""
        # Generate clarifying questions
        clarifying_questions = self._generate_clarifying_questions(reason, missing_information)
        
        # Determine if partial assistance is possible
        partial_assistance = self._is_partial_assistance_possible(reason)
        
        return UncertaintyDecision(
            reason=reason,
            explanation=explanation,
            confidence=confidence,
            missing_information=missing_information,
            clarifying_questions=clarifying_questions,
            partial_assistance_possible=partial_assistance,
            fallback_actions=self._get_fallback_actions(reason)
        )
    
    def _generate_alternatives(self, reason: RefusalReason) -> List[str]:
        """Generate alternative suggestions based on refusal reason."""
        alternatives = {
            RefusalReason.LOW_CONFIDENCE: [
                "Try rephrasing your request more clearly",
                "Provide more context about what you're trying to achieve",
                "Break down your request into smaller parts"
            ],
            RefusalReason.POLICY_VIOLATION: [
                "Review the system guidelines for acceptable requests",
                "Consider alternative approaches that comply with policies",
                "Contact system administrator for policy clarification"
            ],
            RefusalReason.INSUFFICIENT_CONTEXT: [
                "Provide more background information",
                "Share relevant previous interactions or decisions",
                "Specify constraints or requirements"
            ],
            RefusalReason.CAPABILITY_LIMIT: [
                "Check the system capabilities documentation",
                "Consider manual approach for this task",
                "Break down the task into steps the system can handle"
            ]
        }
        
        return alternatives.get(reason, [
            "Please review your request and try again",
            "Contact support if you believe this is an error"
        ])
    
    def _generate_clarifying_questions(
        self,
        reason: UncertaintyReason,
        missing_info: List[str]
    ) -> List[str]:
        """Generate clarifying questions based on uncertainty reason."""
        questions = []
        
        if reason == UncertaintyReason.AMBIGUOUS_INTENT:
            questions = [
                "Could you clarify what you mean by that?",
                "Which aspect is most important to you?",
                "Are you trying to achieve X or Y?"
            ]
        
        elif reason == UncertaintyReason.INCOMPLETE_INFORMATION:
            for info in missing_info:
                if info == "user_input":
                    questions.append("What would you like me to help with?")
                elif info == "context":
                    questions.append("What background should I consider?")
                elif info == "constraints":
                    questions.append("Are there any limitations or requirements?")
        
        elif reason == UncertaintyReason.CONFLICTING_EVIDENCE:
            questions = [
                "I'm seeing conflicting information. Which source should I trust?",
                "Has anything changed since the last time we discussed this?",
                "Could you help me understand which information is correct?"
            ]
        
        return questions
    
    def _is_recovery_possible(self, reason: RefusalReason) -> bool:
        """Determine if recovery from refusal is possible."""
        recoverable_reasons = {
            RefusalReason.LOW_CONFIDENCE,
            RefusalReason.INSUFFICIENT_CONTEXT,
            RefusalReason.RESOURCE_UNAVAILABLE
        }
        
        return reason in recoverable_reasons
    
    def _get_recovery_requirements(self, reason: RefusalReason) -> List[str]:
        """Get requirements for recovery from refusal."""
        requirements = {
            RefusalReason.LOW_CONFIDENCE: ["clearer_request", "more_context"],
            RefusalReason.INSUFFICIENT_CONTEXT: ["additional_information", "background_context"],
            RefusalReason.RESOURCE_UNAVAILABLE: ["resource_availability", "alternative_approach"],
            RefusalReason.PERMISSION_DENIED: ["permission_grant", "authorization"]
        }
        
        return requirements.get(reason, [])
    
    def _is_partial_assistance_possible(self, reason: UncertaintyReason) -> bool:
        """Determine if partial assistance is possible despite uncertainty."""
        # Most uncertainty reasons allow some level of assistance
        no_assistance_reasons = {
            UncertaintyReason.CONFLICTING_EVIDENCE,
            UncertaintyReason.NOVEL_SITUATION
        }
        
        return reason not in no_assistance_reasons
    
    def _get_fallback_actions(self, reason: UncertaintyReason) -> List[Dict[str, any]]:
        """Get fallback actions for uncertain situations."""
        fallbacks = []
        
        if reason == UncertaintyReason.AMBIGUOUS_INTENT:
            fallbacks.append({
                "action": "list_options",
                "description": "List possible interpretations"
            })
        
        elif reason == UncertaintyReason.INCOMPLETE_INFORMATION:
            fallbacks.append({
                "action": "request_clarification",
                "description": "Ask for missing information"
            })
        
        elif reason == UncertaintyReason.LOW_RELEVANCE_KNOWLEDGE:
            fallbacks.append({
                "action": "provide_related_knowledge",
                "description": "Share related information"
            })
        
        return fallbacks
    
    def get_safety_report(self) -> Dict[str, any]:
        """Get safety and refusal statistics."""
        return {
            "current_state": self.current_state.value,
            "total_transitions": len(self.state_history),
            "refusal_count": len(self.refusal_decisions),
            "uncertainty_count": len(self.uncertainty_decisions),
            "recent_refusals": [
                {
                    "reason": d.reason.value,
                    "explanation": d.explanation,
                    "confidence": d.confidence
                }
                for d in self.refusal_decisions[-5:]
            ] if self.refusal_decisions else [],
            "recent_uncertainties": [
                {
                    "reason": d.reason.value,
                    "missing_info": d.missing_information
                }
                for d in self.uncertainty_decisions[-5:]
            ] if self.uncertainty_decisions else []
        }
    
    def create_plan(
        self,
        intent: str,
        user_input: any,
        domain_context: Optional[List[any]] = None
    ) -> Dict[str, any]:
        """
        Create a plan with integrated safety checks.
        
        Updated to handle refusal and uncertainty states.
        """
        # Start with intent classification
        self.transition(PlannerState.INTENT_CLASSIFICATION, {
            "intent": intent,
            "user_input": user_input
        })
        
        # If in refusal or uncertainty state, return appropriate plan
        if self.current_state == PlannerState.REFUSE:
            latest_refusal = self.refusal_decisions[-1] if self.refusal_decisions else None
            return {
                "state": "refused",
                "reason": latest_refusal.reason.value if latest_refusal else "unknown",
                "explanation": latest_refusal.explanation if latest_refusal else "Request refused",
                "alternative_suggestions": latest_refusal.alternative_suggestions if latest_refusal else [],
                "steps": []
            }
        
        elif self.current_state == PlannerState.UNCERTAIN:
            latest_uncertainty = self.uncertainty_decisions[-1] if self.uncertainty_decisions else None
            return {
                "state": "uncertain",
                "reason": latest_uncertainty.reason.value if latest_uncertainty else "unknown",
                "explanation": latest_uncertainty.explanation if latest_uncertainty else "Need more information",
                "clarifying_questions": latest_uncertainty.clarifying_questions if latest_uncertainty else [],
                "steps": latest_uncertainty.fallback_actions if latest_uncertainty else []
            }
        
        # Normal planning flow
        plan_steps = []
        
        # Context assembly
        if self.transition(PlannerState.CONTEXT_ASSEMBLY, {"intent": intent}):
            plan_steps.append({
                "step": "context_assembly",
                "description": "Gather relevant context and memories"
            })
        
        # LLM reasoning
        if self.transition(PlannerState.LLM_REASONING, {"intent": intent}):
            plan_steps.append({
                "step": "llm_reasoning",
                "description": "Reason about response with LLM"
            })
        
        # Action planning
        if self.transition(PlannerState.ACTION_PLANNING, {"intent": intent}):
            plan_steps.append({
                "step": "action_planning",
                "description": "Plan specific actions to take"
            })
        
        # Check final state
        if self.current_state in [PlannerState.REFUSE, PlannerState.UNCERTAIN]:
            # Handle refusal/uncertainty that occurred during planning
            return self.create_plan(intent, user_input, domain_context)
        
        # Normal completion
        self.transition(PlannerState.COMPLETE, {"plan_steps": len(plan_steps)})
        
        return {
            "state": "complete",
            "steps": plan_steps,
            "estimated_complexity": len(plan_steps),
            "requires_confirmation": len(plan_steps) > 3  # Complex plans need confirmation
        }