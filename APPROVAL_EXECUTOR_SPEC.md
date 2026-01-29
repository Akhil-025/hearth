"""
APPROVAL → EXECUTION HANDSHAKE SPECIFICATION

# Authority transfer point
# One-shot execution
# No retries
# Fail-closed

============================================================================
OVERVIEW
============================================================================

The APPROVAL → EXECUTION HANDSHAKE is the critical boundary between
GOVERNANCE (where plans are approved) and EXECUTION (where plans run).

This handshake ensures:
1. Authority transfer is explicit and audited
2. Execution happens exactly once (one-shot guarantee)
3. All validation is fail-closed (reject on any doubt)
4. Audit trail is immutable and comprehensive
5. PlanDraft is never mutated during approval/execution


============================================================================
ARCHITECTURE
============================================================================

Approval Flow:
  PlanDraft (compiled)
    ↓
  Approval Gateway (governance layer - separate)
    ↓
  ApprovalRequest (approved)
    ↓

Execution Flow:
  ExecutionRequest (immutable)
    ↓ (Authority Transfer)
  HandshakeValidator
    ↓ (Validation: fail-closed)
  Stage4Translator
    ↓ (Exact translation, no inference)
  OneShot Wrapper
    ↓ (One-shot guarantee)
  Stage-4 Dispatcher
    ↓
  ExecutionAuditTrail (append-only record)


============================================================================
DATA STRUCTURES
============================================================================

ExecutionRequest (frozen dataclass)
-----------------------------------
@dataclass(frozen=True)
class ExecutionRequest:
    execution_id: str                       # Unique execution ID
    plan_draft: Any                         # Reference to PlanDraft
    approval_request: Any                   # Approved ApprovalRequest
    approval_timestamp: str                 # ISO 8601 approval time
    approver_identity: str                  # Who approved
    security_summary_snapshot: Dict         # Artemis state at approval
    execution_context: Dict = {}            # User context (default empty)

Purpose:
  - Immutable record of authority transfer
  - References PlanDraft (no copy, immutable anyway)
  - Captures security state at approval time
  - Can only be created once (per execution)


ExecutionState (Enum)
---------------------
PENDING   → Never executed
EXECUTING → Execution in progress
EXECUTED  → Execution completed
FAILED    → Execution failed (blocked)

Transitions:
  PENDING → EXECUTING → EXECUTED
  PENDING → EXECUTING → FAILED
  (No backward transitions, no skipping)


OneShot (Wrapper)
-----------------
Enforces one-shot execution guarantee:
  - can_execute() → bool (true only if PENDING)
  - mark_executing() → void (PENDING → EXECUTING)
  - mark_executed() → void (EXECUTING → EXECUTED)
  - mark_failed(reason) → void (EXECUTING → FAILED)
  - get_state() → ExecutionState

Raises RuntimeError on state violations:
  - Second execution attempt
  - Marking executed before executing
  - Invalid state transitions


ExecutionAuditEvent (frozen dataclass)
--------------------------------------
@dataclass(frozen=True)
class ExecutionAuditEvent:
    timestamp: str                  # ISO 8601
    execution_id: str               # Which execution
    event_type: str                 # Event type
    details: Dict[str, Any]         # Event details
    error_message: Optional[str]    # Error (if applicable)

All fields immutable (frozen=True).


ExecutionAuditTrail (Append-Only)
---------------------------------
Immutable append-only audit trail:
  - record() → void (append event)
  - get_events() → Tuple[ExecutionAuditEvent] (immutable)
  - get_events_for_execution(id) → Tuple (filtered)

No mutation possible:
  - events stored in list (internal)
  - returned as immutable tuple
  - each event is frozen dataclass


============================================================================
HANDSHAKE VALIDATION
============================================================================

HandshakeValidator.validate() performs 7 checks (fail-closed):

1. ExecutionRequest Structure
   ✓ Has execution_id
   ✓ Has plan_draft (not None)
   ✓ Has approval_request (not None)
   ✓ Has approval_timestamp
   ✓ Has approver_identity

2. Plan Integrity
   ✓ derived_steps exists (not altered)
   ✓ required_faculties exists (not altered)
   ✓ required_capabilities exists (not altered)

3. Security State
   ✓ Current state is readable
   ✓ Current state is not "unknown"

4. Lockdown Check
   ✗ REJECT if current state is "LOCKDOWN"

5. Security Snapshots
   ✓ Either approval or plan snapshot exists
   ✓ Both cannot be missing

6. Snapshot Consistency
   ✓ If both snapshots exist, states should be comparable
   ✓ Fail if state degraded (e.g., DEGRADED → COMPROMISED)

7. Execution Context
   ✓ execution_context is dict (or empty dict)

Returns: (bool, reason_string)
  - True if all checks pass
  - False with explanation if any check fails


============================================================================
STAGE-4 TRANSLATION
============================================================================

Stage4Translator.translate() converts ExecutionRequest → Stage-4 payload.

Translation Rules:
  - Exact steps only (no inference)
  - No reordering (preserve sequence)
  - No enrichment (no defaults added)
  - No modification (PlanDraft immutable)

Input:
  ExecutionRequest (immutable)
  user_id (string)
  token_hash (string)

Output: Dict with Stage-4 executable payload:
{
    "execution_id": "...",
    "user_id": "...",
    "token_hash": "...",
    "plan_intent": "...",
    "plan_draft_id": "...",
    "approval_timestamp": "...",
    "approver_identity": "...",
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

Raises: Stage4TranslationError (fail-closed)


============================================================================
ONE-SHOT EXECUTION GUARANTEE
============================================================================

OneShot wrapper ensures execution happens exactly once:

Lifecycle:
  1. OneShot created (state = PENDING)
  2. can_execute() → True
  3. mark_executing() → state = EXECUTING
  4. mark_executed() → state = EXECUTED
  5. can_execute() → False
  6. Second call → RuntimeError

Benefits:
  - No accidental re-execution
  - No partial execution recovery
  - Clear state machine
  - Deterministic behavior

Guarantees:
  - If execution completes, state is EXECUTED
  - If execution starts, no second attempt possible
  - Each execution_id has at most one OneShot lifecycle


============================================================================
APPROVAL EXECUTOR
============================================================================

ApprovalExecutor.execute() orchestrates the handshake:

Flow:
  1. Check one-shot guarantee
  2. Validate handshake (fail-closed)
  3. Translate to Stage-4
  4. Mark as executing
  5. Dispatch to Stage-4 (if available)
  6. Mark as executed
  7. Record audit trail

Signature:
    execute(
        execution_request: ExecutionRequest,
        user_id: str,
        token_hash: str,
        current_security_state: Optional[Dict] = None
    ) → (bool, str, Dict)

Returns: (success, message, result)
  - success: bool - execution completed
  - message: str - explanation
  - result: dict - execution results or empty dict

Fail-Closed Behavior:
  ✗ One-shot already executed → False
  ✗ Validation fails → False (with reason)
  ✗ Translation fails → False (with reason)
  ✗ Stage-4 dispatch fails → False (with reason)


============================================================================
AUDIT TRAIL
============================================================================

ExecutionAuditTrail records immutable events:

Events (examples):
  - validation_passed
  - validation_failed (with reason)
  - translation_completed (with step count)
  - translation_failed
  - execution_started
  - execution_completed
  - execution_failed
  - one_shot_completed
  - execution_rejected (one-shot violated)
  - execution_error (unexpected)

Each event contains:
  - timestamp: ISO 8601
  - execution_id: which execution
  - event_type: type of event
  - details: event-specific data
  - error_message: error (if applicable)

Audit trail is:
  ✓ Append-only (no deletion)
  ✓ Immutable (events are frozen)
  ✓ Queryable (by execution_id)
  ✓ Non-repudiable (timestamp + events + approver)


============================================================================
CONSTRAINT ENFORCEMENT
============================================================================

1. NO AUTONOMY
   ✓ Executor never decides to execute (user decides)
   ✓ Executor only validates and translates
   ✓ Executor never modifies plans or policies

2. NO BACKGROUND EXECUTION
   ✓ execute() is synchronous (blocking)
   ✓ No async, no threads, no background tasks
   ✓ Caller waits for result

3. NO RETRIES
   ✓ Single-pass validation
   ✓ Fail on first error (fail-closed)
   ✓ No retry logic or recovery attempts
   ✓ OneShot prevents second attempt

4. NO PARTIAL EXECUTION
   ✓ OneShot ensures all-or-nothing
   ✓ Either EXECUTED or not executed
   ✓ No mid-execution resumption

5. NO MUTATION OF PLANDRAFT
   ✓ PlanDraft is frozen (already immutable)
   ✓ ExecutionRequest stores reference (not copy)
   ✓ No modification during approval/execution

6. STANDARD LIBRARY ONLY
   ✓ Imports: dataclasses, datetime, enum, typing
   ✓ No external dependencies
   ✓ Python 3.10+

7. FAIL-CLOSED ON EVERY BOUNDARY
   ✓ One-shot violated → RuntimeError
   ✓ Validation fails → False
   ✓ Translation fails → StepParseError
   ✓ Stage-4 dispatch fails → False
   ✓ Unexpected errors → False with message


============================================================================
ERROR HANDLING
============================================================================

Exception Types:
  - HandshakeValidationError: Validation failed (explicit)
  - Stage4TranslationError: Translation failed (explicit)
  - RuntimeError: OneShot violated (state machine)
  - ApprovalExecutionError: Execution failed (explicit)

Fail-Closed Pattern:
  try:
      result = executor.execute(request, user_id, token_hash)
  except RuntimeError as e:
      # OneShot violated
      log_error(e)
      reject_execution()
  except (HandshakeValidationError, Stage4TranslationError) as e:
      # Validation or translation failed
      log_error(e)
      reject_execution()

Returns always include reason:
  (False, "Validation failed: reason", {})
  (False, "Already executed", {})
  (True, "Execution completed successfully", result)


============================================================================
SECURITY PROPERTIES
============================================================================

Authority Transfer:
  - ApprovalRequest captures who approved
  - ExecutionRequest captures approver_identity
  - Audit trail links approval → execution
  - Non-repudiable (timestamp + approver + events)

Immutability:
  - ExecutionRequest is frozen dataclass
  - Events are frozen dataclasses
  - Audit trail returns tuples (immutable)
  - PlanDraft untouched (already frozen)

Fail-Closed:
  - LOCKDOWN blocks execution
  - Validation rejects on any uncertainty
  - OneShot prevents re-execution
  - No silent defaults or fallbacks

Auditability:
  - Every step recorded (validation, translation, execution)
  - Timestamp on every event
  - Error messages preserved
  - Execution ID links all events


============================================================================
INTEGRATION POINTS
============================================================================

1. PlanCompiler
   ExecutionRequest holds reference to PlanDraft
   No modification: PlanDraft remains frozen

2. Approval Gateway
   Produces ApprovalRequest
   ExecutionRequest captures it

3. Artemis Security Policy
   Handshake validator checks security state
   LOCKDOWN blocks execution

4. Stage-4 Orchestrator
   ApprovalExecutor dispatches to Stage4Orchestrator
   Returns Stage-4 results verbatim

5. Audit System
   Maintains immutable ExecutionAuditTrail
   Integrates with Artemis event trace (future)


============================================================================
EXAMPLES
============================================================================

See: examples/approval_executor_example.py

- Example 1: Successful handshake
- Example 2: One-shot guarantee enforcement
- Example 3: Failed validation (fail-closed)
- Example 4: LOCKDOWN blocks execution
- Example 5: Full ApprovalExecutor orchestration
- Example 6: Audit trail immutability


============================================================================
MANDATORY COMMENTS
============================================================================

At every boundary:

# Authority transfer point
# One-shot execution
# No retries
# Fail-closed

Appears in:
  ✓ artemis/approval_executor.py (module docstring)
  ✓ ExecutionRequest class
  ✓ HandshakeValidator class
  ✓ HandshakeValidator.validate()
  ✓ Stage4Translator class
  ✓ OneShot class
  ✓ ExecutionAuditEvent class
  ✓ ExecutionAuditTrail class
  ✓ ExecutionAuditTrail.record()
  ✓ ApprovalExecutor class
  ✓ ApprovalExecutor.execute()


============================================================================
NEXT PHASES
============================================================================

Phase 1: Execution Engine
  - Implement faculty dispatchers
  - Route steps to appropriate domain
  - Collect results

Phase 2: Result Aggregation
  - Combine domain results
  - Format for presentation
  - Handle partial failures

Phase 3: Memory Proposals
  - Steps can propose memory saves
  - User confirmation
  - Persistent storage

Phase 4: Long-Running Execution
  - Support batch plans
  - Background dispatch (with auditing)
  - Resume capability (future)
"""
