"""
APPROVAL → EXECUTION HANDSHAKE EXAMPLES

# Authority transfer point
# One-shot execution
# No retries
# Fail-closed

Demonstrates the handshake between approval governance and execution.
"""

from artemis.approval_executor import (
    ExecutionRequest,
    HandshakeValidator,
    Stage4Translator,
    OneShot,
    ApprovalExecutor,
    ExecutionState,
    HandshakeValidationError,
    Stage4TranslationError,
)
from datetime import datetime
from uuid import uuid4


def example_1_successful_handshake():
    """Example: Successful approval → execution handshake."""
    print("=" * 70)
    print("EXAMPLE 1: Successful Approval → Execution Handshake")
    print("=" * 70)

    # Create mock PlanDraft
    class MockPlanDraft:
        def __init__(self):
            self.draft_id = "plan-001"
            self.intent = "Learn Python decorators"
            self.derived_steps = [
                MockStep(1, "READ_KNOWLEDGE", "Query knowledge base"),
                MockStep(2, "ANALYZE_CODE", "Analyze patterns"),
            ]
            self.required_faculties = frozenset(["READ_KNOWLEDGE", "ANALYZE_CODE"])
            self.required_capabilities = frozenset(["KNOWLEDGE_READ", "ANALYSIS"])
            self.estimated_risk_level = "low"
            self.assumptions = ("User has knowledge access",)
            self.known_unknowns = ("Exact time required",)
            self.security_summary_snapshot = {"state": "SECURE"}

    class MockStep:
        def __init__(self, seq, faculty, action):
            self.sequence = seq
            self.faculty = type("Faculty", (), {"value": faculty})()
            self.action = action
            self.parameters = {}
            self.required_capabilities = frozenset(["KNOWLEDGE_READ"])
            self.estimated_duration_sec = 5.0
            self.notes = ""

    # Create mock ApprovalRequest
    class MockApprovalRequest:
        def __init__(self):
            self.security_summary = type("Summary", (), {"state": "SECURE"})()

    # Build ExecutionRequest
    execution_id = "exec-" + str(uuid4())[:8]
    plan = MockPlanDraft()
    approval = MockApprovalRequest()

    exec_request = ExecutionRequest(
        execution_id=execution_id,
        plan_draft=plan,
        approval_request=approval,
        approval_timestamp=datetime.utcnow().isoformat() + "Z",
        approver_identity="admin@hearth.local",
        security_summary_snapshot={"state": "SECURE"},
        execution_context={"user_id": "user-123"},
    )

    print(f"✓ ExecutionRequest created: {execution_id}")
    print(f"  Plan: {plan.draft_id}")
    print(f"  Approver: {exec_request.approver_identity}")
    print()

    # Validate handshake
    current_state = {"state": "SECURE"}
    valid, reason = HandshakeValidator.validate(exec_request, current_state)

    print(f"✓ Handshake validation: {valid}")
    print(f"  Reason: {reason}")
    print()

    # Translate to Stage-4
    try:
        payload = Stage4Translator.translate(
            exec_request,
            user_id="user-123",
            token_hash="token-abc123",
        )
        print(f"✓ Translated to Stage-4")
        print(f"  Steps: {len(payload['steps'])}")
        print(f"  Risk level: {payload['estimated_risk_level']}")
        print()
    except Stage4TranslationError as e:
        print(f"✗ Translation failed: {e}")
        print()

    return exec_request


def example_2_one_shot_guarantee():
    """Example: One-shot execution guarantee."""
    print("=" * 70)
    print("EXAMPLE 2: One-Shot Execution Guarantee")
    print("=" * 70)

    # Create mock ExecutionRequest
    exec_request = ExecutionRequest(
        execution_id="exec-oneshot",
        plan_draft=None,  # Not needed for this example
        approval_request=None,
        approval_timestamp=datetime.utcnow().isoformat() + "Z",
        approver_identity="admin",
        security_summary_snapshot={},
    )

    one_shot = OneShot(exec_request)

    print(f"✓ OneShot created, state: {one_shot.get_state().value}")

    # First execution attempt
    if one_shot.can_execute():
        print(f"✓ Can execute: True")
        try:
            one_shot.mark_executing()
            print(f"✓ Marked as executing, state: {one_shot.get_state().value}")

            one_shot.mark_executed()
            print(f"✓ Marked as executed, state: {one_shot.get_state().value}")
        except RuntimeError as e:
            print(f"✗ Error: {e}")
    else:
        print(f"✗ Cannot execute (state: {one_shot.get_state().value})")

    print()

    # Second execution attempt (should fail)
    print(f"Attempting second execution...")
    if one_shot.can_execute():
        print(f"✗ ERROR: Should not allow second execution!")
    else:
        print(f"✓ CORRECTLY BLOCKED second execution (state: {one_shot.get_state().value})")
    print()


