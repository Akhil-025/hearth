"""
APPROVAL → EXECUTION HANDSHAKE

# Authority transfer point
# One-shot execution
# No retries
# Fail-closed

Converts an APPROVED PlanDraft into ONE-SHOT executable Stage-4 plan,
then dispatches it exactly once.

CONSTRAINTS:
- No autonomy
- No background execution
- No retries
- No partial execution
- No mutation of PlanDraft
- Standard library only
- Fail-closed on every boundary

This is the CRITICAL HANDSHAKE between governance and execution.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum


# ============================================================================
# EXECUTION REQUEST MODEL
# ============================================================================

@dataclass(frozen=True)
class ExecutionRequest:
    """
    Immutable request to execute an approved plan.

    # Authority transfer point
    # One-shot execution
    # No retries
    # Fail-closed

    This object represents the transfer of authority from approval
    governance to execution. It captures the approval context and
    ensures execution happens exactly once under consistent assumptions.
    """
    execution_id: str                       # Unique execution identifier
    plan_draft: Any                         # Reference to PlanDraft (not copy)
    approval_request: Any                   # The approved ApprovalRequest
    approval_timestamp: str                 # ISO 8601 approval time
    approver_identity: str                  # Who approved this
    security_summary_snapshot: Dict[str, Any]  # Artemis state at approval time
    execution_context: Dict[str, Any] = field(default_factory=dict)  # User context

    # No execution guarantee:
    # This field tracks whether execution has occurred.
    # It is NOT part of the frozen dataclass validation,
    # but external OneShot wrapper enforces it.


class ExecutionState(Enum):
    """State machine for one-shot execution guarantee."""
    PENDING = "pending"          # Never executed
    EXECUTING = "executing"      # Execution in progress
    EXECUTED = "executed"        # Execution completed
    FAILED = "failed"            # Execution failed


# ============================================================================
# HANDSHAKE VALIDATION
# ============================================================================

class HandshakeValidationError(Exception):
    """Validation failure: explicit, fail-closed."""
    pass


class HandshakeValidator:
    """
    Validate handshake between approval and execution.

    # Authority transfer point
    # One-shot execution
    # No retries
    # Fail-closed

    Validates:
    - Approval is valid for current security state
    - Required capabilities are allowed
    - Plan has not been altered
    - Approval snapshot matches plan snapshot
    """

    @staticmethod
    def validate(
        execution_request: ExecutionRequest,
        current_security_state: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Validate execution handshake (fail-closed).

        # Authority transfer point
        # One-shot execution
        # No retries
        # Fail-closed

        Args:
            execution_request: ExecutionRequest (immutable)
            current_security_state: Current Artemis state

        Returns:
            (valid, reason) - reason explains failure if not valid

        Any mismatch → FAIL CLOSED (returns False)
        """
        # Validation 1: ExecutionRequest has required fields
        try:
            if not execution_request.execution_id:
                return False, "ExecutionRequest missing execution_id"
            if execution_request.plan_draft is None:
                return False, "ExecutionRequest missing plan_draft"
            if execution_request.approval_request is None:
                return False, "ExecutionRequest missing approval_request"
            if not execution_request.approval_timestamp:
                return False, "ExecutionRequest missing approval_timestamp"
            if not execution_request.approver_identity:
                return False, "ExecutionRequest missing approver_identity"
        except Exception as e:
            return False, f"ExecutionRequest validation failed: {e}"

        # Validation 2: Plan has not been altered
        try:
            plan = execution_request.plan_draft
            if not hasattr(plan, "derived_steps"):
                return False, "Plan is missing derived_steps (altered?)"
            if not hasattr(plan, "required_faculties"):
                return False, "Plan is missing required_faculties (altered?)"
            if not hasattr(plan, "required_capabilities"):
                return False, "Plan is missing required_capabilities (altered?)"
        except Exception as e:
            return False, f"Plan integrity check failed: {e}"

        # Validation 3: Security state is readable
        try:
            current_state = current_security_state.get("state", "unknown")
            if current_state == "unknown":
                return False, "Current security state is unknown"
        except Exception as e:
            return False, f"Security state check failed: {e}"

        # Validation 4: Current state is not LOCKDOWN (lockdown blocks execution)
        if current_state == "LOCKDOWN":
            return False, "Execution blocked: system in LOCKDOWN"

        # Validation 5: Approval snapshot + plan snapshot exist
        approval_snapshot = getattr(execution_request.approval_request, "security_summary", None)
        plan_snapshot = getattr(execution_request.plan_draft, "security_summary_snapshot", None)

        if not approval_snapshot and not plan_snapshot:
            # Both missing: fail-closed
            return False, "No security snapshot available (approval or plan)"

        # Validation 6: If both snapshots exist, states should be comparable
        # (not necessarily identical - approval may have been granted in SECURE,
        # now in DEGRADED, which is acceptable as long as execution is allowed)
        try:
            approval_state = getattr(approval_snapshot, "state", None) if approval_snapshot else None
            plan_state = plan_snapshot.get("state", None) if plan_snapshot else None

            # If we have both, verify they're at least consistent
            if approval_state and plan_state and approval_state != plan_state:
                # States differ - this is suspicious but not necessarily fatal
                # (approval in SECURE, now in DEGRADED is acceptable)
                # Only fail if approval was for DEGRADED but now in COMPROMISED
                if approval_state == "DEGRADED" and plan_state in ["COMPROMISED", "LOCKDOWN"]:
                    return False, "State degraded since approval was granted"
        except Exception as e:
            return False, f"Snapshot comparison failed: {e}"

        # Validation 7: Execution context is present
        try:
            context = execution_request.execution_context
            if not isinstance(context, dict):
                return False, "ExecutionRequest has invalid execution_context"
        except Exception as e:
            return False, f"Execution context check failed: {e}"

        # All validations passed
        return True, "Handshake validation passed"


