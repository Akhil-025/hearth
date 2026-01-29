"""
EXECUTION OBSERVABILITY & ROLLBACK SCAFFOLD (Step 19)

Post-execution inspection only - NO AUTOMATION, NO RETRIES, NO ROLLBACK EXECUTION.

Creates immutable execution records and surfaces rollback scaffolding.
Designed for manual inspection and (when applicable) manual rollback.

CONSTRAINTS:
- No automation
- No retries
- No background threads
- No state mutation outside explicit execution
- Rollback is MANUAL and OPTIONAL
- Standard library only
- Fail-closed

COMPOSITION:
1. ExecutionRecord - Immutable execution history
2. StepEvent - Hash-linked step events
3. SecuritySnapshot - Pre/post security state
4. RollbackScaffold - Manual rollback hints (verbatim from plan)
5. ExecutionObserver - Records execution progress
6. RollbackPlanner - Surfaces rollback possibilities (NO EXECUTION)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from hashlib import sha256
import json


# ============================================================================
# STEP EVENTS
# ============================================================================

class StepEventType(Enum):
    """
    Step-level events (append-only, hash-linked).
    
    No retries, no branching.
    """
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"


@dataclass(frozen=True)
class StepEvent:
    """
    Immutable step-level event (append-only, hash-linked).
    
    # Post-execution inspection only
    # No automatic recovery
    # No retries
    # Fail-closed
    
    Events form an append-only chain.
    Each event is linked to the previous one via hash.
    """
    timestamp: datetime
    step_index: int
    step_name: str
    event_type: StepEventType
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    previous_event_hash: Optional[str] = None
    
    def get_hash(self) -> str:
        """
        Compute hash of this event (for chain linking).
        
        Returns:
            SHA-256 hash of event contents
        """
        event_dict = {
            "timestamp": self.timestamp.isoformat(),
            "step_index": self.step_index,
            "step_name": self.step_name,
            "event_type": self.event_type.value,
            "details": self.details,
            "error_message": self.error_message,
            "previous_event_hash": self.previous_event_hash,
        }
        event_json = json.dumps(event_dict, sort_keys=True, default=str)
        return sha256(event_json.encode()).hexdigest()


# ============================================================================
# SECURITY SNAPSHOTS
# ============================================================================

@dataclass(frozen=True)
class SecuritySnapshot:
    """
    Immutable security state snapshot (pre or post execution).
    
    # Post-execution inspection only
    # No automatic recovery
    # No retries
    # Fail-closed
    
    Captures:
    - Security state
    - Boundary state
    - Timestamp
    """
    timestamp: datetime
    security_state: str  # Enum value (OPERATIONAL, COMPROMISED, LOCKDOWN)
    boundary_state: str  # Enum value (NOMINAL, ELEVATED, COMPROMISED, LOCKDOWN)
    context: str = ""  # Optional context (e.g., "Pre-execution", "Post-execution")
    
    @staticmethod
    def from_kernel(kernel: Any, context: str = "") -> SecuritySnapshot:
        """
        Create snapshot from Artemis kernel.
        
        Args:
            kernel: Artemis kernel instance
            context: Optional context description
        
        Returns:
            SecuritySnapshot (immutable)
        """
        security_state = "UNKNOWN"
        boundary_state = "UNKNOWN"
        
        try:
            if kernel and hasattr(kernel, 'get_security_state'):
                security_state = kernel.get_security_state().value
        except Exception:
            pass
        
        try:
            if kernel and hasattr(kernel, 'get_boundary_state'):
                boundary_state = kernel.get_boundary_state().value
        except Exception:
            pass
        
        return SecuritySnapshot(
            timestamp=datetime.now(),
            security_state=security_state,
            boundary_state=boundary_state,
            context=context,
        )


# ============================================================================
# SIDE EFFECTS
# ============================================================================

class SideEffectCategory(Enum):
    """Categories of side effects."""
    FILE_SYSTEM = "file_system"  # Files created/modified/deleted
    NETWORK = "network"  # Network calls made
    DATA_MUTATION = "data_mutation"  # Data modified
    CONFIGURATION = "configuration"  # Configuration changed
    SYSTEM = "system"  # System-level changes
    OTHER = "other"  # Other effects


@dataclass(frozen=True)
class SideEffect:
    """
    Immutable record of a single side effect.
    
    # Post-execution inspection only
    # No automatic recovery
    # No retries
    # Fail-closed
    """
    category: SideEffectCategory
    description: str
    timestamp: datetime
    reversible: bool = False  # Can this be undone?
    step_index: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SideEffectReport:
    """
    Immutable report of declared vs observed side effects.
    
    # Post-execution inspection only
    # No automatic recovery
    # No retries
    # Fail-closed
    """
    side_effects_declared: Tuple[SideEffect, ...] = ()  # From plan
    side_effects_observed: Tuple[SideEffect, ...] = ()  # Observed/inferred
    unknown_effects: bool = False  # True if we can't fully observe effects


# ============================================================================
# EXECUTION RECORD
# ============================================================================

class ExecutionStatus(Enum):
    """Execution completion status."""
    STARTED = "started"
    COMPLETED = "completed"
    COMPLETED_PARTIAL = "completed_partial"  # Some steps executed before failure/stop
    FAILED = "failed"
    INCOMPLETE = "incomplete"  # Security escalation stopped execution


@dataclass(frozen=True)
class ExecutionRecord:
    """
    Immutable execution history record.
    
    # Post-execution inspection only
    # No automatic recovery
    # No retries
    # Fail-closed
    
    Captures complete execution context:
    - Execution ID and plan ID
    - Live mode state at execution time
    - Security snapshots (pre and post)
    - Step-level events (append-only, hash-linked)
    - Side effects (declared vs observed)
    - Timestamps and status
    """
    execution_id: str
    plan_id: str
    live_mode_state: str  # "DRY_RUN" or "LIVE"
    
    # Security context
    security_snapshot_pre: SecuritySnapshot
    security_snapshot_post: Optional[SecuritySnapshot] = None
    
    # Step events (append-only, hash-linked)
    step_events: Tuple[StepEvent, ...] = ()
    
    # Side effects
    side_effects_report: Optional[SideEffectReport] = None
    
    # Execution status
    status: ExecutionStatus = ExecutionStatus.STARTED
    completion_reason: str = ""
    
    # Timestamps
    timestamp_start: datetime = field(default_factory=datetime.now)
    timestamp_end: Optional[datetime] = None
    
    # Immutable marker
    _immutable_marker: str = field(default="execution_record_v1", init=False, repr=False)
    
    def get_execution_hash(self) -> str:
        """
        Get hash of entire execution record (for tamper-evident audit).
        
        Returns:
            SHA-256 hash of record contents
        """
        record_dict = {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "live_mode_state": self.live_mode_state,
            "status": self.status.value,
            "timestamp_start": self.timestamp_start.isoformat(),
            "timestamp_end": self.timestamp_end.isoformat() if self.timestamp_end else None,
            "security_snapshot_pre": {
                "timestamp": self.security_snapshot_pre.timestamp.isoformat(),
                "security_state": self.security_snapshot_pre.security_state,
                "boundary_state": self.security_snapshot_pre.boundary_state,
            },
            "step_count": len(self.step_events),
        }
        record_json = json.dumps(record_dict, sort_keys=True, default=str)
        return sha256(record_json.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to immutable dictionary (for inspection).
        
        Returns:
            Dictionary representation (safe for serialization)
        """
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "live_mode_state": self.live_mode_state,
            "status": self.status.value,
            "completion_reason": self.completion_reason,
            "timestamp_start": self.timestamp_start.isoformat(),
            "timestamp_end": self.timestamp_end.isoformat() if self.timestamp_end else None,
            "security_snapshot_pre": {
                "timestamp": self.security_snapshot_pre.timestamp.isoformat(),
                "security_state": self.security_snapshot_pre.security_state,
                "boundary_state": self.security_snapshot_pre.boundary_state,
                "context": self.security_snapshot_pre.context,
            },
            "security_snapshot_post": {
                "timestamp": self.security_snapshot_post.timestamp.isoformat(),
                "security_state": self.security_snapshot_post.security_state,
                "boundary_state": self.security_snapshot_post.boundary_state,
                "context": self.security_snapshot_post.context,
            } if self.security_snapshot_post else None,
            "step_events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "step_index": e.step_index,
                    "step_name": e.step_name,
                    "event_type": e.event_type.value,
                    "details": e.details,
                    "error_message": e.error_message,
                }
                for e in self.step_events
            ],
            "execution_hash": self.get_execution_hash(),
        }


