# HEARTH DRY RUN - SPECIFICATION

## Overview

The HEARTH Dry Run system demonstrates the full governance loop **without executing anything**.

**Core Principle:**
```
# Dry-run only
# No execution
# No authority transfer
# Inspection only
```

This is a **demonstration tool**, not an execution tool.

---

## Purpose

### What It Does
- Accepts user intent
- Compiles plan (Phase 1)
- Presents plan (Phase 3)
- Requests approval (Phase 3)
- Builds execution request (Phase 2)
- **STOPS** before execution

### What It Does NOT Do
- ❌ Execute plans
- ❌ Dispatch to Stage-4
- ❌ Cause side effects
- ❌ Perform background work
- ❌ Transfer authority

### Why It Exists
- Demonstrate the governance loop
- Test plan compilation
- Verify approval flow
- Validate security gates
- Audit decision paths
- **WITHOUT** executing anything

---

## Architecture

### DryRunController

Orchestrates the full governance loop in read-only mode.

```python
class DryRunController:
    def __init__(self, kernel, agent):
        """Initialize with Artemis kernel and HestiaAgent"""
        
    def run_full_loop(
        self,
        user_intent: str,
        mocked_llm_output: str,
        auto_approve: bool = False,
        approver_identity: str = "test-user@example.com",
    ) -> DryRunReport:
        """
        Run full governance loop WITHOUT execution.
        
        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only
        """
```

### DryRunReport

Immutable record of the dry-run governance loop.

```python
@dataclass(frozen=True)
class DryRunReport:
    dry_run_id: str
    timestamp: str
    user_intent: str
    
    # Phase 1: Compilation
    plan_compilation_success: bool
    plan_compilation_message: str
    plan_draft_summary: Optional[Dict[str, Any]]
    
    # Phase 3: Presentation
    plan_presentation_summary: Optional[Dict[str, Any]]
    approval_prompt_preview: Optional[str]
    
    # Phase 3: Approval
    approval_requested: bool
    approval_granted: bool
    approval_reason: str
    approval_decision_id: Optional[str]
    
    # Phase 2: Execution Request
    execution_request_built: bool
    execution_request_summary: Optional[Dict[str, Any]]
    execution_validation_passed: bool
    execution_validation_message: str
    
    # Security state
    security_summary_at_start: Dict[str, Any]
    security_summary_at_approval: Dict[str, Any]
    security_summary_at_execution_check: Dict[str, Any]
    
    # Explicit statement
    execution_performed: bool = False  # ALWAYS False
    explicit_statement: str = "NO EXECUTION PERFORMED - DRY RUN ONLY"
    
    # Failure tracking
    failure_step: Optional[str] = None
    failure_reason: Optional[str] = None
    
    def to_human_text(self) -> str:
        """Export as human-readable text"""
```

---

## Data Flow

```
User Intent + Mocked LLM Output
    ↓
DryRunController.run_full_loop()
    ↓
PHASE 1: PLAN COMPILATION
    ↓ (# Dry-run only)
PlanDraft (immutable)
    ↓
PHASE 3: PRESENTATION
    ↓ (# Dry-run only)
PlanPresentation (human-readable)
    ↓
PHASE 3: APPROVAL REQUEST
    ↓ (# Dry-run only)
User approval decision (auto or manual)
    ↓
IF APPROVED:
    ↓
PHASE 2: EXECUTION REQUEST
    ↓ (# Dry-run only)
ExecutionRequest built
    ↓
Validation checked (but NOT executed)
    ↓
[STOP - No execution]
    ↓
DryRunReport (immutable)
```

**Key Point:** Flow stops before execution. No Stage-4 dispatch.

---

## Usage

### Basic Usage

```python
from artemis.dry_run import DryRunController
from hestia.agent import HestiaAgent
from core.kernel import Kernel

# Initialize
kernel = Kernel()
kernel.boot()

agent = HestiaAgent(kernel=kernel)
controller = DryRunController(kernel=kernel, agent=agent)

# Run dry-run
report = controller.run_full_loop(
    user_intent="Analyze my activity from last week",
    mocked_llm_output="""
PLAN_START
STEP_1: Retrieve activity data
STEP_2: Analyze patterns
STEP_3: Store insights
PLAN_END
""",
    auto_approve=True,
)

# Display report
print(report.to_human_text())
```

