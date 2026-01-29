"""
PLAN COMPILER SPECIFICATION

# LLM reasoning → plan
# No execution authority
# No autonomy
# Fail-closed

============================================================================
OVERVIEW
============================================================================

The PLAN COMPILER converts Hestia (LLM) reasoning into STRICT, EXECUTABLE PLANS
that can later be approved and executed.

CORE CONSTRAINT: No execution, no approval, no mutation of system state.

OUTPUT: PlanDraft (immutable, auditable, deterministic)


============================================================================
ARCHITECTURE
============================================================================

+------------------+
| Hestia LLM       |  Generates raw text with step markers
+------------------+
        ↓
+------------------+
| PlanParser       |  Parses raw text → step dicts
+------------------+        Fails on ambiguous/underspecified steps
        ↓
+------------------+
| Validation       |  Rejects forbidden keywords, undefined capabilities
+------------------+        Rejects non-explicit conditionals
        ↓
+------------------+
| Step Normalization | Converts dicts → immutable PlanStep objects
+------------------+        Validates each step independently
        ↓
+------------------+
| PlanDraft       |  Frozen dataclass: immutable, auditable
+------------------+        Security snapshot attached (inspection, no mutation)


============================================================================
CONSTRAINTS
============================================================================

1. NO EXECUTION
   - Plans are pure data structures (no side effects)
   - No code execution during compilation

2. NO APPROVAL
   - Compiler produces drafts only
   - No capability gates
   - Approval happens at a later stage

3. NO RETRIES
   - Single pass: parse → validate → compile
   - Fail on first error (fail-closed)

4. NO BACKGROUND ACTIVITY
   - Synchronous operation
   - No async, no background tasks
   - No resource consumption

5. NO MUTATION OF SYSTEM STATE
   - Artemis state untouched
   - Security summary is SNAPSHOT only (inspection, read-only)
   - No logging (append-only event trace not used)

6. STANDARD LIBRARY ONLY
   - No external dependencies
   - json, dataclasses, enum, uuid only

7. DETERMINISTIC OUTPUT
   - Identical inputs → identical outputs
   - No randomness, no ordering variations


============================================================================
DATA STRUCTURES
============================================================================

Faculty (Enum)
--------------
READ_KNOWLEDGE       # Query knowledge store
READ_MEMORY         # Query memory
ANALYZE_CODE        # Hephaestus reasoning
ANALYZE_HABITS      # Apollo reasoning
ANALYZE_TONE        # Hermes reasoning
RECOMMEND_MUSIC     # Dionysus reasoning
PLAN_SCHEDULE       # Hermes scheduling

WRITE faculties FORBIDDEN in draft phase.


CapabilityType (Enum)
---------------------
READ_ONLY           # General read access
KNOWLEDGE_READ      # Knowledge store access
MEMORY_READ         # Memory access
ANALYSIS            # Analysis capability

All WRITE capabilities FORBIDDEN in draft phase.


PlanStep (frozen dataclass)
---------------------------
@dataclass(frozen=True)
class PlanStep:
    sequence: int                          # 1-based order
    faculty: Faculty                       # Single faculty only
    action: str                            # Explicit verb+noun
    parameters: Dict[str, Any]             # Input parameters
    required_capabilities: FrozenSet[str]  # Capabilities needed
    estimated_duration_sec: Optional[float] = None
    notes: str = ""

Constraints:
- action must be explicit (no ambiguity)
- action must not contain forbidden keywords (if, maybe, try, retry, etc.)
- required_capabilities must not be empty
- parameters must be JSON-serializable


PlanDraft (frozen dataclass)
----------------------------
@dataclass(frozen=True)
class PlanDraft:
    draft_id: str                                      # Unique ID
    intent: str                                        # Original user intent
    derived_steps: Tuple[PlanStep, ...]               # Ordered steps
    required_faculties: FrozenSet[Faculty]            # Faculties needed
    required_capabilities: FrozenSet[str]             # Capabilities needed
    estimated_risk_level: str                         # low|medium|high|unknown
    required_approvals: FrozenSet[str]                # Approval types needed
    security_summary_snapshot: Dict[str, Any]         # Artemis state at compile time
    assumptions: Tuple[str, ...]                      # Explicit assumptions
    known_unknowns: Tuple[str, ...]                   # Known gaps
    timestamp: str                                    # ISO 8601 compile timestamp
    compiler_version: str = "1.0"                     # Plan format version

All fields are immutable (frozen=True).
All tuple/frozenset fields prevent mutation.


============================================================================
LLM OUTPUT FORMAT
============================================================================

Hestia must output steps using explicit markers:

    STEP 1:
    FACULTY: READ_KNOWLEDGE
    ACTION: Query knowledge base for Python decorators
    PARAMETERS: {"search_term": "python decorators", "limit": 5}
    CAPABILITIES: KNOWLEDGE_READ

    STEP 2:
    FACULTY: ANALYZE_CODE
    ACTION: Analyze decorator patterns in retrieved code
    PARAMETERS: {"focus": "syntax"}
    CAPABILITIES: ANALYSIS

Markers (case-insensitive):
- STEP <number>:      Step header
- FACULTY:            Faculty name
- ACTION:             Action description
- PARAMETERS:         JSON dict (optional, defaults to {})
- CAPABILITIES:       Comma-separated capability list

Parser rejects:
- Missing STEP markers
- Missing FACULTY marker
- Missing or empty ACTION
- Missing or empty CAPABILITIES
- Steps without required markers


============================================================================
VALIDATION RULES
============================================================================

1. Step Sequences
   ✓ Must be consecutive: 1, 2, 3, ... N
   ✗ Reject: 1, 3, 5 or 0, 1, 2

2. Faculty Names
   ✓ Must match Faculty enum (case-insensitive)
   ✓ READ_KNOWLEDGE, ANALYZE_CODE, PLAN_SCHEDULE, etc.
   ✗ Reject: UNKNOWN_FACULTY, "create_file"

3. Action Text
   ✓ Explicit verb+noun: "Query knowledge base", "Analyze patterns"
   ✗ Reject: "do stuff", "maybe analyze"
   ✗ Reject: Actions containing keywords:
      - if, maybe, try, retry, loop, while, for, attempt
      - request approval, wait for, depends on

4. Capabilities
   ✓ Must be non-empty list
   ✓ Each must match CapabilityType enum
   ✗ Reject: empty list, unknown capability names

5. Parameters
   ✓ Must be JSON-serializable
   ✗ Reject: non-serializable objects (functions, threads, etc.)


============================================================================
FAIL-CLOSED BEHAVIOR
============================================================================

Compiler fails-closed on any ambiguity:

1. Parse Errors
   - Missing marker → StepParseError (fail-closed)
   - Invalid JSON → StepParseError (fail-closed)
   - Malformed steps → StepParseError (fail-closed)

2. Validation Errors
   - Forbidden keyword in action → ValidationError (fail-closed)
   - Unknown faculty/capability → ValidationError (fail-closed)
   - Non-consecutive steps → ValidationError (fail-closed)

3. Unexpected Errors
   - All exceptions propagate as compilation failures
   - No silent fallbacks or defaults

Usage:
    try:
        plan = compiler.compile(...)
    except (StepParseError, ValidationError) as e:
        # Compilation failed: plan is None
        return None, str(e)


============================================================================
INTEGRATION WITH HESTIA
============================================================================

HestiaAgent.compile_plan(intent, llm_output, draft_id=None)
-------------------------------------------------------------

Arguments:
    intent: str           # User's original intent
    llm_output: str       # Raw LLM text with step markers
    draft_id: str?        # Optional draft ID (auto-generated if None)

Returns:
    (PlanDraft | None, str)
    - PlanDraft: Successfully compiled (immutable)
    - None: Compilation failed
    - str: Message (success or error explanation)

Example:
    plan, message = agent.compile_plan(
        intent="Learn Python decorators",
        llm_output=llm_output,
        draft_id="session-123-plan-001"
    )
    
    if plan:
        print(f"Plan has {plan.step_count()} steps")
        for step in plan.derived_steps:
            print(f"  {step.action}")
    else:
        print(f"Compilation failed: {message}")


HestiaAgent.get_plan_draft(plan)
--------------------------------

Export PlanDraft as JSON-serializable dict.

Returns:
    Dict[str, Any] with all plan information
    - JSON-serializable (safe for persistence)
    - Immutable (external copies don't affect original)


============================================================================
SECURITY AWARENESS
============================================================================

1. Security Snapshot
   - Current Artemis state captured at compile time (read-only inspection)
   - Attached to PlanDraft for audit trail
   - NOT used to gate plan compilation

2. No Mutation
   - Compiler does NOT escalate Artemis state
   - Compiler does NOT downgrade Artemis state
   - Compiler does NOT record to event trace
   - Compiler does NOT modify credentials

3. Read-Only Inspection
   - If kernel is available, inspect current state
   - If inspection fails, use empty snapshot
   - Fail-closed: empty snapshot never causes compilation failure


============================================================================
ASSUMPTIONS & UNKNOWNS
============================================================================

All plans include explicit assumptions and known unknowns.

Assumptions (examples):
- "User has read access to all knowledge sources referenced in steps"
- "User has read access to all memory types referenced in steps"
- "LLM outputs are deterministic given identical inputs"

Known Unknowns (examples):
- "Exact time required for each step (estimates only)"
- "Availability of knowledge sources (assumed available)"
- "Memory structure and completeness (assumed valid)"

Users should review these before approving plans.


============================================================================
RISK ESTIMATION
============================================================================

Simple heuristic (can be enhanced):

Low:     Only READ_KNOWLEDGE + READ_MEMORY faculties
Medium:  Any analysis faculties (ANALYZE_CODE, ANALYZE_HABITS, ANALYZE_TONE)
High:    (Reserved for future multi-resource plans)
Unknown: Other combinations


============================================================================
IMPLEMENTATION DETAILS
============================================================================

Fail-Closed Pattern
-------------------
def compile(intent, llm_output, security_summary, draft_id):
    try:
        parsed_steps = PlanParser.parse_steps(llm_output)  # May raise StepParseError
        validate_draft(parsed_steps)                        # May raise ValidationError
        steps = [PlanStep(...) for parsed in parsed_steps]  # May raise ValueError
        # Build PlanDraft
    except (StepParseError, ValidationError, ValueError):
        raise  # Caller handles exception

Immutability
------------
- All dataclasses use frozen=True
- All collections are tuple or frozenset
- to_dict() returns copy (safe for external modification)
- External modifications don't affect original PlanDraft

Determinism
-----------
- No randomness in parsing, validation, or normalization
- No time-dependent behavior (timestamp only for audit)
- Identical LLM output always produces identical PlanDraft
  (given same draft_id and security snapshot)


============================================================================
EXAMPLES
============================================================================

See: examples/plan_compiler_example.py

- Example 1: Successful compilation
- Example 2: Fail-closed on missing FACULTY
- Example 3: Fail-closed on forbidden conditional
- Example 4: Fail-closed on ambiguous step
- Example 5: Immutability verification
- Example 6: Security snapshot capture
- Example 7: JSON export


============================================================================
FORBIDDEN CONSTRUCTS
============================================================================

Plan actions MUST NOT contain:

1. Conditionals
   - "if", "maybe", "try"
   → These require runtime decision-making (not pre-approved)

2. Loops
   - "loop", "while", "for", "repeatedly"
   → These require unbounded execution (unknown cost)

3. Retries
   - "retry", "attempt", "repeat on failure"
   → These require fallback logic (not explicit)

4. Implicit Approvals
   - "request approval", "ask for permission"
   → Approvals happen after compilation, not during step execution

5. Implicit Conditionals
   - "wait for", "depends on", "only if"
   → These encode runtime decisions in step description


============================================================================
FUTURE EXTENSIONS
============================================================================

1. Approval Gateway
   Compile → Approve → Execute
   Approval logic gates plan based on risk level, required capabilities, etc.

2. Capability Binding
   Match required capabilities to available resources
   Verify user has authority for each capability

3. Resource Costing
   Estimate time, memory, network, etc. for each step
   Aggregate total cost

4. Plan Optimization
   Reorder steps for efficiency (with dependency analysis)
   Suggest merged steps where appropriate

5. Execution Engine
   Iterate through steps, dispatch to appropriate faculty
   Record execution trace

6. Memory Proposals
   Steps can propose memory saves for future context
   User confirms before save


============================================================================
KEYWORDS
============================================================================

# LLM reasoning → plan
# No execution authority
# No autonomy
# Fail-closed

These comments appear at every compiler boundary to reinforce constraints.
"""
