# LIVE MODE GATE SPECIFICATION

## Overview

The **Live Mode Gate** is an explicit, auditable authority boundary that controls whether approved execution plans can proceed to actual execution. It implements a fail-closed safety mechanism where execution is **disabled by default** and must be explicitly enabled by a human operator.

## Purpose

The Live Mode Gate solves the critical problem of **execution authority transfer**:

1. **Plans are compiled** → LLM reasoning produces executable instructions
2. **Plans are approved** → Human operator confirms intent
3. **Gate is checked** → **HARD BOUNDARY**: Is execution allowed?
4. **Plans are executed** → Only if gate is LIVE

Without the gate, approval would automatically lead to execution. The gate adds an explicit "master switch" that decouples approval from execution, allowing:

- Testing the governance loop without risk (DRY_RUN mode)
- Explicit opt-in to execution (LIVE mode)
- Automatic safety responses to security degradation
- Complete audit trail of execution authority changes

## States

### DRY_RUN (Default)

- **Execution**: BLOCKED
- **Behavior**: Plans are validated but not executed
- **Safety**: Fail-closed (safe default)
- **Use case**: Testing, development, demonstrations

When in DRY_RUN:
- ApprovalExecutor performs all validation
- Plan structure is verified
- Approval handshake is checked
- No commands are executed
- No files are created/modified/deleted
- Audit trail records "execution would have happened"

### LIVE

- **Execution**: ENABLED
- **Behavior**: Approved plans are executed
- **Safety**: Fail-open (dangerous)
- **Use case**: Production execution

When in LIVE:
- ApprovalExecutor performs full execution
- Commands are run
- Files are modified
- System state changes
- All consequences are real

## Transitions

### DRY_RUN → LIVE (Enable)

**Method**: `enable_live(reason: str, user_identity: str) → (bool, str)`

**Requirements**:
- Explicit reason (why execution is needed)
- User identity (who is enabling)
- Security state must be OPERATIONAL (not COMPROMISED/LOCKDOWN)

**Validation**:
```python
# Check security state first
if kernel.get_security_state() in [SecurityState.COMPROMISED, SecurityState.LOCKDOWN]:
    return False, "Cannot enable LIVE: Security state is not operational"

# Record transition
transition = LiveModeTransition(
    timestamp=datetime.now(),
    from_state=LiveModeState.DRY_RUN,
    to_state=LiveModeState.LIVE,
    reason=reason,
    user_identity=user_identity,
    automatic=False,
)
```

**Audit Trail**:
- Transition recorded immutably
- Timestamp of enable
- Reason for enabling
- User who enabled
- Security state at time of enable

**Example**:
```python
gate = LiveModeGate(kernel=kernel)
success, message = gate.enable_live(
    reason="Production deployment of approved changes",
    user_identity="operator@example.com",
)
# success=True, message="Live mode enabled: Production deployment..."
```

### LIVE → DRY_RUN (Disable)

**Method**: `disable_live(reason: str, user_identity: str, automatic: bool) → (bool, str)`

**Requirements**:
- Explicit reason (why execution is being blocked)
- User identity (who is disabling, or "system" for automatic)
- Automatic flag (True for security revert, False for manual)

**Manual Disable**:
```python
success, message = gate.disable_live(
    reason="Task complete, returning to safe mode",
    user_identity="operator@example.com",
    automatic=False,
)
```

**Automatic Disable** (Security Revert):
```python
# Triggered by check_security_and_revert_if_needed()
if kernel.get_security_state() in [SecurityState.COMPROMISED, SecurityState.LOCKDOWN]:
    success, message = gate.disable_live(
        reason=f"Automatic revert: Security state is {state.value}",
        user_identity="system",
        automatic=True,
    )
```

**Audit Trail**:
- Transition recorded immutably
- Timestamp of disable
- Reason for disabling
- User who disabled (or "system")
- Automatic flag (distinguishes manual vs auto-revert)

## Components

### LiveModeState (Enum)

