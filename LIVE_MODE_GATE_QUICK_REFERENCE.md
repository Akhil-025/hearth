# LIVE MODE GATE - QUICK REFERENCE

## TL;DR

**Live Mode Gate** = Explicit "master switch" controlling execution authority

- **Default**: DRY_RUN (execution blocked, safe)
- **Enable**: Explicit, requires reason + user identity
- **Disable**: Manual or auto-revert on security degradation
- **Audit**: Complete, immutable transition history

## States

| State | Execution | Safety | Use Case |
|-------|-----------|--------|----------|
| **DRY_RUN** | ❌ BLOCKED | ✅ SAFE | Testing, development, demos |
| **LIVE** | ✅ ENABLED | ⚠️ DANGEROUS | Production execution |

## Quick Start

### 1. Create Gate (Defaults to DRY_RUN)

```python
from artemis.live_mode_gate import LiveModeGate
from core.kernel import Kernel

kernel = Kernel()
gate = LiveModeGate(kernel=kernel)

# Check state
print(gate.get_state().value)  # "DRY_RUN"
print(gate.is_dry_run())       # True
print(gate.is_live())          # False
```

### 2. Enable Live Mode

```python
success, message = gate.enable_live(
    reason="Production deployment of approved changes",
    user_identity="operator@example.com",
)

if success:
    print(f"✓ LIVE MODE ENABLED: {message}")
    # Execution is now allowed
else:
    print(f"✗ FAILED: {message}")
    # Execution still blocked
```

### 3. Execute (Gate is Checked)

```python
from artemis.approval_executor import ApprovalExecutor

executor = ApprovalExecutor(
    stage4_orchestrator=None,
    kernel=kernel,
    live_mode_gate=gate,  # Gate is checked before execution
)

# If gate is DRY_RUN: execution blocked
# If gate is LIVE: execution proceeds
success, message, results = executor.execute(execution_request)
```

### 4. Disable Live Mode

```python
success, message = gate.disable_live(
    reason="Task complete, returning to safe mode",
    user_identity="operator@example.com",
    automatic=False,
)

if success:
    print(f"✓ LIVE MODE DISABLED: {message}")
    # Execution is now blocked (safe)
```

## Hestia UI Integration

```python
from hestia.agent import HestiaAgent

agent = HestiaAgent(kernel=kernel)

# Display status
print(agent.display_live_mode_status(gate))

# Explain consequences
print(agent.explain_live_mode_consequences())

# Enable via Hestia
success, message = agent.enable_live_mode(
    live_mode_gate=gate,
    reason="Production deployment",
    user_identity="operator@example.com",
)
print(message)

# Disable via Hestia
success, message = agent.disable_live_mode(
    live_mode_gate=gate,
    reason="Deployment complete",
    user_identity="operator@example.com",
)
print(message)
```

## Auto-Revert (Security Integration)

```python
# Gate monitors security state
from artemis.boundary import SecurityState

# Simulate security degradation
kernel._security_state = SecurityState.COMPROMISED

# Check security and auto-revert if needed
reverted = gate.check_security_and_revert_if_needed()

if reverted:
    print("⚠️ AUTO-REVERTED to DRY_RUN due to security degradation")
    # Gate is now DRY_RUN, execution blocked

# Check transition history
transitions = gate.get_transition_history()
for t in transitions:
    if t.automatic:
        print(f"Auto-revert: {t.reason}")
```

## Audit Trail

```python
# Get complete transition history
transitions = gate.get_transition_history()

for transition in transitions:
    auto_flag = "[AUTO]" if transition.automatic else "[MANUAL]"
    print(f"{transition.timestamp}: {transition.from_state.value} → {transition.to_state.value} {auto_flag}")
    print(f"  Reason: {transition.reason}")
    print(f"  User: {transition.user_identity}")
```

## Common Patterns

### Pattern: Development Testing

```python
# Gate defaults to DRY_RUN (safe)
gate = LiveModeGate(kernel=kernel)
executor = ApprovalExecutor(live_mode_gate=gate, ...)

# Test governance loop without execution
success, message, results = executor.execute(request)
# Execution blocked, validation successful
```

### Pattern: Production Execution

```python
# Create gate
gate = LiveModeGate(kernel=kernel)

# Show status and consequences
print(agent.display_live_mode_status(gate))
print(agent.explain_live_mode_consequences())

# Enable LIVE mode
success, msg = agent.enable_live_mode(gate, "Deploy migration", "dba@example.com")
if not success:
    return  # Cannot enable

# Execute
success, msg, results = executor.execute(request)

# Disable LIVE mode
agent.disable_live_mode(gate, "Migration complete", "dba@example.com")
```

### Pattern: Security Response

```python
# Gate is LIVE
gate.enable_live("Active maintenance", "ops@example.com")

# Security incident detected
kernel._security_state = SecurityState.COMPROMISED

# Auto-revert to DRY_RUN
reverted = gate.check_security_and_revert_if_needed()
# Execution now blocked

# Verify in audit trail
transitions = gate.get_transition_history()
# Last transition: automatic=True, reason="Automatic revert: Security state is COMPROMISED"
```

## Validation

### Gate Validator

```python
from artemis.live_mode_gate import LiveModeGateValidator

# Check if execution is allowed
can_execute, reason = LiveModeGateValidator.can_execute(gate)

if can_execute:
    print(f"✓ Execution allowed: {reason}")
else:
    print(f"✗ Execution blocked: {reason}")
```