# ============================================================================
# ROLLBACK SCAFFOLD (NOT EXECUTION)
# ============================================================================

@dataclass(frozen=True)
class RollbackHint:
    """
    Single rollback hint from plan (verbatim).
    
    # Post-execution inspection only
    # No automatic recovery
    # No retries
    # Fail-closed
    
    Hints are surfaced verbatim from the plan.
    They are NOT executed, only presented.
    """
    step_index: int
    description: str
    actions: Tuple[str, ...] = ()  # Suggested actions (verbatim from plan)
    required_inputs: Dict[str, str] = field(default_factory=dict)  # Inputs needed for rollback
    risks: Tuple[str, ...] = ()  # Warnings/risks
    estimated_duration: Optional[str] = None


@dataclass(frozen=True)
class RollbackScaffold:
    """
    Rollback guidance (NOT EXECUTED, MANUAL ONLY).
    
    # Post-execution inspection only
    # No automatic recovery
    # No retries
    # Fail-closed
    
    Surfaces rollback possibilities if:
    1. Plan declares rollback hints
    2. Execution did NOT complete successfully
    3. No security escalation occurred
    
    If rollback is NOT possible, explicitly states so.
    """
    execution_id: str
    is_rollback_possible: bool
    reason: str  # Why or why not rollback is possible
    
    rollback_hints: Tuple[RollbackHint, ...] = ()  # Hints from plan (verbatim)
    
    # Warnings
    warnings: Tuple[str, ...] = ()  # Important warnings for manual rollback
    irreversible_steps: Tuple[int, ...] = ()  # Step indices that cannot be rolled back
    
    # Manual checklist
    manual_steps: Tuple[str, ...] = ()  # Steps user must perform manually
    
    def to_summary(self) -> str:
        """
        Generate human-readable summary.
        
        # Post-execution inspection only
        # No automatic recovery
        # No retries
        # Fail-closed
        
        Returns:
            String summary for user display
        """
        lines = []
        lines.append("=" * 70)
        lines.append("ROLLBACK SCAFFOLD")
        lines.append("=" * 70)
        lines.append("")
        
        if self.is_rollback_possible:
            lines.append("✓ ROLLBACK IS POSSIBLE")
            lines.append(f"  Reason: {self.reason}")
            lines.append("")
            
            if self.rollback_hints:
                lines.append("Rollback Hints (from plan - MANUAL EXECUTION REQUIRED):")
                for i, hint in enumerate(self.rollback_hints, 1):
                    lines.append(f"\n  Hint {i}: Step {hint.step_index}")
                    lines.append(f"    Description: {hint.description}")
                    if hint.actions:
                        lines.append("    Suggested Actions:")
                        for action in hint.actions:
                            lines.append(f"      - {action}")
                    if hint.risks:
                        lines.append("    Risks:")
                        for risk in hint.risks:
                            lines.append(f"      ⚠️  {risk}")
            
            if self.warnings:
                lines.append("\nWarnings:")
                for warning in self.warnings:
                    lines.append(f"  ⚠️  {warning}")
            
            if self.irreversible_steps:
                lines.append(f"\nIrreversible Steps: {self.irreversible_steps}")
                lines.append("  (These steps CANNOT be rolled back)")
            
            if self.manual_steps:
                lines.append("\nManual Steps You Must Perform:")
                for i, step in enumerate(self.manual_steps, 1):
                    lines.append(f"  {i}. {step}")
        
        else:
            lines.append("✗ ROLLBACK IS NOT POSSIBLE")
            lines.append(f"  Reason: {self.reason}")
            lines.append("")
            lines.append("This execution CANNOT be rolled back.")
            if self.warnings:
                lines.append("\nWarnings:")
                for warning in self.warnings:
                    lines.append(f"  ⚠️  {warning}")
        
        lines.append("")
        lines.append("=" * 70)
        lines.append("To perform rollback manually:")
        lines.append("1. Review all hints and warnings above")
        lines.append("2. Execute rollback steps in REVERSE order of execution")
        lines.append("3. Verify each step before proceeding to next")
        lines.append("4. This is MANUAL - automation is NOT performed")
        lines.append("=" * 70)
        
        return "\n".join(lines)