```python
class LiveModeState(Enum):
    """
    Live mode gate states.
    
    DRY_RUN: Execution blocked (safe default)
    LIVE: Execution enabled (dangerous)
    """
    DRY_RUN = "DRY_RUN"
    LIVE = "LIVE"
```

### LiveModeTransition (Immutable Record)

```python
@dataclass(frozen=True)
class LiveModeTransition:
    """
    Immutable record of a live mode gate transition.
    
    Records:
    - When the transition occurred
    - What states changed
    - Why the transition occurred
    - Who initiated the transition
    - Whether it was automatic (security revert)
    """
    timestamp: datetime
    from_state: LiveModeState
    to_state: LiveModeState
    reason: str
    user_identity: str  # "system" for automatic
    automatic: bool  # True for security revert, False for manual
```

### LiveModeGate (Controller)

```python
class LiveModeGate:
    """
    Explicit execution authority gate.
    
    Default: DRY_RUN (fail-closed)
    Transitions: Explicit enable/disable with audit trail
    Security: Auto-revert to DRY_RUN on COMPROMISED/LOCKDOWN
    """
    
    def __init__(self, kernel: Any = None):
        """
        Initialize gate in DRY_RUN state.
        
        Args:
            kernel: Artemis kernel (for security state monitoring)
        """
        self._state = LiveModeState.DRY_RUN  # Fail-closed
        self._kernel = kernel
        self._transition_history: List[LiveModeTransition] = []
    
    def enable_live(self, reason: str, user_identity: str) → (bool, str):
        """Enable execution (DRY_RUN → LIVE)."""
        
    def disable_live(self, reason: str, user_identity: str, automatic: bool) → (bool, str):
        """Disable execution (LIVE → DRY_RUN)."""
    
    def check_security_and_revert_if_needed(self) → bool:
        """Auto-revert to DRY_RUN if security degraded."""
    
    def get_state(self) → LiveModeState:
        """Get current state."""
    
    def is_live(self) → bool:
        """Check if execution is enabled."""
    
    def is_dry_run(self) → bool:
        """Check if execution is blocked."""
    
    def get_transition_history(self) → Tuple[LiveModeTransition, ...]:
        """Get immutable transition history."""
```

### LiveModeGateValidator (Validator)

```python
class LiveModeGateValidator:
    """
    Validates that gate allows execution.
    
    Enforces:
    - Gate must exist
    - Gate must be in LIVE state
    - No execution allowed in DRY_RUN
    """
    
    @staticmethod
    def can_execute(gate: LiveModeGate) → Tuple[bool, str]:
        """
        Check if execution is allowed.
        
        Args:
            gate: LiveModeGate instance
        
        Returns:
            (allowed: bool, reason: str)
        """
        if not gate:
            return False, "No live mode gate configured"
        
        if gate.is_dry_run():
            return False, "Live mode gate is in DRY_RUN state (execution blocked)"
        
        return True, "Live mode gate is LIVE (execution enabled)"
```

## Integration

### ApprovalExecutor Integration

The Live Mode Gate is checked at the **very start** of `ApprovalExecutor.execute()`, before any other validation:

```python
def execute(self, execution_request: ExecutionRequest) → Tuple[bool, str, Dict]:
    """
    Execute an approved plan.
    
    Validation order:
    0. Live mode gate check (HARD BOUNDARY)  ← NEW
    1. One-shot guarantee
    2. Approval handshake validation
    3. Stage4 orchestration
    """
    execution_id = execution_request.execution_id
    
    try:
        # Step 0: Check live mode gate (HARD BOUNDARY)
        if self._live_mode_gate:
            from artemis.live_mode_gate import LiveModeGateValidator
            
            can_execute, gate_reason = LiveModeGateValidator.can_execute(self._live_mode_gate)
            
            if not can_execute:
                self._audit_trail.record(
                    execution_id,
                    "live_mode_gate_blocked",
                    {"reason": gate_reason},
                    error_message=gate_reason,
                )
                return False, f"EXECUTION BLOCKED: {gate_reason}", {}
            
            self._audit_trail.record(
                execution_id,
                "live_mode_gate_passed",
                {"gate_state": self._live_mode_gate.get_state().value},
            )
        
        # Step 1: Check one-shot guarantee
        # ... (existing validation continues)
```

