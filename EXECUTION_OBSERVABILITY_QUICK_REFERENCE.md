# EXECUTION OBSERVABILITY & ROLLBACK SCAFFOLD - QUICK REFERENCE

## TL;DR

**Step 19** = Immutable execution records + optional manual rollback guidance (NOT executed)

- **ExecutionRecord**: Captures complete execution history (hash-linked events, security snapshots)
- **ExecutionObserver**: Records step events (append-only, best-effort side effects)
- **RollbackScaffold**: Surfaces rollback hints (verbatim from plan, NOT executed)
- **Hestia UX**: Displays execution results and rollback options (no automation)

## Quick Start

### 1. Create Observer

```python
from artemis.execution_observability import ExecutionObserver
from core.kernel import Kernel

kernel = Kernel()
observer = ExecutionObserver(
    execution_id="exec-001",
    plan_id="plan-001",
    kernel=kernel,
)
```

### 2. Record Execution

```python
# Record step started
observer.record_step_started(0, "Initialize", {"input": "data"})

# Record step completed
observer.record_step_completed(0, "Initialize", {"output": "ready"})

# Record side effect
observer.record_side_effect(
    SideEffectCategory.FILE_SYSTEM,
    "Created /tmp/data.txt",
    reversible=True,
)

# Mark execution complete
observer.mark_completed("All steps finished")
```

### 3. Get Execution Record

```python
record = observer.get_execution_record("LIVE")

# Record is immutable and hash-linked
print(record.status.value)  # "completed"
print(record.execution_hash[:16])  # First 16 chars of hash
```

### 4. Create Rollback Scaffold

```python
from artemis.execution_observability import RollbackPlanner

rollback_hints = [
    {
        "step_index": 0,
        "description": "Drop database",
        "actions": ["DROP DATABASE test_db;"],
        "risks": ["Irreversible - all data lost"],
    }
]

scaffold = RollbackPlanner.plan_rollback(record, rollback_hints)

if scaffold.is_rollback_possible:
    print("✓ Rollback is possible (but NOT executed)")
else:
    print("✗ Rollback not possible")
    print(scaffold.reason)
```

### 5. Display with Hestia

```python
from hestia.agent import HestiaAgent

agent = HestiaAgent(kernel=kernel)

# Display execution summary
summary = agent.display_execution_summary(record)
print(summary)

# Show irreversible actions
irreversible = agent.show_irreversible_actions(record)
print(irreversible)

# Show rollback guidance (NOT executed)
guidance = agent.show_rollback_guidance(scaffold)
print(guidance)

# Request rollback confirmation (user must execute manually)
confirmed, reason = agent.confirm_manual_rollback(scaffold)
```

## Components

### ExecutionRecord

| Field | Type | Description |
|-------|------|-------------|
| `execution_id` | str | Unique execution identifier |
| `plan_id` | str | Plan being executed |
| `live_mode_state` | str | "DRY_RUN" or "LIVE" |
| `security_snapshot_pre` | SecuritySnapshot | Security state before execution |
| `security_snapshot_post` | SecuritySnapshot | Security state after execution |
| `step_events` | Tuple[StepEvent, ...] | Hash-linked step events (immutable) |
| `side_effects_report` | SideEffectReport | Declared vs observed effects |
| `status` | ExecutionStatus | STARTED, COMPLETED, FAILED, INCOMPLETE |
| `timestamp_start` | datetime | Execution start time |
| `timestamp_end` | datetime | Execution end time (if complete) |

### StepEvent (Hash-Linked)

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | datetime | When event occurred |
| `step_index` | int | Step number |
| `step_name` | str | Step name |
| `event_type` | StepEventType | STARTED, COMPLETED, FAILED |
| `details` | Dict | Additional details |
| `error_message` | str | Error (if failed) |
| `previous_event_hash` | str | Hash of previous event (chain linking) |

### ExecutionObserver Methods

| Method | Purpose |
|--------|---------|
| `record_step_started(index, name, details)` | Record step start |
| `record_step_completed(index, name, details)` | Record step completion |
| `record_step_failed(index, name, error, details)` | Record step failure |
| `record_side_effect(category, description, reversible, details)` | Record side effect |
| `mark_completed(reason)` | Mark execution complete |
| `mark_failed(reason)` | Mark execution failed |
| `mark_incomplete_security_escalation(reason)` | Mark incomplete (security) |
| `get_execution_record(live_mode_state)` | Get immutable record |

### RollbackScaffold

| Field | Type | Description |
|-------|------|-------------|
| `execution_id` | str | Execution identifier |
| `is_rollback_possible` | bool | Can rollback proceed? |
| `reason` | str | Why or why not |
| `rollback_hints` | Tuple[RollbackHint, ...] | Hints from plan (verbatim) |
| `warnings` | Tuple[str, ...] | Important warnings |
| `irreversible_steps` | Tuple[int, ...] | Steps that can't be undone |
| `manual_steps` | Tuple[str, ...] | User must perform these |

### Hestia UX Methods

| Method | Purpose |
|--------|---------|
| `display_execution_summary(record)` | Show execution results |
| `show_irreversible_actions(record)` | List actions that can't be undone |
| `show_rollback_guidance(scaffold)` | Display rollback options |
| `confirm_manual_rollback(scaffold)` | Request rollback confirmation (NO EXECUTION) |