### What Gets Returned

```python
report = controller.run_full_loop(...)

# Check compilation
report.plan_compilation_success  # True if compiled
report.plan_compilation_message   # Success or error

# Check presentation
report.plan_presentation_summary  # Summary of plan
report.approval_prompt_preview    # Approval prompt text

# Check approval
report.approval_granted           # True if approved
report.approval_reason            # Why approved/rejected

# Check execution request (if approved)
report.execution_request_built    # True if built
report.execution_validation_passed  # Would it pass validation?
report.execution_validation_message  # Why allowed/blocked

# Security state throughout
report.security_summary_at_start
report.security_summary_at_approval
report.security_summary_at_execution_check

# Explicit guarantee
report.execution_performed        # ALWAYS False
report.explicit_statement         # "NO EXECUTION PERFORMED - DRY RUN ONLY"
```

---

## Failure Paths

### 1. Compilation Failure

When LLM output doesn't have explicit step markers:

```python
mocked_llm_output = """
1. Do this
2. Do that
3. Do the other thing
"""

report = controller.run_full_loop(
    user_intent="Do something",
    mocked_llm_output=mocked_llm_output,
)

# Result:
report.plan_compilation_success == False
report.failure_step == "plan_compilation"
report.failure_reason == "Parse error: ..."
```

### 2. Approval Rejection

When user (or auto_approve=False) rejects:

```python
report = controller.run_full_loop(
    user_intent="Delete my data",
    mocked_llm_output="...",
    auto_approve=False,  # User rejects
)

# Result:
report.approval_granted == False
report.execution_request_built == False
report.execution_performed == False
```

### 3. Lockdown Blocking

When system is in LOCKDOWN:

```python
# Trigger LOCKDOWN
kill_switch = KillSwitch(kernel=kernel)
kill_switch.engage(reason="Security incident")

report = controller.run_full_loop(
    user_intent="Show my notes",
    mocked_llm_output="...",
    auto_approve=True,
)

# Result:
report.execution_validation_passed == False
report.execution_validation_message == "System in LOCKDOWN"
report.security_summary_at_execution_check['state'] == "LOCKDOWN"
```

---

## Security Properties

### 1. No Execution Authority

```python
# DryRunController can:
- Compile plans
- Present plans
- Request approval
- Build execution requests
- Validate execution requests

# DryRunController CANNOT:
- Execute plans
- Dispatch to Stage-4
- Cause side effects
- Transfer authority
- Perform background work
```

### 2. Immutable Reports

```python
@dataclass(frozen=True)
class DryRunReport:
    ...

# Attempts to mutate:
object.__setattr__(report, "execution_performed", True)
# Raises: FrozenInstanceError
```

### 3. Explicit Guarantee

```python
report.execution_performed  # ALWAYS False
report.explicit_statement   # "NO EXECUTION PERFORMED - DRY RUN ONLY"
```

Every report includes an explicit statement that no execution happened.

### 4. Read-Only Inspection

```python
# Security state inspection:
security_at_start = self._get_security_snapshot()
security_at_approval = self._get_security_snapshot()
security_at_execution_check = self._get_security_snapshot()

# No mutations, no state changes
# Inspection only
```

---

## Examples

See `examples/dry_run_example.py` for 6 working examples:

1. **Successful Approval Flow** - Full loop without execution
2. **Compilation Failure** - What happens when parsing fails
3. **Approval Rejection** - What happens when user rejects
4. **Lockdown Blocking** - What happens in LOCKDOWN
5. **Immutability Verification** - Verify report is frozen
6. **Approved vs Rejected** - Side-by-side comparison

Run:
```bash
python examples/dry_run_example.py
```

---

## Report Format

### Human-Readable Output