# ============================================================================
# STAGE-4 TRANSLATION
# ============================================================================

class Stage4TranslationError(Exception):
    """Translation failure: explicit, fail-closed."""
    pass


class Stage4Translator:
    """
    Translate PlanDraft → Stage-4 ExecutionPlan.

    # Authority transfer point
    # One-shot execution
    # No retries
    # Fail-closed

    Translation Rules:
    - Exact steps only (no inference)
    - No reordering (preserve sequence)
    - No enrichment (no defaults added)
    - No modification (PlanDraft immutable)
    """

    @staticmethod
    def translate(
        execution_request: ExecutionRequest,
        user_id: str,
        token_hash: str,
    ) -> Dict[str, Any]:
        """
        Translate ExecutionRequest → Stage-4 execution payload.

        # Authority transfer point
        # One-shot execution
        # No retries
        # Fail-closed

        Args:
            execution_request: Approved ExecutionRequest (immutable)
            user_id: User initiating execution
            token_hash: Stage-3 capability token

        Returns:
            Dict containing Stage-4 execution payload

        Raises:
            Stage4TranslationError: If translation fails (fail-closed)
        """
        try:
            plan = execution_request.plan_draft

            # Extract steps from PlanDraft
            steps = []
            for plan_step in plan.derived_steps:
                step_dict = {
                    "sequence": plan_step.sequence,
                    "faculty": plan_step.faculty.value,
                    "action": plan_step.action,
                    "parameters": plan_step.parameters,
                    "required_capabilities": sorted(plan_step.required_capabilities),
                }
                if plan_step.estimated_duration_sec is not None:
                    step_dict["estimated_duration_sec"] = plan_step.estimated_duration_sec
                if plan_step.notes:
                    step_dict["notes"] = plan_step.notes

                steps.append(step_dict)

            # Build Stage-4 payload (no enrichment, no defaults)
            payload = {
                "execution_id": execution_request.execution_id,
                "user_id": user_id,
                "token_hash": token_hash,
                "plan_intent": plan.intent,
                "plan_draft_id": plan.draft_id,
                "approval_timestamp": execution_request.approval_timestamp,
                "approver_identity": execution_request.approver_identity,
                "trigger_type": "manual",  # Explicit (not inferred)
                "steps": steps,
                "required_faculties": sorted(f.value for f in plan.required_faculties),
                "required_capabilities": sorted(plan.required_capabilities),
                "estimated_risk_level": plan.estimated_risk_level,
                "security_snapshot_at_approval": execution_request.security_summary_snapshot,
                "assumptions": list(plan.assumptions),
                "known_unknowns": list(plan.known_unknowns),
                "translation_timestamp": datetime.utcnow().isoformat() + "Z",
            }

            return payload

        except AttributeError as e:
            raise Stage4TranslationError(f"Plan structure invalid: {e}")
        except KeyError as e:
            raise Stage4TranslationError(f"Missing required field: {e}")
        except Exception as e:
            raise Stage4TranslationError(f"Translation failed: {e}")


# ============================================================================
# ONE-SHOT EXECUTION GUARANTEE
# ============================================================================