**Key Points**:
- Gate check happens **before** one-shot check
- Gate check happens **before** handshake validation
- Gate check is **audited** (both pass and block)
- Gate check returns immediately on block (fail-fast)

### Hestia UI Integration

Hestia provides user-friendly methods for gate control:

```python
class HestiaAgent:
    """Hestia agent with live mode gate UX."""
    
    def display_live_mode_status(self, live_mode_gate: Any) → str:
        """
        Display current gate status.
        
        Shows:
        - Current state (DRY_RUN or LIVE)
        - What this means for execution
        - Recent transition history
        """
    
    def explain_live_mode_consequences(self) → str:
        """
        Explain what enabling live mode means.
        
        Provides clear explanation of:
        - What DRY_RUN means (safe)
        - What LIVE means (dangerous)
        - Security implications
        - Recommended practices
        """
    
    def enable_live_mode(
        self,
        live_mode_gate: Any,
        reason: str,
        user_identity: str,
    ) → Tuple[bool, str]:
        """
        Enable live mode (allow execution).
        
        Wraps gate.enable_live() with user-friendly feedback.
        """
    
    def disable_live_mode(
        self,
        live_mode_gate: Any,
        reason: str,
        user_identity: str,
    ) → Tuple[bool, str]:
        """
        Disable live mode (block execution).
        
        Wraps gate.disable_live() with user-friendly feedback.
        """
```

## Security Integration

### Auto-Revert Mechanism

The gate automatically reverts to DRY_RUN when security degrades:

```python
def check_security_and_revert_if_needed(self) → bool:
    """
    Check security state and revert to DRY_RUN if needed.
    
    Triggers:
    - SecurityState.COMPROMISED
    - SecurityState.LOCKDOWN
    
    Returns:
        True if reverted, False if no action needed
    """
    if not self._kernel:
        return False
    
    security_state = self._kernel.get_security_state()
    
    from artemis.boundary import SecurityState
    if security_state in [SecurityState.COMPROMISED, SecurityState.LOCKDOWN]:
        if self._state == LiveModeState.LIVE:
            # Auto-revert to DRY_RUN
            self.disable_live(
                reason=f"Automatic revert: Security state is {security_state.value}",
                user_identity="system",
                automatic=True,
            )
            return True
    
    return False
```

**When to Check**:
- Before `enable_live()` (prevents enable during incident)
- Before execution (prevents execution if security degraded)
- Periodically (optional, for proactive monitoring)

**Audit Trail**:
- Auto-revert transitions are marked with `automatic=True`
- Reason includes security state that triggered revert
- User identity is "system" (not a human)

## Audit Trail

Every transition is recorded immutably:

```python
# Example transition history
transitions = gate.get_transition_history()

for transition in transitions:
    print(f"{transition.timestamp}: {transition.from_state.value} → {transition.to_state.value}")
    print(f"  Reason: {transition.reason}")
    print(f"  User: {transition.user_identity}")
    print(f"  Automatic: {transition.automatic}")
```

**Output**:
```
2024-01-15 10:30:00: DRY_RUN → LIVE
  Reason: Production deployment of approved changes
  User: operator@example.com
  Automatic: False

2024-01-15 10:45:00: LIVE → DRY_RUN
  Reason: Automatic revert: Security state is COMPROMISED
  User: system
  Automatic: True

2024-01-15 11:00:00: DRY_RUN → LIVE
  Reason: Security recovered, resuming execution
  User: admin@example.com
  Automatic: False
```

## Design Principles

### Fail-Closed

- **Default state**: DRY_RUN (execution blocked)
- **Enable**: Explicit, requires reason and user
- **Disable**: Automatic on security degradation
- **Philosophy**: Safe by default, dangerous by explicit choice

### Explicit Over Implicit

- No automatic enable
- No timers or timeouts
- No background state changes
- Every transition requires human intent (except security revert)