```
======================================================================
DRY RUN REPORT: [UUID]
======================================================================

⚠ NO EXECUTION PERFORMED - DRY RUN ONLY

User Intent: [Intent]
Timestamp: [ISO 8601]

======================================================================
PHASE 1: PLAN COMPILATION
======================================================================
Success: True
Message: Plan compiled successfully (3 steps)

Plan Draft Summary:
  Plan ID: [UUID]
  Steps: 3
  Faculties: knowledge_retrieval, analysis, memory_write
  Risk Level: low

======================================================================
PHASE 3: PRESENTATION & APPROVAL
======================================================================
Presentation Created: Yes
Approval Requested: True

Approval Prompt Preview:
[First 500 chars of approval prompt]

Approval Granted: True
Approval Reason: Auto-approved for dry-run testing
Approval Decision ID: [UUID]

======================================================================
PHASE 2: EXECUTION REQUEST (DRY RUN)
======================================================================
Execution Request Built: Yes
Validation Would Pass: True
Validation Message: All validation checks passed

Execution Request Summary:
  Request ID: [UUID]
  Plan ID: [UUID]
  Approver: demo-user@example.com

======================================================================
SECURITY STATE THROUGHOUT
======================================================================
At Start: SECURE
At Approval: SECURE
At Execution Check: SECURE

======================================================================
⚠ NO EXECUTION PERFORMED - DRY RUN ONLY
======================================================================
```

---

## Integration with Phases

### Phase 1: Plan Compiler

```python
# DryRunController uses:
plan_draft, msg = agent.compile_plan(intent, llm_output)
```

### Phase 3: Hestia UI Layer

```python
# DryRunController uses:
presentation = agent.present_plan(plan_draft)
approval_prompt = ApprovalPromptBuilder.build_prompt(...)
```

### Phase 2: Approval Executor

```python
# DryRunController uses:
approval_request = ApprovalRequest(...)
execution_request = ExecutionRequest(...)
validator = HandshakeValidator(kernel=kernel)
validation_result = validator.validate(execution_request)

# BUT: DryRunController NEVER calls executor.execute()
```

---

## Constraints

### 1. No External Dependencies
- Standard library only
- No external packages
- No network calls

### 2. No Async Operations
- All methods synchronous
- All I/O blocking
- No background threads

### 3. No State Mutation
- All inputs preserved
- All outputs frozen
- No side effects

### 4. No Execution
- No Stage-4 dispatch
- No action execution
- No resource modification

### 5. Fail-Closed
- All ambiguities explicit
- All errors reported
- No silent failures

---

## Testing

Run all examples:
```bash
python examples/dry_run_example.py
```

Expected output:
- 6 examples execute successfully
- All reports show `execution_performed = False`
- All reports include explicit statement
- All failure paths demonstrated

---

## Use Cases

### 1. Development Testing
Test plan compilation without executing:
```python
report = controller.run_full_loop(intent, llm_output)
if not report.plan_compilation_success:
    print(f"Compilation failed: {report.plan_compilation_message}")
```

### 2. Approval Flow Testing
Test approval decisions:
```python
report_approved = controller.run_full_loop(..., auto_approve=True)
report_rejected = controller.run_full_loop(..., auto_approve=False)
```

### 3. Security Gate Testing
Test LOCKDOWN blocking:
```python
kill_switch.engage(reason="Test")
report = controller.run_full_loop(...)
assert not report.execution_validation_passed
```

### 4. Documentation
Generate examples for documentation:
```python
report = controller.run_full_loop(...)
with open("example.txt", "w") as f:
    f.write(report.to_human_text())
```

---

## Limitations

### What Dry Run Can Do
- ✅ Compile plans
- ✅ Present plans
- ✅ Request approval
- ✅ Build execution requests
- ✅ Validate execution requests
- ✅ Report what WOULD happen

### What Dry Run Cannot Do
- ❌ Actually execute plans
- ❌ Cause side effects
- ❌ Modify system state
- ❌ Access real resources
- ❌ Dispatch to Stage-4

### What You Need Real Execution For
- Actually running plans
- Modifying data
- Creating artifacts
- Interacting with external systems

---

## Summary

The HEARTH Dry Run system:
- ✅ Demonstrates full governance loop
- ✅ Tests plan compilation
- ✅ Verifies approval flow
- ✅ Validates security gates
- ✅ Produces immutable reports
- ✅ Explicit "no execution" guarantee
- ✅ Read-only inspection only
- ✅ Fail-closed by default
- ✅ Standard library only

**Key Principle:** Shows what WOULD happen without actually doing it.

**Use When:** Testing, documentation, development, debugging.

**Don't Use When:** You need actual execution (use ApprovalExecutor instead).

---

## Next Steps

After dry-run testing:
1. If plan compiles correctly → proceed to real approval flow
2. If plan fails compilation → fix LLM output format
3. If approval rejected → revise plan
4. If validation fails → check security state

Dry run is the **first step** in the governance loop, not the last.