def example_3_failed_validation():
    """Example: Fail-closed on validation error."""
    print("=" * 70)
    print("EXAMPLE 3: Fail-Closed Validation Error")
    print("=" * 70)

    # Create invalid ExecutionRequest (missing plan_draft)
    exec_request = ExecutionRequest(
        execution_id="exec-invalid",
        plan_draft=None,  # MISSING
        approval_request=None,
        approval_timestamp=datetime.utcnow().isoformat() + "Z",
        approver_identity="admin",
        security_summary_snapshot={},
    )

    current_state = {"state": "SECURE"}
    valid, reason = HandshakeValidator.validate(exec_request, current_state)

    print(f"Validation result: {valid}")
    print(f"Reason: {reason}")
    print()

    if not valid:
        print(f"✓ CORRECTLY REJECTED: {reason}")
    print()


def example_4_lockdown_blocks_execution():
    """Example: LOCKDOWN state blocks execution."""
    print("=" * 70)
    print("EXAMPLE 4: LOCKDOWN Blocks Execution")
    print("=" * 70)

    class MockPlanDraft:
        def __init__(self):
            self.derived_steps = []
            self.required_faculties = frozenset()
            self.required_capabilities = frozenset()

    exec_request = ExecutionRequest(
        execution_id="exec-lockdown",
        plan_draft=MockPlanDraft(),
        approval_request=None,
        approval_timestamp=datetime.utcnow().isoformat() + "Z",
        approver_identity="admin",
        security_summary_snapshot={"state": "SECURE"},
    )

    # Validation with SECURE state (should pass)
    current_state_secure = {"state": "SECURE"}
    valid, reason = HandshakeValidator.validate(exec_request, current_state_secure)
    print(f"With SECURE state: {valid}")

    # Validation with LOCKDOWN state (should fail)
    current_state_lockdown = {"state": "LOCKDOWN"}
    valid, reason = HandshakeValidator.validate(exec_request, current_state_lockdown)
    print(f"With LOCKDOWN state: {valid}")
    print(f"Reason: {reason}")
    print()

    if not valid:
        print(f"✓ CORRECTLY BLOCKED execution in LOCKDOWN")
    print()


def example_5_approval_executor():
    """Example: ApprovalExecutor orchestration."""
    print("=" * 70)
    print("EXAMPLE 5: ApprovalExecutor Orchestration")
    print("=" * 70)

    class MockPlanDraft:
        def __init__(self):
            self.draft_id = "plan-exec"
            self.intent = "Test execution"
            self.derived_steps = [MockStep()]
            self.required_faculties = frozenset()
            self.required_capabilities = frozenset()
            self.estimated_risk_level = "low"
            self.assumptions = ()
            self.known_unknowns = ()
            self.security_summary_snapshot = {"state": "SECURE"}

    class MockStep:
        def __init__(self):
            self.sequence = 1
            self.faculty = type("F", (), {"value": "READ_KNOWLEDGE"})()
            self.action = "Query"
            self.parameters = {}
            self.required_capabilities = frozenset()
            self.estimated_duration_sec = 1.0
            self.notes = ""

    execution_id = "exec-orch"
    exec_request = ExecutionRequest(
        execution_id=execution_id,
        plan_draft=MockPlanDraft(),
        approval_request=None,
        approval_timestamp=datetime.utcnow().isoformat() + "Z",
        approver_identity="admin",
        security_summary_snapshot={"state": "SECURE"},
    )

    executor = ApprovalExecutor(stage4_orchestrator=None, kernel=None)

    success, message, result = executor.execute(
        exec_request,
        user_id="user-123",
        token_hash="token-xyz",
        current_security_state={"state": "SECURE"},
    )

    print(f"Execution result: {success}")
    print(f"Message: {message}")
    print()

    # Get audit trail
    events = executor.get_audit_trail(execution_id)
    print(f"Audit events: {len(events)}")
    for event in events:
        print(f"  - {event.event_type} ({event.timestamp})")
    print()

    # Attempt second execution (should fail due to one-shot)
    print(f"Attempting second execution...")
    success2, message2, _ = executor.execute(
        exec_request,
        user_id="user-123",
        token_hash="token-xyz",
    )

    print(f"Second execution result: {success2}")
    print(f"Message: {message2}")
    print()

    if not success2 and "already" in message2.lower():
        print(f"✓ CORRECTLY BLOCKED second execution")
    print()


def example_6_audit_trail_immutability():
    """Example: Audit trail is immutable."""
    print("=" * 70)
    print("EXAMPLE 6: Audit Trail Immutability")
    print("=" * 70)

    from artemis.approval_executor import ExecutionAuditTrail

    trail = ExecutionAuditTrail()

    # Record events
    trail.record("exec-1", "started", {"user_id": "user-123"})
    trail.record("exec-1", "completed", {"result": "success"})

    events = trail.get_events()
    print(f"Audit events recorded: {len(events)}")
    print(f"Events type: {type(events).__name__}")

    # Try to modify (should fail)
    try:
        events[0] = None  # Attempt mutation
        print(f"✗ ERROR: Should not be able to modify events tuple!")
    except TypeError:
        print(f"✓ CORRECTLY BLOCKED mutation (tuple immutable)")

    print()


if __name__ == "__main__":
    print()
    print("APPROVAL → EXECUTION HANDSHAKE EXAMPLES")
    print()

    example_1_successful_handshake()
    example_2_one_shot_guarantee()
    example_3_failed_validation()
    example_4_lockdown_blocks_execution()
    example_5_approval_executor()
    example_6_audit_trail_immutability()

    print("=" * 70)
    print("All examples completed")
    print("=" * 70)