### Auditable

- All transitions recorded immutably
- Complete history preserved
- Timestamp, states, reason, user for every change
- Automatic flag distinguishes manual vs security revert

### Stateless

- No persistence across restarts
- No configuration files
- No saved state
- Every session starts in DRY_RUN

### Orthogonal

- Gate is independent of approval
- Approval can succeed while gate blocks execution
- Gate does not affect plan compilation
- Gate only controls execution authority

## Usage Patterns

### Pattern 1: Development Testing

```python
# Create gate (defaults to DRY_RUN)
gate = LiveModeGate(kernel=kernel)

# Test the governance loop without execution
executor = ApprovalExecutor(live_mode_gate=gate, ...)
success, message, results = executor.execute(request)
# Execution blocked, validation successful
```

### Pattern 2: Production Execution

```python
# Create gate
gate = LiveModeGate(kernel=kernel)

# Display status and consequences
print(agent.display_live_mode_status(gate))
print(agent.explain_live_mode_consequences())

# Enable live mode
success, message = agent.enable_live_mode(
    gate,
    reason="Deploying approved database migration",
    user_identity="dba@example.com",
)

if not success:
    print(f"ERROR: {message}")
    return

# Execute (gate is now LIVE)
executor = ApprovalExecutor(live_mode_gate=gate, ...)
success, message, results = executor.execute(request)

# Disable live mode after execution
agent.disable_live_mode(
    gate,
    reason="Migration complete, returning to safe mode",
    user_identity="dba@example.com",
)
```

### Pattern 3: Security Response

```python
# Gate is LIVE, execution is happening
gate = LiveModeGate(kernel=kernel)
gate.enable_live("Active maintenance", "ops@example.com")

# Security incident detected
kernel._security_state = SecurityState.COMPROMISED

# Check security (auto-revert)
reverted = gate.check_security_and_revert_if_needed()
# reverted=True, gate is now DRY_RUN

# Execution attempts now blocked
success, message, results = executor.execute(request)
# success=False, message="EXECUTION BLOCKED: Live mode gate is in DRY_RUN state"

# Review audit trail
transitions = gate.get_transition_history()
# Last transition shows automatic=True, reason="Automatic revert: Security state is COMPROMISED"
```

## Constraints

### No Automation

- No automatic enable (always requires human)
- No scheduled transitions
- No time-based auto-disable
- Only exception: security auto-revert

### No Persistence

- No state saved to disk
- No configuration files
- No environment variables
- Every restart begins in DRY_RUN

### No Background Execution

- No daemon processes
- No async state changes
- No event-driven transitions
- All transitions are synchronous

### Standard Library Only

- No external dependencies
- Pure Python implementation
- No database required
- No network calls

## Anti-Patterns

### ❌ Auto-Enable on Approval

```python
# WRONG: Do not auto-enable when plan is approved
def approve_plan(plan):
    approved = user_confirms(plan)
    if approved:
        gate.enable_live("Plan approved", user)  # ❌ BAD
        executor.execute(request)
```

**Why**: Couples approval with execution, defeats the purpose of the gate.

**Right**: Keep approval and execution separate. Enable gate explicitly when ready to execute.

### ❌ Persistent LIVE State

```python
# WRONG: Do not save gate state to file
def shutdown():
    with open("gate_state.txt", "w") as f:
        f.write(gate.get_state().value)  # ❌ BAD

def startup():
    with open("gate_state.txt", "r") as f:
        state = f.read()
        if state == "LIVE":
            gate.enable_live("Restored state", "system")  # ❌ BAD
```

**Why**: Gate should always start in DRY_RUN. Persistent LIVE state removes the fail-closed guarantee.

**Right**: Always start in DRY_RUN. Require explicit enable every session.

### ❌ Timed Auto-Disable

```python
# WRONG: Do not auto-disable after timeout
def enable_with_timeout(duration_seconds):
    gate.enable_live("Timed execution", user)
    time.sleep(duration_seconds)
    gate.disable_live("Timeout expired", "system", automatic=True)  # ❌ BAD
```

