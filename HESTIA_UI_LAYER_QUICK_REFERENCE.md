# HESTIA UI LAYER - QUICK REFERENCE

## Core Rule
```
# UX only
# No authority
# No execution
# No autonomy
```

Hestia has **ZERO** execution authority. It only presents plans and requests approval.

## Quick Start

```python
from hestia.agent import HestiaAgent

agent = HestiaAgent()

# 1. Compile plan from LLM reasoning
plan_draft, msg = agent.compile_plan(intent, llm_output)

# 2. Present to user (human-readable)
presentation = agent.present_plan(plan_draft)
print(presentation.to_human_text())

# 3. Request approval (user decides)
approved, reason = agent.request_approval(plan_draft)

if approved:
    # Plan approved — send to ApprovalExecutor (NOT Hestia)
    pass
else:
    # Plan rejected — explain why
    explanation = agent.explain_rejection(reason)
    print(explanation)
```

## What Hestia Can Do

- ✅ Think (reason about problems)
- ✅ Compile plans (LLM → executable)
- ✅ Present plans (human-readable)
- ✅ Request approval (prompt user)
- ✅ Explain decisions (why rejected)

## What Hestia Cannot Do

- ❌ Execute plans
- ❌ Approve plans
- ❌ Retry failed plans
- ❌ Modify plans
- ❌ Make autonomous decisions

## Key Classes

### `PlanPresentation`
```python
@dataclass(frozen=True)
class PlanPresentation:
    plan_id: str
    user_intent: str
    summary: str
    steps: Tuple[StepPresentation, ...]
    faculties_involved: Tuple[str, ...]
    data_sources_accessed: Tuple[str, ...]
    capabilities_required: Tuple[str, ...]
    estimated_total_duration_sec: Optional[float]
    estimated_risk_level: str
    security_posture_snapshot: Dict[str, Any]
    irreversible_actions: Tuple[str, ...]
    assumptions: Tuple[str, ...]
    presentation_timestamp: str
    
    def to_human_text(self) -> str:
        """Export as human-readable string"""
```

### `ApprovalPromptBuilder`
```python
class ApprovalPromptBuilder:
    @staticmethod
    def build_prompt(plan_pres, security_summary) -> str:
        """Generate factual approval prompt (no persuasion)"""
        
    @staticmethod
    def build_rejection_explanation(reason: str) -> str:
        """Generate rejection explanation"""
```

### `HestiaUIBoundary`
```python
class HestiaUIBoundary:
    @staticmethod
    def present_plan(plan_draft) -> PlanPresentation:
        """Convert PlanDraft to human-readable form"""
        
    @staticmethod
    def request_approval_from_user(plan_pres) -> Tuple[bool, str]:
        """Prompt user for YES/NO approval"""
        
    @staticmethod
    def explain_rejection(reason: str) -> str:
        """Human-readable rejection explanation"""
        
    @staticmethod
    def display_authority_constraints() -> str:
        """Show Hestia's boundaries"""
```

### `AuthorityFlowValidator`
```python
class AuthorityFlowValidator:
    @staticmethod
    def ensure_no_execution_authority(hestia) -> None:
        """Verify no execution methods"""
        
    @staticmethod
    def ensure_no_approval_authority(hestia) -> None:
        """Verify no approval methods"""
        
    @staticmethod
    def ensure_no_retry_logic(hestia) -> None:
        """Verify no retry methods"""
        
    @staticmethod
    def ensure_no_plan_mutation(plan_draft) -> Tuple[bool, str]:
        """Verify plan is immutable"""
```

### `ApprovalDecision`
```python
@dataclass(frozen=True)
class ApprovalDecision:
    decision_id: str
    plan_id: str
    approved: bool
    approver_identity: str
    timestamp: str
    reason: str
    security_state_at_decision: Dict[str, Any]
```

## HestiaAgent Integration

### Methods Added

```python
class HestiaAgent:
    
    def present_plan(self, plan_draft: PlanDraft) -> PlanPresentation:
        """Convert PlanDraft into human-readable form"""
        
    def request_approval(self, plan_draft: PlanDraft) -> Tuple[bool, str]:
        """Prompt user for approval"""
        
    def explain_rejection(self, reason: str) -> str:
        """Human-readable rejection explanation"""
        
    def display_authority_boundaries(self) -> str:
        """Show what Hestia can/cannot do"""
```