### Input Validation

```python
# Empty reason
success, msg = gate.enable_live("", "user")
# success=False, msg="Reason cannot be empty"

# Empty user
success, msg = gate.enable_live("reason", "")
# success=False, msg="User identity cannot be empty"

# Security state not operational
kernel._security_state = SecurityState.COMPROMISED
success, msg = gate.enable_live("reason", "user")
# success=False, msg="Cannot enable LIVE: Security state is COMPROMISED"
```

## Key Methods

### LiveModeGate

| Method | Returns | Description |
|--------|---------|-------------|
| `enable_live(reason, user)` | `(bool, str)` | Enable execution (DRY_RUN → LIVE) |
| `disable_live(reason, user, automatic)` | `(bool, str)` | Disable execution (LIVE → DRY_RUN) |
| `check_security_and_revert_if_needed()` | `bool` | Auto-revert if security degraded |
| `get_state()` | `LiveModeState` | Get current state |
| `is_live()` | `bool` | Check if execution enabled |
| `is_dry_run()` | `bool` | Check if execution blocked |
| `get_transition_history()` | `Tuple[LiveModeTransition, ...]` | Get immutable audit trail |

### LiveModeGateValidator

| Method | Returns | Description |
|--------|---------|-------------|
| `can_execute(gate)` | `(bool, str)` | Check if gate allows execution |

### HestiaAgent (UX Methods)

| Method | Returns | Description |
|--------|---------|-------------|
| `display_live_mode_status(gate)` | `str` | Show current status and history |
| `explain_live_mode_consequences()` | `str` | Explain risks and implications |
| `enable_live_mode(gate, reason, user)` | `(bool, str)` | Enable with user-friendly feedback |
| `disable_live_mode(gate, reason, user)` | `(bool, str)` | Disable with user-friendly feedback |

## Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Fail-Closed** | Default state is DRY_RUN (execution blocked) |
| **Explicit** | Enable requires reason + user identity |
| **Auditable** | All transitions recorded immutably |
| **Stateless** | No persistence, every session starts DRY_RUN |
| **Orthogonal** | Independent of approval, only controls execution |

## Security Integration

| Trigger | Action | Result |
|---------|--------|--------|
| **COMPROMISED** | Auto-revert to DRY_RUN | Execution blocked |
| **LOCKDOWN** | Auto-revert to DRY_RUN | Execution blocked |
| **OPERATIONAL** | Allow enable_live() | Can enable LIVE mode |

## Constraints

| Constraint | Rationale |
|------------|-----------|
| **No automatic enable** | Execution requires human intent |
| **No persistence** | Always start in safe state |
| **No timers** | No background state changes |
| **Standard library only** | No external dependencies |

## Anti-Patterns

### ❌ Auto-Enable on Approval

```python
# WRONG
if user_approves(plan):
    gate.enable_live("Approved", user)  # ❌ BAD
    executor.execute(request)

# RIGHT
if user_approves(plan):
    # Approval and execution are separate
    # User must explicitly enable gate when ready
    pass
```

### ❌ Persistent LIVE State

```python
# WRONG
with open("gate_state.txt", "w") as f:
    f.write(gate.get_state().value)  # ❌ BAD

# RIGHT
# Gate always starts in DRY_RUN
# No state saved to disk
```

### ❌ Timed Auto-Disable

```python
# WRONG
gate.enable_live("Test", user)
time.sleep(60)
gate.disable_live("Timeout", "system", True)  # ❌ BAD

# RIGHT
gate.enable_live("Test", user)
# ... execute ...
gate.disable_live("Complete", user, False)  # Explicit disable
```

## Troubleshooting

### Execution is Blocked

```python
# Check gate state
print(f"Gate state: {gate.get_state().value}")

# Check if DRY_RUN
if gate.is_dry_run():
    print("Gate is in DRY_RUN mode (execution blocked)")
    print("Enable LIVE mode to allow execution")
    
    # Enable if appropriate
    success, msg = gate.enable_live(reason, user)
    if not success:
        print(f"Cannot enable: {msg}")
```

### Cannot Enable LIVE Mode

```python
# Check security state
security_state = kernel.get_security_state()
print(f"Security state: {security_state.value}")

if security_state != SecurityState.OPERATIONAL:
    print("Security state is not OPERATIONAL")
    print("Resolve security issues before enabling LIVE mode")
```

### Gate Reverted Automatically

```python
# Check transition history
transitions = gate.get_transition_history()

for t in transitions:
    if t.automatic:
        print(f"Auto-revert occurred at {t.timestamp}")
        print(f"  Reason: {t.reason}")
        print(f"  From: {t.from_state.value} → To: {t.to_state.value}")
```

## Examples

See [examples/live_mode_gate_example.py](examples/live_mode_gate_example.py) for complete working examples:

1. Default DRY_RUN blocking execution
2. Enable LIVE mode and execute
3. Auto-revert on security degradation
4. Manual disable after execution
5. Transition history audit
6. Integration with Hestia UI

## See Also

- [LIVE_MODE_GATE_SPEC.md](LIVE_MODE_GATE_SPEC.md) - Complete specification
- [artemis/live_mode_gate.py](artemis/live_mode_gate.py) - Implementation
- [artemis/approval_executor.py](artemis/approval_executor.py) - Gate integration
- [hestia/agent.py](hestia/agent.py) - Hestia UI methods