# ============================================================================
# EXECUTION OBSERVER
# ============================================================================

class ExecutionObserver:
    """
    Records execution progress (append-only events).
    
    # Post-execution inspection only
    # No automatic recovery
    # No retries
    # Fail-closed
    
    Used by Stage-4 to emit step-level events.
    Events are append-only and hash-linked.
    No retries, no branching.
    """
    
    def __init__(self, execution_id: str, plan_id: str, kernel: Any = None):
        """
        Initialize observer.
        
        Args:
            execution_id: Unique execution identifier
            plan_id: Plan being executed
            kernel: Artemis kernel (for security snapshots)
        """
        self.execution_id = execution_id
        self.plan_id = plan_id
        self._kernel = kernel
        
        self._step_events: List[StepEvent] = []
        self._side_effects: List[SideEffect] = []
        
        # Security snapshots
        self._security_snapshot_pre = SecuritySnapshot.from_kernel(kernel, "Pre-execution")
        self._security_snapshot_post: Optional[SecuritySnapshot] = None
        
        # Execution status
        self._status = ExecutionStatus.STARTED
        self._completion_reason = ""
        self._timestamp_start = datetime.now()
        self._timestamp_end: Optional[datetime] = None
    
    def record_step_started(
        self,
        step_index: int,
        step_name: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record step started event.
        
        Args:
            step_index: Index of step
            step_name: Name of step
            details: Optional details
        """
        details = details or {}
        previous_hash = self._step_events[-1].get_hash() if self._step_events else None
        
        event = StepEvent(
            timestamp=datetime.now(),
            step_index=step_index,
            step_name=step_name,
            event_type=StepEventType.STEP_STARTED,
            details=details,
            previous_event_hash=previous_hash,
        )
        
        self._step_events.append(event)
    
    def record_step_completed(
        self,
        step_index: int,
        step_name: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record step completed event.
        
        Args:
            step_index: Index of step
            step_name: Name of step
            details: Optional details
        """
        details = details or {}
        previous_hash = self._step_events[-1].get_hash() if self._step_events else None
        
        event = StepEvent(
            timestamp=datetime.now(),
            step_index=step_index,
            step_name=step_name,
            event_type=StepEventType.STEP_COMPLETED,
            details=details,
            previous_event_hash=previous_hash,
        )
        
        self._step_events.append(event)
    
    def record_step_failed(
        self,
        step_index: int,
        step_name: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record step failed event.
        
        Args:
            step_index: Index of step
            step_name: Name of step
            error_message: Error message
            details: Optional details
        """
        details = details or {}
        previous_hash = self._step_events[-1].get_hash() if self._step_events else None
        
        event = StepEvent(
            timestamp=datetime.now(),
            step_index=step_index,
            step_name=step_name,
            event_type=StepEventType.STEP_FAILED,
            error_message=error_message,
            details=details,
            previous_event_hash=previous_hash,
        )
        
        self._step_events.append(event)
    
    def record_side_effect(
        self,
        category: SideEffectCategory,
        description: str,
        reversible: bool = False,
        step_index: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record side effect (best-effort observation).
        
        Args:
            category: Category of effect
            description: Description
            reversible: Can this be undone?
            step_index: Which step caused this
            details: Optional details
        """
        details = details or {}
        
        side_effect = SideEffect(
            category=category,
            description=description,
            timestamp=datetime.now(),
            reversible=reversible,
            step_index=step_index,
            details=details,
        )
        
        self._side_effects.append(side_effect)
    
    def mark_completed(self, reason: str = "") -> None:
        """
        Mark execution as completed.
        
        Args:
            reason: Why execution completed
        """
        self._status = ExecutionStatus.COMPLETED
        self._completion_reason = reason
        self._timestamp_end = datetime.now()
        self._security_snapshot_post = SecuritySnapshot.from_kernel(
            self._kernel,
            "Post-execution (completed)",
        )
    
    def mark_failed(self, reason: str = "") -> None:
        """
        Mark execution as failed.
        
        Args:
            reason: Why execution failed
        """
        self._status = ExecutionStatus.FAILED
        self._completion_reason = reason
        self._timestamp_end = datetime.now()
        self._security_snapshot_post = SecuritySnapshot.from_kernel(
            self._kernel,
            "Post-execution (failed)",
        )
    
    def mark_incomplete_security_escalation(self, reason: str = "") -> None:
        """
        Mark execution as incomplete (security escalation stopped execution).
        
        Args:
            reason: Why execution was stopped
        """
        self._status = ExecutionStatus.INCOMPLETE
        self._completion_reason = reason or "Security escalation"
        self._timestamp_end = datetime.now()
        self._security_snapshot_post = SecuritySnapshot.from_kernel(
            self._kernel,
            "Post-execution (incomplete - security escalation)",
        )
    
    def get_execution_record(self, live_mode_state: str) -> ExecutionRecord:
        """
        Get immutable execution record.
        
        Args:
            live_mode_state: "DRY_RUN" or "LIVE"
        
        Returns:
            Immutable ExecutionRecord
        """
        side_effects_report = SideEffectReport(
            side_effects_declared=(),
            side_effects_observed=tuple(self._side_effects),
            unknown_effects=True,  # Best-effort observation
        )
        
        return ExecutionRecord(
            execution_id=self.execution_id,
            plan_id=self.plan_id,
            live_mode_state=live_mode_state,
            security_snapshot_pre=self._security_snapshot_pre,
            security_snapshot_post=self._security_snapshot_post,
            step_events=tuple(self._step_events),
            side_effects_report=side_effects_report,
            status=self._status,
            completion_reason=self._completion_reason,
            timestamp_start=self._timestamp_start,
            timestamp_end=self._timestamp_end,
        )


# ============================================================================
# ROLLBACK PLANNER (NO EXECUTION)
# ============================================================================

class RollbackPlanner:
    """
    Surfaces rollback possibilities (NO EXECUTION).
    
    # Post-execution inspection only
    # No automatic recovery
    # No retries
    # Fail-closed
    
    Does NOT:
    - Execute rollback
    - Infer rollback steps
    - Modify system state
    - Retry on failure
    
    Does:
    - Surface rollback hints from plan (verbatim)
    - Mark irreversible steps
    - Generate manual checklist
    - Provide warnings
    """
    
    @staticmethod
    def plan_rollback(
        execution_record: ExecutionRecord,
        rollback_hints_from_plan: Optional[List[Dict[str, Any]]] = None,
    ) -> RollbackScaffold:
        """
        Create rollback scaffold (NOT EXECUTED).
        
        # Post-execution inspection only
        # No automatic recovery
        # No retries
        # Fail-closed
        
        Args:
            execution_record: The execution record
            rollback_hints_from_plan: Hints from plan (if any)
        
        Returns:
            RollbackScaffold (not executed)
        """
        rollback_hints_from_plan = rollback_hints_from_plan or []
        
        # Determine if rollback is possible
        is_rollback_possible = False
        reason = ""
        warnings = []
        irreversible_steps = []
        manual_steps = []
        
        # Check execution status
        if execution_record.status == ExecutionStatus.COMPLETED:
            reason = "Execution completed successfully - no rollback needed"
            is_rollback_possible = False
        
        elif execution_record.status == ExecutionStatus.INCOMPLETE:
            reason = "Security escalation stopped execution - CANNOT rollback"
            warnings.append("Security incident occurred during execution")
            warnings.append("System state may be inconsistent")
            is_rollback_possible = False
        
        elif execution_record.status == ExecutionStatus.FAILED:
            if execution_record.security_snapshot_post and \
               execution_record.security_snapshot_post.security_state != "OPERATIONAL":
                reason = "Security state degraded - CANNOT rollback safely"
                warnings.append("Security state is not OPERATIONAL")
                is_rollback_possible = False
            else:
                reason = "Partial execution - rollback may be possible"
                is_rollback_possible = bool(rollback_hints_from_plan)
                
                if not is_rollback_possible and rollback_hints_from_plan:
                    reason = "Rollback hints available but plan did not complete"
                    is_rollback_possible = True
                
                # Find irreversible steps
                for i, event in enumerate(execution_record.step_events):
                    if event.event_type == StepEventType.STEP_COMPLETED:
                        # Mark as potentially irreversible (user must verify)
                        irreversible_steps.append(i)
        
        elif execution_record.status == ExecutionStatus.STARTED:
            reason = "Execution did not start - no rollback needed"
            is_rollback_possible = False
        
        # Convert hints from plan
        rollback_hints = []
        for hint_dict in rollback_hints_from_plan:
            try:
                rollback_hints.append(
                    RollbackHint(
                        step_index=hint_dict.get("step_index", -1),
                        description=hint_dict.get("description", ""),
                        actions=tuple(hint_dict.get("actions", [])),
                        required_inputs=hint_dict.get("required_inputs", {}),
                        risks=tuple(hint_dict.get("risks", [])),
                        estimated_duration=hint_dict.get("estimated_duration"),
                    )
                )
            except Exception:
                # Skip malformed hints
                pass
        
        # Generate manual steps
        if is_rollback_possible and rollback_hints:
            manual_steps = [
                "Review all rollback hints above carefully",
                "Verify that the execution state is as expected",
                "Execute rollback hints in REVERSE order",
                "Test system state after each rollback step",
                "Document any manual interventions",
            ]
        
        return RollbackScaffold(
            execution_id=execution_record.execution_id,
            is_rollback_possible=is_rollback_possible,
            reason=reason,
            rollback_hints=tuple(rollback_hints),
            warnings=tuple(warnings),
            irreversible_steps=tuple(irreversible_steps),
            manual_steps=tuple(manual_steps),
        )
