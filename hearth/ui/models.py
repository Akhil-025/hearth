# UI Layer - Data Models
# Phase 1: Human Interface
# NO EXECUTION
# NO AUTONOMY
# NO MEMORY WRITES
# NO BACKGROUND THREADS

"""
Immutable UI data models.

All models are @dataclass(frozen=True):
- Immutable once created
- Hashable
- Serializable
- No side effects

Models represent VIEWS of system state, not commands.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Dict, Optional, Any
from datetime import datetime
import hashlib


class ApprovalChoice(Enum):
    """Approval decision choice."""
    APPROVE = "approve"
    REJECT = "reject"


class SecurityState(Enum):
    """Security state (read from Artemis)."""
    SECURE = "secure"
    DEGRADED = "degraded"
    COMPROMISED = "compromised"
    LOCKDOWN = "lockdown"


class LiveMode(Enum):
    """Execution mode (read from Artemis)."""
    DRY_RUN = "dry_run"
    LIVE = "live"


@dataclass(frozen=True)
class PlanStep:
    """
    Single plan step (immutable).
    
    # UI ONLY
    # NO EXECUTION
    # NO AUTONOMY
    # NO MEMORY WRITE
    """
    step_id: str
    order: int
    action: str
    subsystem: str
    parameters: Dict[str, Any]
    duration_estimate_ms: int
    cost_estimate: float
    
    def to_dict(self) -> dict:
        """Serialize to dict (no side effects)."""
        return {
            "step_id": self.step_id,
            "order": self.order,
            "action": self.action,
            "subsystem": self.subsystem,
            "parameters": dict(self.parameters),
            "duration_estimate_ms": self.duration_estimate_ms,
            "cost_estimate": self.cost_estimate,
        }


@dataclass(frozen=True)
class PlanViewModel:
    """
    Immutable view of a compiled plan.
    
    Does:
    - Contains plan data from PlanCompiler
    - Formats for display
    - No inference or summarization
    
    Does NOT:
    - Execute
    - Call domains
    - Call executor
    - Modify state
    
    # UI ONLY
    # NO EXECUTION
    # NO AUTONOMY
    # NO MEMORY WRITE
    """
    plan_id: str
    intent: str
    steps: Tuple[PlanStep, ...]  # Immutable tuple
    faculties_involved: Tuple[str, ...]  # Immutable tuple
    data_accessed: Tuple[str, ...]  # Immutable tuple
    credentials_required: Tuple[str, ...]  # Immutable tuple
    risk_level: str  # "low", "medium", "high", "critical"
    irreversible_actions: Tuple[str, ...]  # Immutable tuple
    estimated_duration_ms: int
    cost_estimate: float
    created_at: datetime
    
    @staticmethod
    def create(
        plan_id: str,
        intent: str,
        steps: List[PlanStep],
        faculties: List[str],
        data_accessed: List[str],
        credentials: List[str],
        risk_level: str,
        irreversible_actions: List[str],
        duration_ms: int,
        cost: float,
    ) -> "PlanViewModel":
        """
        Create plan view (immutable).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        return PlanViewModel(
            plan_id=plan_id,
            intent=intent,
            steps=tuple(steps),
            faculties_involved=tuple(faculties),
            data_accessed=tuple(data_accessed),
            credentials_required=tuple(credentials),
            risk_level=risk_level,
            irreversible_actions=tuple(irreversible_actions),
            estimated_duration_ms=duration_ms,
            cost_estimate=cost,
            created_at=datetime.utcnow(),
        )
    
    def to_dict(self) -> dict:
        """Serialize to dict (no side effects)."""
        return {
            "plan_id": self.plan_id,
            "intent": self.intent,
            "steps": [s.to_dict() for s in self.steps],
            "faculties_involved": list(self.faculties_involved),
            "data_accessed": list(self.data_accessed),
            "credentials_required": list(self.credentials_required),
            "risk_level": self.risk_level,
            "irreversible_actions": list(self.irreversible_actions),
            "estimated_duration_ms": self.estimated_duration_ms,
            "cost_estimate": self.cost_estimate,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class SecuritySnapshotView:
    """
    Immutable view of security posture (read from Artemis).
    
    Does:
    - Shows security state
    - Shows live mode
    - Shows integrity status
    
    Does NOT:
    - Modify security state
    - Execute
    - Make decisions
    
    # UI ONLY
    # NO EXECUTION
    # NO AUTONOMY
    # NO MEMORY WRITE
    """
    security_state: SecurityState
    live_mode: LiveMode
    integrity_status: str  # "verified", "degraded", "unverified"
    last_audit_time: datetime
    guidance_active: bool
    
    @staticmethod
    def create(
        state: SecurityState,
        mode: LiveMode,
        integrity: str,
        last_audit: datetime,
        guidance: bool = False,
    ) -> "SecuritySnapshotView":
        """Create security snapshot (immutable)."""
        return SecuritySnapshotView(
            security_state=state,
            live_mode=mode,
            integrity_status=integrity,
            last_audit_time=last_audit,
            guidance_active=guidance,
        )
    
    def to_dict(self) -> dict:
        """Serialize to dict (no side effects)."""
        return {
            "security_state": self.security_state.value,
            "live_mode": self.live_mode.value,
            "integrity_status": self.integrity_status,
            "last_audit_time": self.last_audit_time.isoformat(),
            "guidance_active": self.guidance_active,
        }


@dataclass(frozen=True)
class ApprovalDecision:
    """
    Immutable approval/rejection decision.
    
    Does:
    - Records user's explicit choice
    - Immutable (cannot be changed)
    - Hashable (can be verified)
    
    Does NOT:
    - Execute
    - Modify plans
    - Call executor
    - Modify state
    
    # UI ONLY
    # NO EXECUTION
    # NO AUTONOMY
    # NO MEMORY WRITE
    """
    decision_id: str
    plan_id: str
    choice: ApprovalChoice
    user_id: str
    timestamp: datetime
    reason: Optional[str]  # Required if REJECT, optional if APPROVE
    
    @staticmethod
    def create(
        plan_id: str,
        choice: ApprovalChoice,
        user_id: str,
        reason: Optional[str] = None,
    ) -> "ApprovalDecision":
        """
        Create approval decision (immutable).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        timestamp = datetime.utcnow()
        
        # Validate: reject requires reason
        if choice == ApprovalChoice.REJECT and not reason:
            raise ValueError("Rejection requires reason")
        
        # Generate decision ID
        id_str = f"{plan_id}_{user_id}_{choice.value}_{timestamp.isoformat()}"
        decision_id = f"dec-{hashlib.sha256(id_str.encode()).hexdigest()[:12]}"
        
        return ApprovalDecision(
            decision_id=decision_id,
            plan_id=plan_id,
            choice=choice,
            user_id=user_id,
            timestamp=timestamp,
            reason=reason,
        )
    
    def to_dict(self) -> dict:
        """Serialize to dict (no side effects)."""
        return {
            "decision_id": self.decision_id,
            "plan_id": self.plan_id,
            "choice": self.choice.value,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ApprovalSession:
    """
    Immutable approval session record.
    
    Does:
    - Records approval interaction
    - Contains plan view and decision
    - Immutable audit trail
    
    Does NOT:
    - Execute
    - Modify plans
    - Modify decisions
    - Call executor
    
    # UI ONLY
    # NO EXECUTION
    # NO AUTONOMY
    # NO MEMORY WRITE
    """
    session_id: str
    plan: PlanViewModel
    security_snapshot: SecuritySnapshotView
    decision: ApprovalDecision
    duration_ms: int
    
    @staticmethod
    def create(
        plan: PlanViewModel,
        security: SecuritySnapshotView,
        decision: ApprovalDecision,
        duration_ms: int,
    ) -> "ApprovalSession":
        """Create approval session (immutable)."""
        id_str = f"{plan.plan_id}_{decision.decision_id}_{decision.timestamp.isoformat()}"
        session_id = f"sess-{hashlib.sha256(id_str.encode()).hexdigest()[:12]}"
        
        return ApprovalSession(
            session_id=session_id,
            plan=plan,
            security_snapshot=security,
            decision=decision,
            duration_ms=duration_ms,
        )
    
    def to_dict(self) -> dict:
        """Serialize to dict (no side effects)."""
        return {
            "session_id": self.session_id,
            "plan": self.plan.to_dict(),
            "security_snapshot": self.security_snapshot.to_dict(),
            "decision": self.decision.to_dict(),
            "duration_ms": self.duration_ms,
        }
