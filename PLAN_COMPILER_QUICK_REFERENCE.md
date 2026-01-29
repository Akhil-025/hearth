"""
PLAN COMPILER - QUICK REFERENCE

# LLM reasoning → plan
# No execution authority
# No autonomy
# Fail-closed

============================================================================
AT A GLANCE
============================================================================

PURPOSE:      Convert Hestia LLM reasoning → strict executable plans
OUTPUT:       PlanDraft (immutable dataclass)
NO:           Execution, approval, retries, mutations, background tasks
CONSTRAINTS:  Standard library only, deterministic, fail-closed


============================================================================
STEP FORMAT (LLM MUST USE)
============================================================================

    STEP 1:
    FACULTY: READ_KNOWLEDGE
    ACTION: Query knowledge base for Python decorators
    PARAMETERS: {"search_term": "python decorators"}
    CAPABILITIES: KNOWLEDGE_READ

Rules:
- Sequential STEP numbers (1, 2, 3, ...)
- Each step has FACULTY, ACTION, PARAMETERS, CAPABILITIES
- ACTION cannot contain: if, maybe, try, retry, loop, while, for, attempt
- CAPABILITIES is comma-separated list: KNOWLEDGE_READ, ANALYSIS, etc.


============================================================================
USAGE (FROM HESTIA)
============================================================================

    compiler = PlanCompiler(kernel=kernel_ref)
    
    plan, message = compiler.compile(
        intent="Learn Python decorators",
        llm_output=raw_llm_text,
        security_summary=snapshot,
        draft_id="unique-id"
    )
    
    if plan:
        # Success: plan is immutable PlanDraft
        for step in plan.derived_steps:
            print(step.action)
        
        # Export as dict
        plan_dict = plan.to_dict()
    else:
        # Failure: message explains why
        print(f"Failed: {message}")


============================================================================
VALIDATIONS (FAIL-CLOSED)
============================================================================

✗ REJECTED:
  - Missing STEP markers
  - Missing FACULTY/ACTION/CAPABILITIES
  - Conditional keywords in action (if, maybe, try, ...)
  - Unknown faculty names
  - Unknown capability names
  - Non-sequential step numbers
  - Non-JSON-serializable parameters

✓ ACCEPTED:
  - Explicit, deterministic actions
  - Known faculty names
  - Known capability names
  - JSON-serializable parameters


============================================================================
DATA STRUCTURES
============================================================================

PlanStep (frozen):
  - sequence: int (1, 2, 3, ...)
  - faculty: Faculty enum (READ_KNOWLEDGE, ANALYZE_CODE, etc.)
  - action: str (explicit description)
  - parameters: dict (JSON-serializable)
  - required_capabilities: frozenset (KNOWLEDGE_READ, ANALYSIS, etc.)
  - estimated_duration_sec: float? (optional)
  - notes: str (optional)

PlanDraft (frozen):
  - draft_id: str
  - intent: str
  - derived_steps: tuple[PlanStep] (immutable)
  - required_faculties: frozenset[Faculty]
  - required_capabilities: frozenset[str]
  - estimated_risk_level: "low"|"medium"|"high"|"unknown"
  - required_approvals: frozenset[str]
  - security_summary_snapshot: dict (Artemis state at compile time)
  - assumptions: tuple[str]
  - known_unknowns: tuple[str]
  - timestamp: str (ISO 8601)


============================================================================
FACULTY OPTIONS
============================================================================

READ_KNOWLEDGE        Query knowledge store
READ_MEMORY          Query memory
ANALYZE_CODE         Hephaestus reasoning
ANALYZE_HABITS       Apollo reasoning
ANALYZE_TONE         Hermes reasoning
RECOMMEND_MUSIC      Dionysus reasoning
PLAN_SCHEDULE        Hermes scheduling

WRITE faculties: FORBIDDEN in draft phase


============================================================================
CAPABILITY OPTIONS
============================================================================

READ_ONLY             General read access
KNOWLEDGE_READ        Knowledge store access
MEMORY_READ           Memory access
ANALYSIS              Analysis capability

All WRITE capabilities: FORBIDDEN in draft phase


============================================================================
ERROR HANDLING
============================================================================

    try:
        plan = compiler.compile(...)
    except StepParseError as e:
        # Parsing failed: missing markers, invalid JSON, etc.
        print(f"Parse error: {e}")
    except ValidationError as e:
        # Validation failed: forbidden keywords, unknown faculty, etc.
        print(f"Validation error: {e}")


============================================================================
IMMUTABILITY
============================================================================

PlanDraft is frozen: all fields immutable

    plan.intent = "HACKED"          # ✗ AttributeError
    plan.derived_steps[0] = new_step # ✗ TypeError
    plan.required_faculties.add(...) # ✗ AttributeError

to_dict() returns a COPY:
    
    plan_dict = plan.to_dict()  # Can be modified safely
    plan_dict['intent'] = "..."  # Does not affect original plan


============================================================================
SECURITY
============================================================================

- Security snapshot captured at compile time (read-only inspection)
- Attached to PlanDraft for audit trail
- NOT used to gate compilation (all plans compile regardless of state)
- Compiler does NOT mutate Artemis state
- Compiler does NOT record to event trace


============================================================================
ASSUMPTIONS
============================================================================

All plans include explicit assumptions:
- User has read access to all knowledge sources
- User has read access to all memory types
- LLM outputs are deterministic given identical inputs

Review these before approving plans.


============================================================================
EXAMPLES
============================================================================

See: examples/plan_compiler_example.py

- Example 1: Successful plan (3 steps)
- Example 2: Rejected - missing FACULTY
- Example 3: Rejected - forbidden keyword (if)
- Example 4: Rejected - empty CAPABILITIES
- Example 5: Immutability demo
- Example 6: Security snapshot demo
- Example 7: JSON export demo


============================================================================
INTEGRATION
============================================================================

HestiaAgent has:

  compile_plan(intent, llm_output, draft_id=None)
    → (PlanDraft, str) | (None, str)

  get_plan_draft(plan)
    → Dict[str, Any] (JSON-serializable)


============================================================================
KEYWORDS (FORBIDDEN IN ACTIONS)
============================================================================

if              Conditional
maybe           Ambiguous
try             Retry semantic
retry           Explicit retry
loop            Unbounded loop
while           Unbounded loop
for             Loop
attempt         Retry semantic
request approval Implicit approval
wait for        Implicit condition
depends on      Implicit condition


============================================================================
NEXT STEPS AFTER COMPILATION
============================================================================

1. Review PlanDraft
   - Check steps make sense
   - Verify assumptions
   - Acknowledge known unknowns

2. Approve PlanDraft
   - Governance gates based on risk level, capabilities, state
   - (Implementation: artemis/approval.py)

3. Execute PlanDraft
   - (Future: execution engine routes steps to faculties)


============================================================================
FAIL-CLOSED PRINCIPLE
============================================================================

Compiler rejects anything it cannot explicitly understand:

- Missing markers? Reject.
- Ambiguous action? Reject.
- Unknown faculty? Reject.
- Forbidden keyword? Reject.
- Invalid parameters? Reject.
- Non-sequential steps? Reject.

When in doubt: fail-closed.
"""
