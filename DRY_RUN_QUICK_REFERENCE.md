# HEARTH DRY RUN - QUICK REFERENCE

## Core Rule
```
# Dry-run only
# No execution
# No authority transfer
# Inspection only
```

NO EXECUTION PERFORMED. Ever.

---

## Quick Start

```python
from artemis.dry_run import DryRunController
from hestia.agent import HestiaAgent
from core.kernel import Kernel

# 1. Initialize
kernel = Kernel()
kernel.boot()
agent = HestiaAgent(kernel=kernel)
controller = DryRunController(kernel=kernel, agent=agent)

# 2. Run dry-run
report = controller.run_full_loop(
    user_intent="Your request here",
    mocked_llm_output="""
PLAN_START
STEP_1: First action
STEP_2: Second action
PLAN_END
""",
    auto_approve=True,  # Or False to simulate rejection
)

# 3. Check results
print(report.to_human_text())
print(f"Execution performed: {report.execution_performed}")  # Always False
```

---

## What It Does

```
Think (Compile)
    ↓
Propose (Present)
    ↓
Approve (Request)
    ↓
[STOP - No Execute]
    ↓
Report
```

---

## Key Classes

### `DryRunController`
```python
class DryRunController:
    def __init__(self, kernel, agent):
        """Initialize with Artemis kernel and HestiaAgent"""
        
    def run_full_loop(
        user_intent: str,
        mocked_llm_output: str,
        auto_approve: bool = False,
        approver_identity: str = "test-user@example.com",
    ) -> DryRunReport:
        """Run full governance loop WITHOUT execution"""
```

### `DryRunReport`
```python
@dataclass(frozen=True)
class DryRunReport:
    dry_run_id: str
    timestamp: str
    user_intent: str
    
    # Compilation
    plan_compilation_success: bool
    plan_compilation_message: str
    plan_draft_summary: Optional[Dict]
    
    # Presentation
    plan_presentation_summary: Optional[Dict]
    approval_prompt_preview: Optional[str]
    
    # Approval
    approval_requested: bool
    approval_granted: bool
    approval_reason: str
    
    # Execution request (NOT executed)
    execution_request_built: bool
    execution_validation_passed: bool
    execution_validation_message: str
    
    # Security
    security_summary_at_start: Dict
    security_summary_at_approval: Dict
    security_summary_at_execution_check: Dict
    
    # Guarantee
    execution_performed: bool = False  # ALWAYS False
    explicit_statement: str = "NO EXECUTION PERFORMED - DRY RUN ONLY"
    
    def to_human_text(self) -> str:
        """Export as human-readable text"""
```

---

## Failure Paths

### 1. Compilation Failure
```python
# Bad LLM output (no step markers)
report = controller.run_full_loop(
    user_intent="Do something",
    mocked_llm_output="Just some text without markers",
)

report.plan_compilation_success == False
report.failure_step == "plan_compilation"
```

### 2. Approval Rejection
```python
# User rejects
report = controller.run_full_loop(
    user_intent="Delete data",
    mocked_llm_output="...",
    auto_approve=False,
)

report.approval_granted == False
report.execution_request_built == False
```

### 3. Lockdown Blocking
```python
# System in LOCKDOWN
kill_switch.engage(reason="Security incident")

report = controller.run_full_loop(...)

report.execution_validation_passed == False
report.security_summary_at_execution_check['state'] == "LOCKDOWN"
```

---

## Report Fields

### Compilation
- `plan_compilation_success` - Did it compile?
- `plan_compilation_message` - Success or error
- `plan_draft_summary` - Plan details (if compiled)

### Presentation
- `plan_presentation_summary` - Presentation details
- `approval_prompt_preview` - Approval prompt text

### Approval
- `approval_requested` - Was approval requested?
- `approval_granted` - Did user approve?
- `approval_reason` - Why approved/rejected

### Execution Check
- `execution_request_built` - Was request built?
- `execution_validation_passed` - Would it pass validation?
- `execution_validation_message` - Why allowed/blocked

### Guarantee
- `execution_performed` - **ALWAYS False**
- `explicit_statement` - "NO EXECUTION PERFORMED - DRY RUN ONLY"

---

## Examples

Run:
```bash
python examples/dry_run_example.py
```

6 examples:
1. Successful approval flow
2. Compilation failure
3. Approval rejection
4. Lockdown blocking
5. Immutability verification
6. Approved vs rejected comparison

---

## Use Cases

### Test Plan Compilation
```python
report = controller.run_full_loop(intent, llm_output)
if not report.plan_compilation_success:
    print(f"Fix LLM output: {report.plan_compilation_message}")
```

### Test Approval Flow
```python
report_yes = controller.run_full_loop(..., auto_approve=True)
report_no = controller.run_full_loop(..., auto_approve=False)
```

### Test Security Gates
```python
kill_switch.engage(reason="Test")
report = controller.run_full_loop(...)
assert not report.execution_validation_passed
```

---

## Constraints

**Dry Run Can:**
- ✅ Compile plans
- ✅ Present plans
- ✅ Request approval
- ✅ Build execution requests
- ✅ Validate (check if execution would be allowed)
- ✅ Report what WOULD happen

**Dry Run Cannot:**
- ❌ Execute plans
- ❌ Dispatch to Stage-4
- ❌ Cause side effects
- ❌ Modify state
- ❌ Access real resources

---

## Security Properties

### 1. No Execution
```python
report.execution_performed  # ALWAYS False
```

### 2. Immutable Reports
```python
@dataclass(frozen=True)
class DryRunReport:
    ...
```

### 3. Explicit Guarantee
```python
report.explicit_statement  # "NO EXECUTION PERFORMED - DRY RUN ONLY"
```

### 4. Read-Only Inspection
```python
# Only reads security state
# Never modifies it
```

---

## Integration

### Phase 1: Plan Compiler
```python
agent.compile_plan(intent, llm_output)  # Used by dry-run
```

### Phase 3: Hestia UI
```python
agent.present_plan(plan_draft)  # Used by dry-run
ApprovalPromptBuilder.build_prompt(...)  # Used by dry-run
```

### Phase 2: Approval Executor
```python
HandshakeValidator.validate(...)  # Used by dry-run
# BUT: ApprovalExecutor.execute() is NEVER called
```

---

## Verification

Check report:
```python
# Always False
assert report.execution_performed == False

# Explicit statement
assert "NO EXECUTION" in report.explicit_statement

# Immutable
try:
    object.__setattr__(report, "execution_performed", True)
    assert False, "Should have raised"
except (AttributeError, TypeError):
    pass  # Good
```

---

## Summary

| Aspect | Details |
|--------|---------|
| **Purpose** | Demonstrate governance loop without execution |
| **Authority** | ZERO (no execution, no dispatch, no side effects) |
| **Immutability** | 100% (frozen dataclass) |
| **Execution** | NEVER (explicit guarantee) |
| **Inspection** | Read-only (security state snapshots) |
| **Fail-Closed** | YES (all ambiguities explicit) |
| **Dependencies** | Standard library only |

**Key Principle:** Shows what WOULD happen without actually doing it.

**Use For:** Testing, documentation, development, debugging.

**Don't Use For:** Actual execution (use ApprovalExecutor instead).

---

**Status:** ✅ COMPLETE
**Compilation:** ✅ 0 ERRORS
**Examples:** ✅ 6 WORKING EXAMPLES
**Guarantee:** ⚠ NO EXECUTION EVER
