# HESTIA UI LAYER SPECIFICATION

## Overview

The Hestia UI Layer exposes the Think → Propose → Approve → Execute → Stop loop to humans in a clear, inspectable way.

**Core Principle:**
```
# UX only
# No authority
# No execution
# No autonomy
```

This layer has **ZERO** execution authority. It only:
- Presents plans to humans
- Requests approval (doesn't decide)
- Displays boundaries (doesn't override)
- Records decisions (doesn't enact them)

## Architecture

### Immutable Data Structures

#### `StepPresentation`
Human-readable representation of a single plan step.

```python
@dataclass(frozen=True)
class StepPresentation:
    sequence: int                       # Step number
    description: str                   # Human-readable action
    faculty: str                       # Which capability (knowledge_retrieval, code_execute, etc.)
    data_accessed: List[str]           # What data touched
    capabilities_required: List[str]   # Permissions needed
    estimated_duration_sec: Optional[float]
    irreversible: bool                 # Does this change state?
```

#### `PlanPresentation`
Complete, human-readable plan suitable for approval decision.

```python
@dataclass(frozen=True)
class PlanPresentation:
    plan_id: str                       # Reference to original PlanDraft
    user_intent: str                  # What user asked for
    summary: str                      # One-line summary
    steps: Tuple[StepPresentation, ...]
    faculties_involved: Tuple[str, ...]
    data_sources_accessed: Tuple[str, ...]
    capabilities_required: Tuple[str, ...]
    estimated_total_duration_sec: Optional[float]
    estimated_risk_level: str         # low | medium | high | unknown
    security_posture_snapshot: Dict[str, Any]  # Artemis state at presentation time
    irreversible_actions: Tuple[str, ...]
    assumptions: Tuple[str, ...]
    presentation_timestamp: str       # ISO 8601
```

#### `ApprovalDecision`
Immutable record of user's approval decision.

```python
@dataclass(frozen=True)
class ApprovalDecision:
    decision_id: str                  # Unique ID
    plan_id: str                     # Which plan
    approved: bool                   # YES or NO
    approver_identity: str           # Who decided
    timestamp: str                   # ISO 8601
    reason: str                      # Why they decided
    security_state_at_decision: Dict[str, Any]
```

### UI Methods

All methods in the UI layer are **presentation-only**. None have execution or approval authority.

#### `HestiaUIBoundary.present_plan(plan_draft) → PlanPresentation`

Convert a PlanDraft into human-readable form.

```python
plan_pres = HestiaUIBoundary.present_plan(plan_draft)
# Now human can inspect:
# - What will happen (steps)
# - What data will be touched
# - What permissions are needed
# - What risks exist
# - What actions are irreversible
```

**Constraints:**
- Pure conversion (no decisions)
- No execution authority
- No modification of original plan_draft
- Read-only inspection only

#### `HestiaUIBoundary.request_approval_from_user(plan_presentation) → Tuple[bool, str]`

Prompt user for approval decision.

```python
approved, reason = HestiaUIBoundary.request_approval_from_user(plan_pres)
# approved: bool (True if user says YES)
# reason: str (user's explanation)
```

**Constraints:**
- No auto-approval
- No default approval
- Explicit YES or NO required
- Records user's actual response

#### `HestiaUIBoundary.explain_rejection(reason: str) → str`

Build human-readable rejection explanation.

```python
explanation = HestiaUIBoundary.explain_rejection("System is in LOCKDOWN")
# Explains why plan was rejected in plain English
```

**Constraints:**
- Factual (no minimization or alarmism)
- Clear (no jargon)
- Actionable (explains what user can do)

#### `HestiaUIBoundary.display_authority_constraints() → str`

Show what Hestia can and cannot do.

```python
boundaries = HestiaUIBoundary.display_authority_constraints()
# Factual description of Hestia's boundaries
```

### Approval Prompt Builder

#### `ApprovalPromptBuilder.build_prompt(plan_pres, security_summary) → str`

Generate a factual approval prompt.

**Design principles:**
- **Factual**: No persuasion, no minimization, no alarmism
- **Complete**: All information needed for decision
- **Clear**: Plain English, no jargon
- **Neutral**: No opinions, no preferences
- **Explicit**: Risks, assumptions, irreversible actions clearly marked

**Output includes:**
- Current security state
- What will happen (steps)
- Data that will be accessed
- Permissions needed
- Duration estimate
- Assumptions (must be true for plan to work)
- Irreversible actions (marked with ⚠)
- Risk level assessment

Example:
```
PLAN: Retrieve recent notes from Knowledge Store
User Intent: Show me my recent notes

Current Security State: SECURE
  Reason: All systems normal

Risk Level: low

WHAT THIS PLAN WILL DO:
  1. Query Knowledge Store for recent notes

DATA THAT WILL BE ACCESSED: Knowledge Store

PERMISSIONS NEEDED: read:knowledge

ASSUMPTIONS (must be true for this plan to work):
  • Knowledge Store is available
  • You have recent notes stored

Do you want to approve this plan?
  Type: YES or NO
```

### Authority Flow Validator

Verify that Hestia respects its boundaries.

```python
class AuthorityFlowValidator:
    
    @staticmethod
    def ensure_no_execution_authority(hestia) → None:
        """Verify Hestia cannot execute"""
        
    @staticmethod
    def ensure_no_approval_authority(hestia) → None:
        """Verify Hestia cannot approve"""
        
    @staticmethod
    def ensure_no_retry_logic(hestia) → None:
        """Verify Hestia cannot retry"""
        
    @staticmethod
    def ensure_no_plan_mutation(plan_draft) → Tuple[bool, str]:
        """Verify plan is immutable"""
```

## Integration with HestiaAgent

Three new methods added to `HestiaAgent`:

### `present_plan(plan_draft) → PlanPresentation`

```python
agent = HestiaAgent()
plan_draft = agent.compile_plan(intent, llm_output)
presentation = agent.present_plan(plan_draft)  # Human-readable
```

### `request_approval(plan_draft) → Tuple[bool, str]`

```python
approved, reason = agent.request_approval(plan_draft)
if approved:
    # User approved — can now proceed to execution
    # (Execution is done via ApprovalExecutor, NOT by Hestia)
else:
    # User rejected — explain why
    explanation = agent.explain_rejection(reason)
```

### `explain_rejection(reason) → str`

```python
explanation = agent.explain_rejection("Plan requires write:memory capability")
print(explanation)
```

### `display_authority_boundaries() → str`

```python
boundaries = agent.display_authority_boundaries()
print(boundaries)
# Shows what Hestia can and cannot do
```

## Mandatory Comments

Every boundary crossing requires comments:

```python
# UX only
# No authority
# No execution
# No autonomy
```

These appear at:
- Class definitions
- Method definitions
- Boundary points
- Authority transitions

## Data Flow

```
User Request
    ↓
Hestia.compile_plan()
    ↓ (# LLM reasoning → plan)
PlanDraft (immutable, no execution authority)
    ↓
Hestia.present_plan()
    ↓ (# UX only)
PlanPresentation (human-readable, inspectable)
    ↓
Display to user
    ↓
Hestia.request_approval()
    ↓ (# UX only, no authority)
User approval decision
    ↓
ApprovalDecision (immutable record)
    ↓
[At this point, execution happens via ApprovalExecutor, NOT Hestia]
    ↓
ApprovalRequest → ExecutionRequest → Stage4 execution
```

**Key Point:** Hestia's role ends after `request_approval()`. Execution happens elsewhere (ApprovalExecutor → Stage4).

## Security Properties

### 1. No Execution Authority
```python
# Hestia CAN:
- Reason (think)
- Compile plans
- Present plans
- Request approval

# Hestia CANNOT:
- Execute
- Approve
- Retry
- Modify plans
```

### 2. Immutability
All data structures are frozen dataclasses:
```python
@dataclass(frozen=True)  # Cannot be modified
class PlanPresentation:
    ...
```

Attempts to mutate raise `FrozenInstanceError`.

### 3. Fail-Closed
Ambiguities default to "no execution":
- Unrecognized risk level → presented as "unknown"
- Missing data → presented as "unknown"
- Malformed assumptions → listed as-is for user inspection

### 4. One-Way Flow
```
compile_plan() → present_plan() → request_approval() → [STOP]
```

No backward loops, no retries, no modifications.

### 5. Explicit Authorization
Every approval requires:
- Explicit user action (YES or NO)
- No defaults
- No auto-approval
- No silent retries

## Usage Patterns

### Pattern 1: Simple Approval Flow

```python
from hestia.agent import HestiaAgent

agent = HestiaAgent()

# 1. Compile user intent into plan
plan_draft, msg = agent.compile_plan(
    intent="Analyze my activity from last week",
    llm_output="..."  # From LLM reasoning
)

if not plan_draft:
    print(f"Failed: {msg}")
    exit()

# 2. Present plan to user
presentation = agent.present_plan(plan_draft)
print(presentation.to_human_text())

# 3. Request approval
approved, reason = agent.request_approval(plan_draft)

if approved:
    print("Plan approved by user")
    # Next: ExecutionRequest → ApprovalExecutor
else:
    explanation = agent.explain_rejection(reason)
    print(explanation)
```

### Pattern 2: Authority Verification

```python
from hestia.ui_layer import AuthorityFlowValidator

# Verify Hestia's constraints
AuthorityFlowValidator.ensure_no_execution_authority(agent)
AuthorityFlowValidator.ensure_no_approval_authority(agent)
AuthorityFlowValidator.ensure_no_retry_logic(agent)

# Verify plan immutability
is_immutable, reason = AuthorityFlowValidator.ensure_no_plan_mutation(plan_draft)
assert is_immutable, f"Plan mutability issue: {reason}"
```

### Pattern 3: Manual Approval Prompt

```python
from hestia.ui_layer import PlanPresentation, ApprovalPromptBuilder

# Create custom presentation
presentation = PlanPresentation(...)

# Build approval prompt
security_state = {"state": "SECURE"}
prompt = ApprovalPromptBuilder.build_prompt(presentation, security_state)
print(prompt)

# Get user input
user_input = input("Approve? (YES/NO): ")
approved = user_input.upper() == "YES"
```

## Constraints

### 1. No External Dependencies
- Standard library only
- No imports outside Python stdlib
- No external packages

### 2. No Async Operations
- All methods are synchronous
- All I/O is blocking
- No background execution

### 3. No State Mutation
- All inputs are preserved
- All outputs are frozen
- No side effects

### 4. No Silent Failures
- All ambiguities are explicit
- All errors are reported
- No default assumptions

## Error Handling

### No Exceptions During Approval Flow

The UI layer does not raise exceptions. Instead, it returns:
- `(False, "reason")` for rejections
- Human-readable strings for explanations
- Explicit "unknown" for ambiguous values

### Fail-Closed Defaults

When data is ambiguous:
- Risk level: "unknown"
- Duration: None
- Data sources: inferred from faculties
- Capabilities: listed from plan

## Testing

See `examples/hestia_ui_layer_example.py` for 8 working examples:

1. Simple plan presentation
2. High-risk plan with irreversible actions
3. Factual approval prompt
4. Rejection explanation
5. Authority boundaries
6. Authority validation
7. Plan immutability
8. Approval decision record

## Next Phase

After user approves:
1. Create `ApprovalRequest` (approval boundary)
2. Send to `ApprovalExecutor` (execution boundary)
3. Create `ExecutionRequest` (authority transfer)
4. Execute via Stage4 (actual execution)

**Note:** Hestia is NOT involved in steps 2-4. Those are handled by separate, isolated components.

## Summary

The Hestia UI Layer provides:
- ✅ Human-readable plan presentations
- ✅ Factual, non-persuasive approval prompts
- ✅ Clear authority boundaries
- ✅ Immutable records of decisions
- ✅ No execution authority
- ✅ No approval authority
- ✅ No retry logic
- ✅ No plan mutation

Every user-facing surface is:
- **Inspectable**: All information visible
- **Factual**: No persuasion or alarmism
- **Immutable**: Cannot be altered
- **Explicit**: No hidden defaults
- **Fail-closed**: Ambiguities default to "no"

The user makes all decisions. Hestia just helps them understand what will happen.