## Execution Status

| Status | Meaning |
|--------|---------|
| `STARTED` | Execution began but didn't complete |
| `COMPLETED` | All steps completed successfully |
| `COMPLETED_PARTIAL` | Some steps completed before failure |
| `FAILED` | Execution failed (stopped by error) |
| `INCOMPLETE` | Security escalation stopped execution |

## Side Effect Categories

| Category | Description |
|----------|-------------|
| `FILE_SYSTEM` | Files created/modified/deleted |
| `NETWORK` | Network calls made |
| `DATA_MUTATION` | Data modified |
| `CONFIGURATION` | Configuration changed |
| `SYSTEM` | System-level changes |
| `OTHER` | Other effects |

## Common Patterns

### Pattern: Record Successful Execution

```python
observer.record_step_started(0, "Step", {})
observer.record_step_completed(0, "Step", {})
observer.mark_completed()

record = observer.get_execution_record("LIVE")
assert record.status == ExecutionStatus.COMPLETED
```

### Pattern: Record Failed Execution

```python
observer.record_step_started(0, "Step 1", {})
observer.record_step_completed(0, "Step 1", {})

observer.record_step_started(1, "Step 2", {})
observer.record_step_failed(1, "Step 2", "Error message")

observer.mark_failed("Step 2 failed")

record = observer.get_execution_record("LIVE")
assert record.status == ExecutionStatus.FAILED
```

### Pattern: Record Security Escalation

```python
observer.record_step_completed(0, "Safe step", {})

# Security state degrades
kernel._security_state = SecurityState.COMPROMISED

observer.mark_incomplete_security_escalation()

record = observer.get_execution_record("LIVE")
assert record.status == ExecutionStatus.INCOMPLETE
```

### Pattern: Track Side Effects

```python
observer.record_side_effect(
    SideEffectCategory.FILE_SYSTEM,
    "Created /tmp/output.txt",
    reversible=True,
    step_index=0,
)

record = observer.get_execution_record("LIVE")
# record.side_effects_report contains all observed effects
```

### Pattern: Manual Rollback (NOT Executed)

```python
scaffold = RollbackPlanner.plan_rollback(record, hints)

if scaffold.is_rollback_possible:
    # User reviews rollback hints (from plan, verbatim)
    for hint in scaffold.rollback_hints:
        print(f"Step {hint.step_index}: {hint.description}")
        for action in hint.actions:
            print(f"  - {action}")  # User must execute manually
else:
    print(f"Rollback not possible: {scaffold.reason}")
```

## Key Constraints

| Constraint | Implementation |
|------------|-----------------|
| **No automation** | Rollback is NOT executed, only suggested |
| **No retries** | Failed execution is not retried |
| **No state mutation** | Events are append-only, immutable |
| **Fail-closed** | Stops immediately on error |
| **No background execution** | Everything is synchronous |
| **Standard library only** | No external dependencies |

## Anti-Patterns

### ❌ Automatic Rollback

```python
# WRONG
if record.status == FAILED:
    execute_rollback(scaffold)  # ❌ NO AUTOMATION
```

### ❌ Inferred Rollback

```python
# WRONG
rollback_steps = infer_undo(record)  # ❌ NO INFERENCE
```

### ❌ Modifying Records

```python
# WRONG
record._status = COMPLETED  # ❌ NO MUTATION
```

## Verification

### Run Examples

```bash
python examples/execution_observability_example.py
```

### Check Compilation

```bash
python -m py_compile artemis/execution_observability.py
```

## Files

| File | Purpose |
|------|---------|
| [artemis/execution_observability.py](artemis/execution_observability.py) | Core implementation (600+ lines) |
| [hestia/agent.py](hestia/agent.py) | UX methods (+200 lines) |
| [examples/execution_observability_example.py](examples/execution_observability_example.py) | Working examples |
| [EXECUTION_OBSERVABILITY_SPEC.md](EXECUTION_OBSERVABILITY_SPEC.md) | Complete specification |

## Design Philosophy

**Post-execution inspection only**
- Records capture what happened (not real-time)
- Analysis happens after execution completes
- No background state changes

**No automation**
- Rollback requires explicit human decision
- User reviews all hints before proceeding
- Each rollback step is manual

**Complete audit trail**
- Hash-linked events (tamper-evident)
- Security snapshots (before and after)
- Side effects tracking (best-effort)
- All transitions immutable

**Fail-closed**
- Defaults assume worst case
- Security escalation stops execution
- Partial execution clearly marked
- Explicit status for every outcome

## Summary

**Step 19** provides immutable execution records and optional manual rollback guidance.

**Creates**:
- ✅ ExecutionRecord (immutable, hash-linked, tamper-evident)
- ✅ ExecutionObserver (records step events, side effects)
- ✅ RollbackScaffold (surfaces hints, NOT executed)
- ✅ Hestia UX (displays results, requests confirmation)

**Guarantees**:
- ✅ Complete audit trail of execution
- ✅ Security context captured
- ✅ Side effects tracked (best-effort)
- ✅ Rollback options presented (manual only)
- ✅ No automation, no retries, no mutation

**Status**: Post-execution inspection and manual rollback guidance only