## Data Flow

```
User Request
    ↓
compile_plan()  # # LLM reasoning → plan
    ↓
PlanDraft (immutable)
    ↓
present_plan()  # # UX only
    ↓
PlanPresentation (frozen dataclass)
    ↓
Display: to_human_text()
    ↓
request_approval()  # # UX only
    ↓
User says YES or NO
    ↓
ApprovalDecision (frozen record)
    ↓
[STOP - Hand off to ApprovalExecutor]
```

## Immutability Guarantee

All UI objects are frozen dataclasses:

```python
@dataclass(frozen=True)
class PlanPresentation:
    ...

# Attempts to mutate:
object.__setattr__(plan_pres, "field", "value")  # Raises FrozenInstanceError
```

## Factual Approval Prompts

No persuasion, no alarmism. Just facts:

```
PLAN: [Summary]
User Intent: [What they asked for]

Current Security State: [SECURE/DEGRADED/LOCKED DOWN]

Risk Level: [low/medium/high/unknown]

WHAT THIS PLAN WILL DO:
  1. [Step 1]
  2. [Step 2]
  ...

DATA THAT WILL BE ACCESSED: [Sources]

PERMISSIONS NEEDED: [Capabilities]

ASSUMPTIONS (must be true for this plan to work):
  • [Assumption 1]
  • [Assumption 2]

⚠ IRREVERSIBLE ACTIONS (cannot be undone):
  • [Action 1]
  • [Action 2]

Do you want to approve this plan?
  Type: YES or NO
```

## Authority Validation

Verify Hestia's constraints:

```python
from hestia.ui_layer import AuthorityFlowValidator

validator = AuthorityFlowValidator()

# These must all pass (no exceptions)
validator.ensure_no_execution_authority(agent)
validator.ensure_no_approval_authority(agent)
validator.ensure_no_retry_logic(agent)

# This must return (True, "...")
is_immutable, reason = validator.ensure_no_plan_mutation(plan_draft)
assert is_immutable
```

## Constraints

1. **No External Dependencies**
   - Standard library only
   - No external packages

2. **No Async**
   - All methods synchronous
   - All I/O blocking

3. **No State Mutation**
   - All data frozen
   - All inputs preserved

4. **No Silent Failures**
   - All ambiguities explicit
   - No default assumptions

## Testing

Run examples:
```bash
python examples/hestia_ui_layer_example.py
```

Includes:
1. Simple plan presentation
2. High-risk plan with irreversible actions
3. Factual approval prompt
4. Rejection explanation
5. Authority boundaries display
6. Authority validation
7. Immutability verification
8. Approval decision record

## Integration Points

### Compiler → UI → Executor

```python
# Phase 1: Compile
plan_draft = agent.compile_plan(intent, llm_output)

# Phase 2: Present (this layer)
presentation = agent.present_plan(plan_draft)
approved, reason = agent.request_approval(plan_draft)

# Phase 3: Execute (separate component)
# NOT: agent.execute(...)
# YES: approval_executor.execute(approval_request)
```

### Key Principle

When user approves:
- Create `ApprovalRequest` (governance boundary)
- Send to `ApprovalExecutor` (execution boundary)
- Hestia's role is **finished**

Execution happens in **separate, isolated component** (ApprovalExecutor + Stage4).

## Mandatory Comments

Every method has:
```python
# UX only
# No authority
# No execution
# No autonomy
```

These are REQUIRED, not optional.

## Summary

| Aspect | Details |
|--------|---------|
| **Authority** | ZERO (no execution, no approval, no retry) |
| **Immutability** | 100% (all frozen dataclasses) |
| **Transparency** | 100% (all information visible) |
| **Fail-Closed** | YES (ambiguities default to "no") |
| **Dependencies** | Standard library only |
| **Async** | NO (all synchronous) |
| **Guarantees** | No execution, no approval, no mutation, no autonomy |

Hestia is a **proposal engine**, not an **execution engine**. Users decide everything.
