"""
APPROVAL → EXECUTION HANDSHAKE - QUICK REFERENCE

# Authority transfer point
# One-shot execution
# No retries
# Fail-closed

============================================================================
AT A GLANCE
============================================================================

PURPOSE:    Authority transfer from approval → execution
MODEL:      Immutable ExecutionRequest + OneShot wrapper
OUTPUT:     Stage-4 execution payload + audit trail
NO:         Autonomy, background tasks, retries, partial execution
GUARANTEE:  Exactly one execution per execution_id


============================================================================
CORE COMPONENTS
============================================================================

ExecutionRequest (frozen dataclass)
  - execution_id: unique ID
  - plan_draft: reference to PlanDraft
  - approval_request: approved request
  - approval_timestamp: when approved
  - approver_identity: who approved
  - security_summary_snapshot: state at approval time
  → Immutable record of authority transfer

HandshakeValidator
  - Validates 7 checks (fail-closed)
  - Rejects if LOCKDOWN
  - Rejects if validation fails
  - Returns (bool, reason)

Stage4Translator
  - Converts ExecutionRequest → Stage-4 payload
  - Exact translation (no inference)
  - No reordering (preserve sequence)
  - Raises Stage4TranslationError on failure

OneShot
  - Ensures exactly one execution
  - State: PENDING → EXECUTING → EXECUTED
  - RuntimeError on second attempt
  - Tracks execution state

ExecutionAuditTrail (append-only)
  - Records every event
  - Immutable events (frozen dataclasses)
  - Queryable by execution_id
  - Immutable tuple returns

ApprovalExecutor
  - Main orchestrator
  - Chains: validate → translate → execute
  - Returns (success, message, result)
  - Manages OneShot + audit trail


============================================================================
USAGE FLOW
============================================================================

1. CREATE ExecutionRequest
   exec_req = ExecutionRequest(
       execution_id="exec-123",
       plan_draft=plan,
       approval_request=approval,
       approval_timestamp=now,
       approver_identity="admin",
       security_summary_snapshot=state,
   )

2. CREATE ApprovalExecutor
   executor = ApprovalExecutor(
       stage4_orchestrator=stage4,
       kernel=kernel
   )

3. EXECUTE PLAN
   success, message, result = executor.execute(
       execution_request=exec_req,
       user_id="user-123",
       token_hash="token-xyz",
       current_security_state={"state": "SECURE"}
   )

4. CHECK RESULT
   if success:
       print("Execution completed")
   else:
       print(f"Failed: {message}")

5. VIEW AUDIT TRAIL
   events = executor.get_audit_trail(exec_req.execution_id)
   for event in events:
       print(f"{event.event_type}: {event.details}")


============================================================================
VALIDATION CHECKS (FAIL-CLOSED)
============================================================================

✓ PASSED:
  ✓ ExecutionRequest has all required fields
  ✓ PlanDraft structure intact (not altered)
  ✓ Current security state is readable
  ✓ Current state is not LOCKDOWN
  ✓ Security snapshots exist
  ✓ Execution context is dict

✗ REJECTED:
  ✗ Missing execution_id
  ✗ Missing plan_draft
  ✗ Plan altered (missing derived_steps)
  ✗ Security state unknown
  ✗ LOCKDOWN prevents execution
  ✗ State degraded since approval
  ✗ No security snapshots


============================================================================
ONE-SHOT GUARANTEE
============================================================================

Lifecycle:
  OneShot created
    ↓
  can_execute() → True
    ↓
  mark_executing() (state = EXECUTING)
    ↓
  mark_executed() (state = EXECUTED)
    ↓
  can_execute() → False
    ↓
  Second call → RuntimeError


Second Attempt → RuntimeError:
  try:
      one_shot.mark_executing()  # Already EXECUTED
  except RuntimeError:
      print("Already executed!")


============================================================================
STAGE-4 TRANSLATION
============================================================================

Converts: ExecutionRequest + user_id + token_hash
Returns:  Stage-4 executable payload (dict)

Input:
  exec_request: ExecutionRequest
  user_id: "user-123"
  token_hash: "token-abc"

Output:
{
    "execution_id": "exec-123",
    "user_id": "user-123",
    "token_hash": "token-abc",
    "plan_intent": "Learn Python",
    "plan_draft_id": "plan-001",
    "approval_timestamp": "2026-01-29T...",
    "approver_identity": "admin",
    "trigger_type": "manual",
    "steps": [
        {
            "sequence": 1,
            "faculty": "read_knowledge",
            "action": "Query knowledge base",
            "parameters": {...},
            "required_capabilities": [...],
            "estimated_duration_sec": 5.0,
            "notes": ""
        },
        ...
    ],
    "required_faculties": [...],
    "required_capabilities": [...],
    "estimated_risk_level": "low",
    "security_snapshot_at_approval": {...},
    "assumptions": [...],
    "known_unknowns": [...],
    "translation_timestamp": "..."
}


============================================================================
AUDIT TRAIL
============================================================================

Event Types:
  validation_passed       → Handshake validation succeeded
  validation_failed       → Validation failed (with reason)
  translation_completed  → Translation succeeded (step count)
  translation_failed     → Translation failed (with reason)
  execution_started      → Execution began
  execution_completed    → Execution succeeded
  execution_failed       → Execution failed (with error)
  execution_rejected     → Rejected (one-shot violated)
  one_shot_completed     → OneShot lifecycle complete
  execution_error        → Unexpected error

Query Audit Trail:
  # All events
  events = executor.get_audit_trail()

  # Events for specific execution
  events = executor.get_audit_trail("exec-123")

  # Each event has:
  # - timestamp: ISO 8601
  # - execution_id: which execution
  # - event_type: type
  # - details: event data
  # - error_message: error (if applicable)


============================================================================
ERROR HANDLING
============================================================================

Synchronous Execution:
  success, message, result = executor.execute(...)
  
  if success:
      # Execution completed (result dict available)
      process_result(result)
  else:
      # Execution failed or rejected
      log_error(message)
      reject()


Return Signature:
  (bool, str, dict)
  - bool: success/failure
  - str: message (reason if failed)
  - dict: results (empty if failed)


Common Failure Messages:
  "ExecutionRequest missing execution_id"
  "Plan is missing derived_steps (altered?)"
  "Current security state is unknown"
  "Execution blocked: system in LOCKDOWN"
  "Execution exec-123 already executed"
  "Translation failed: ..."
  "Stage-4 execution failed: ..."


============================================================================
CONSTRAINTS ENFORCED
============================================================================

✓ No Autonomy
  Executor never decides to execute
  Caller decides, executor validates

✓ No Background Execution
  execute() is synchronous (blocking)
  Caller waits for result

✓ No Retries
  Single-pass validation
  Fail on first error

✓ No Partial Execution
  OneShot ensures all-or-nothing
  Either EXECUTED or failed

✓ No Mutation
  PlanDraft frozen (already immutable)
  ExecutionRequest frozen (not mutable)

✓ Standard Library Only
  dataclasses, datetime, enum, typing

✓ Fail-Closed
  Lockdown blocks
  Validation rejects on doubt
  OneShot prevents re-execution


============================================================================
INTEGRATION
============================================================================

With PlanCompiler:
  ✓ ExecutionRequest holds PlanDraft reference
  ✓ No copy, no mutation

With Approval Gateway:
  ✓ Produces ApprovalRequest
  ✓ ExecutionRequest captures it

With Artemis Security:
  ✓ Handshake validates security state
  ✓ LOCKDOWN blocks execution

With Stage-4 Orchestrator:
  ✓ ApprovalExecutor dispatches
  ✓ Returns Stage-4 results


============================================================================
EXAMPLES
============================================================================

See: examples/approval_executor_example.py

- Example 1: Successful handshake
- Example 2: One-shot guarantee
- Example 3: Failed validation
- Example 4: LOCKDOWN blocks
- Example 5: Full executor flow
- Example 6: Audit trail


============================================================================
KEY PRINCIPLE
============================================================================

# Authority transfer point
# One-shot execution
# No retries
# Fail-closed

This boundary is CRITICAL:
- No autonomy allowed
- Validation must be explicit
- Execution must be audited
- State must be immutable
- Failure must be fail-closed
"""