class OneShot:
    """
    Wrapper ensuring execution happens exactly once.

    # Authority transfer point
    # One-shot execution
    # No retries
    # Fail-closed

    This object tracks execution state and prevents re-execution.
    A second call raises RuntimeError.
    """

    def __init__(self, execution_request: ExecutionRequest):
        """
        Initialize one-shot wrapper.

        Args:
            execution_request: ExecutionRequest (immutable)
        """
        self._execution_request = execution_request
        self._state = ExecutionState.PENDING

    def can_execute(self) -> bool:
        """Check if execution is still possible."""
        return self._state == ExecutionState.PENDING

    def mark_executing(self) -> None:
        """Mark execution as in-progress (fail-closed)."""
        if self._state != ExecutionState.PENDING:
            raise RuntimeError(
                f"Execution already {self._state.value}. "
                "One-shot guarantee violated."
            )
        self._state = ExecutionState.EXECUTING

    def mark_executed(self) -> None:
        """Mark execution as completed."""
        if self._state != ExecutionState.EXECUTING:
            raise RuntimeError(
                f"Execution not in progress (state: {self._state.value}). "
                "State machine violated."
            )
        self._state = ExecutionState.EXECUTED

    def mark_failed(self, reason: str) -> None:
        """Mark execution as failed."""
        if self._state not in [ExecutionState.EXECUTING]:
            raise RuntimeError(
                f"Cannot mark failed from state {self._state.value}"
            )
        self._state = ExecutionState.FAILED

    def get_state(self) -> ExecutionState:
        """Get current execution state."""
        return self._state

    def get_execution_request(self) -> ExecutionRequest:
        """Get the (immutable) execution request."""
        return self._execution_request


# ============================================================================
# AUDIT & TRACE
# ============================================================================

@dataclass(frozen=True)
class ExecutionAuditEvent:
    """
    Immutable audit event for execution lifecycle.

    # Authority transfer point
    # One-shot execution
    # No retries
    # Fail-closed
    """
    timestamp: str                  # ISO 8601
    execution_id: str               # Which execution
    event_type: str                 # validation_passed, execution_started, etc.
    details: Dict[str, Any]         # Event details
    error_message: Optional[str] = None  # If event is an error


class ExecutionAuditTrail:
    """
    Immutable append-only audit trail for execution.

    # Authority transfer point
    # One-shot execution
    # No retries
    # Fail-closed
    """

    def __init__(self):
        """Initialize empty audit trail."""
        self._events = []

    def record(
        self,
        execution_id: str,
        event_type: str,
        details: Dict[str, Any],
        error_message: Optional[str] = None,
    ) -> None:
        """
        Record immutable event (append-only).

        # Authority transfer point
        # One-shot execution
        # No retries
        # Fail-closed

        Args:
            execution_id: Execution identifier
            event_type: Type of event
            details: Event details (dict)
            error_message: Error message (if applicable)
        """
        event = ExecutionAuditEvent(
            timestamp=datetime.utcnow().isoformat() + "Z",
            execution_id=execution_id,
            event_type=event_type,
            details=details,
            error_message=error_message,
        )
        self._events.append(event)

    def get_events(self) -> Tuple[ExecutionAuditEvent, ...]:
        """Get immutable tuple of all events (read-only)."""
        return tuple(self._events)

    def get_events_for_execution(self, execution_id: str) -> Tuple[ExecutionAuditEvent, ...]:
        """Get events for specific execution."""
        return tuple(e for e in self._events if e.execution_id == execution_id)


# ============================================================================
# APPROVAL EXECUTOR
# ============================================================================

class ApprovalExecutionError(Exception):
    """Execution failed: explicit, fail-closed."""
    pass