**Why**: Introduces background state changes, reduces human control, adds complexity.

**Right**: Require explicit disable. Let humans decide when to revert.

### ❌ Gate Without Audit

```python
# WRONG: Do not bypass audit trail
def quick_enable():
    gate._state = LiveModeState.LIVE  # ❌ BAD: No audit
```

**Why**: All transitions must be audited. Direct state mutation defeats the purpose of the gate.

**Right**: Always use `enable_live()` and `disable_live()` methods.

## Implementation Notes

### Thread Safety

Current implementation is **not thread-safe**. If multiple threads access the gate:

1. Use external locking (e.g., `threading.Lock`)
2. Or ensure single-threaded access
3. Or implement internal locking (future enhancement)

### Error Handling

All gate methods return `(success: bool, message: str)` tuples:

```python
success, message = gate.enable_live(reason, user)

if not success:
    # Handle failure (e.g., security state not operational)
    print(f"ERROR: {message}")
else:
    # Proceed with execution
    print(f"SUCCESS: {message}")
```

### Validation

Gate methods validate inputs:

```python
# Empty reason
success, message = gate.enable_live("", user)
# success=False, message="Reason cannot be empty"

# Empty user
success, message = gate.enable_live(reason, "")
# success=False, message="User identity cannot be empty"

# Security state not operational
success, message = gate.enable_live(reason, user)
# success=False, message="Cannot enable LIVE: Security state is COMPROMISED"
```

## Testing

### Unit Tests

```python
def test_default_state_is_dry_run():
    gate = LiveModeGate()
    assert gate.get_state() == LiveModeState.DRY_RUN
    assert gate.is_dry_run()
    assert not gate.is_live()

def test_enable_live_requires_reason():
    gate = LiveModeGate()
    success, message = gate.enable_live("", "user")
    assert not success
    assert "Reason" in message

def test_auto_revert_on_compromised():
    kernel = Kernel()
    gate = LiveModeGate(kernel=kernel)
    gate.enable_live("Test", "user")
    
    kernel._security_state = SecurityState.COMPROMISED
    reverted = gate.check_security_and_revert_if_needed()
    
    assert reverted
    assert gate.is_dry_run()
```

### Integration Tests

```python
def test_executor_blocks_when_dry_run():
    gate = LiveModeGate()  # DRY_RUN by default
    executor = ApprovalExecutor(live_mode_gate=gate)
    
    success, message, results = executor.execute(request)
    
    assert not success
    assert "DRY_RUN" in message

def test_executor_executes_when_live():
    gate = LiveModeGate()
    gate.enable_live("Test execution", "tester")
    executor = ApprovalExecutor(live_mode_gate=gate)
    
    success, message, results = executor.execute(request)
    
    assert success  # Execution proceeds (if other validation passes)
```

## Future Enhancements

### Possible (Not Implemented)

1. **Rate Limiting**: Limit how often enable_live() can be called
2. **Role-Based Access**: Require specific roles to enable LIVE
3. **Multi-Gate**: Separate gates for different execution types
4. **Metrics**: Count transitions, time in each state
5. **Notifications**: Alert on auto-revert or suspicious patterns

### Not Planned (By Design)

1. **Persistence**: Gate always starts in DRY_RUN
2. **Automation**: No automatic enable, no timers
3. **Remote Control**: No API for remote enable
4. **Background Execution**: No async transitions

## Summary

The Live Mode Gate is the **final authority boundary** in the HEARTH execution path:

1. **LLM reasoning** → Plan compilation
2. **Human approval** → Approval decision
3. **Gate check** → **THIS IS THE GATE** ← Execution authority
4. **Execution** → Only if gate is LIVE

**Default**: DRY_RUN (fail-closed)
**Enable**: Explicit, with reason and user identity
**Disable**: Manual or automatic (security revert)
**Audit**: Complete, immutable transition history
**Philosophy**: Execution is opt-in, explicit, and audited

The gate ensures that execution never happens by accident, always requires human intent, and automatically reverts to safe mode during security incidents.