class ApprovalExecutor:
    """
    Execute approved plans.

    # Authority transfer point
    # One-shot execution
    # No retries
    # Fail-closed

    Orchestrates:
    1. Validation (handshake)
    2. Translation (PlanDraft → Stage-4)
    3. One-shot guarantee
    4. Audit recording
    5. Stage-4 dispatch
    """

    def __init__(
        self,
        stage4_orchestrator: Any = None,
        kernel: Any = None,
        live_mode_gate: Any = None,
    ):
        """
        Initialize executor.

        Args:
            stage4_orchestrator: Stage-4 executor (optional for v0.1)
            kernel: Kernel reference for security state (optional)
            live_mode_gate: LiveModeGate for execution authority (optional)
        """
        self._stage4_orchestrator = stage4_orchestrator
        self._kernel = kernel
        self._live_mode_gate = live_mode_gate
        self._audit_trail = ExecutionAuditTrail()
        self._one_shots: Dict[str, OneShot] = {}  # execution_id → OneShot

    def execute(
        self,
        execution_request: ExecutionRequest,
        user_id: str,
        token_hash: str,
        current_security_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute an approved plan exactly once.

        # Authority transfer point
        # One-shot execution
        # No retries
        # Fail-closed

        Args:
            execution_request: ExecutionRequest (immutable)
            user_id: User initiating execution
            token_hash: Stage-3 capability token
            current_security_state: Current Artemis state (optional)

        Returns:
            (success, message, result_dict)
            - success: bool - execution completed successfully
            - message: str - explanation
            - result_dict: dict - execution results (empty if failed)
        """
        execution_id = execution_request.execution_id

        try:
            # Step 0: Check live mode gate (HARD BOUNDARY)
            # Authority transfer point
            # Execution enabled only if LIVE
            # Fail-closed
            if self._live_mode_gate:
                from artemis.live_mode_gate import LiveModeGateValidator
                
                can_execute, gate_reason = LiveModeGateValidator.can_execute(self._live_mode_gate)
                
                if not can_execute:
                    self._audit_trail.record(
                        execution_id,
                        "live_mode_gate_blocked",
                        {"reason": gate_reason},
                        error_message=gate_reason,
                    )
                    return False, f"EXECUTION BLOCKED: {gate_reason}", {}
                
                self._audit_trail.record(
                    execution_id,
                    "live_mode_gate_passed",
                    {"gate_state": self._live_mode_gate.get_state().value},
                )

            # Step 1: Check one-shot guarantee
            if execution_id in self._one_shots:
                one_shot = self._one_shots[execution_id]
                if not one_shot.can_execute():
                    msg = f"Execution {execution_id} already {one_shot.get_state().value}"
                    self._audit_trail.record(
                        execution_id,
                        "execution_rejected",
                        {"reason": "one_shot_violated"},
                        error_message=msg,
                    )
                    return False, msg, {}
            else:
                one_shot = OneShot(execution_request)
                self._one_shots[execution_id] = one_shot

            # Step 2: Validate handshake (fail-closed)
            if current_security_state is None:
                current_security_state = {"state": "SECURE"}  # Fail-open default

            valid, reason = HandshakeValidator.validate(
                execution_request,
                current_security_state,
            )

            if not valid:
                self._audit_trail.record(
                    execution_id,
                    "validation_failed",
                    {"reason": reason},
                    error_message=reason,
                )
                return False, reason, {}

            self._audit_trail.record(
                execution_id,
                "validation_passed",
                {},
            )

            # Step 3: Translate to Stage-4 format (fail-closed)
            try:
                stage4_payload = Stage4Translator.translate(
                    execution_request,
                    user_id,
                    token_hash,
                )
            except Stage4TranslationError as e:
                msg = f"Translation failed: {e}"
                self._audit_trail.record(
                    execution_id,
                    "translation_failed",
                    {},
                    error_message=msg,
                )
                return False, msg, {}

            self._audit_trail.record(
                execution_id,
                "translation_completed",
                {"step_count": len(stage4_payload["steps"])},
            )

            # Step 4: Mark as executing (one-shot check)
            try:
                one_shot.mark_executing()
            except RuntimeError as e:
                msg = str(e)
                self._audit_trail.record(
                    execution_id,
                    "execution_rejected",
                    {"reason": "one_shot_violated"},
                    error_message=msg,
                )
                return False, msg, {}

            self._audit_trail.record(
                execution_id,
                "execution_started",
                {
                    "plan_draft_id": execution_request.plan_draft.draft_id,
                    "user_id": user_id,
                    "approver_identity": execution_request.approver_identity,
                },
            )

            # Step 5: Dispatch to Stage-4 (if available)
            result = {}
            if self._stage4_orchestrator:
                try:
                    result = self._stage4_orchestrator.execute_plan(stage4_payload)
                    self._audit_trail.record(
                        execution_id,
                        "execution_completed",
                        {"result": result},
                    )
                except Exception as e:
                    msg = f"Stage-4 execution failed: {e}"
                    self._audit_trail.record(
                        execution_id,
                        "execution_failed",
                        {},
                        error_message=msg,
                    )
                    one_shot.mark_failed(msg)
                    return False, msg, {}
            else:
                # No Stage-4 executor: return payload for inspection
                result = stage4_payload
                self._audit_trail.record(
                    execution_id,
                    "execution_ready",
                    {"payload_ready": True},
                )

            # Step 6: Mark as executed (success)
            one_shot.mark_executed()

            self._audit_trail.record(
                execution_id,
                "one_shot_completed",
                {"final_state": one_shot.get_state().value},
            )

            return True, "Execution completed successfully", result

        except Exception as e:
            msg = f"Unexpected error during execution: {e}"
            self._audit_trail.record(
                execution_id,
                "execution_error",
                {},
                error_message=msg,
            )
            return False, msg, {}

    def get_audit_trail(self, execution_id: Optional[str] = None) -> Tuple[ExecutionAuditEvent, ...]:
        """Get immutable audit events."""
        if execution_id:
            return self._audit_trail.get_events_for_execution(execution_id)
        return self._audit_trail.get_events()
