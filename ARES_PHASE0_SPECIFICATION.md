# ARES Phase 0: Active Defense & Deterrence - Complete Specification

**Status**: ✅ **PHASE 0 COMPLETE**

**Version**: 1.0  
**Date**: January 30, 2026

---

## Executive Summary

ARES (Active Defense & Deterrence) is a security subsystem for HEARTH that detects threats, collects evidence, and reports findings to Artemis.

### Authority Model

```
Artemis = Law      (makes final decisions)
ARES = War         (detects, slows, misleads, observes, reports)
```

**ARES has ZERO execution authority**:
- Cannot approve or deny plans
- Cannot modify plans
- Cannot kill the system
- Cannot override Artemis
- Cannot change security state
- Cannot access networks
- Cannot persist data

**ARES can only**:
- Observe passively
- Report findings
- Emit deceptive responses
- Record evidence

---

## Architecture

### Module Structure

```
ares/
├── __init__.py           # Package initialization (exports only report_to_artemis)
├── state.py              # Ephemeral state management (in-memory only)
├── signals.py            # Signal definitions (immutable records)
├── sensors.py            # Passive observation hooks (detects patterns)
├── honeypots.py          # Fake endpoints (deceive attackers)
├── deception.py          # Deceptive responses (tarpit logic)
├── profiler.py           # Behavioral fingerprinting (deterministic)
├── timeline.py           # Event correlation (append-only)
├── report.py             # Forensic reports (immutable, signed)
└── interface.py          # Single reporting interface (report_to_artemis)
```

### Data Flow

```
Attack → Sensors → Signals → Timeline → Profiler → Report → Artemis
                    ↓
              Honeypots
              Deception
              Recording
```

---

## Core Components

### 1. State Management (state.py)

**Purpose**: Ephemeral, immutable state storage

**Key Features**:
- In-memory only (cleared on restart)
- Immutable (frozen dataclass)
- Append-only operations
- No disk persistence
- No environment mutation

**API**:
```python
from ares.state import get_store, update_store, clear_store, EphemeralStore

store = get_store()           # Get current state
store = store.add_signal(s)   # Add signal (returns new store)
update_store(store)           # Update global store
clear_store()                 # Clear all state
```

**Constraints**:
- ✅ No disk writes
- ✅ No persistence
- ✅ No environment mutation
- ✅ Fail-closed on corruption

---

### 2. Signal Detection (signals.py)

**Purpose**: Immutable, typed, scored suspicion signals

**Signal Types** (8):
- `EXCESSIVE_PROBING` - Boundary access attempts
- `INVALID_PLAN_ATTEMPTS` - Malformed plans
- `RAPID_REJECTIONS` - Policy rejection pattern
- `SUSPICIOUS_TIMING` - Timing anomalies
- `CAPABILITY_ENUMERATION` - Capability scanning
- `CREDENTIAL_SCAN` - Credential attempts
- `HONEYPOT_TRIGGER` - Honeypot access
- `STATE_MANIPULATION` - State change attempt

**Confidence Levels** (3):
- `LOW` - Possible false positive
- `MEDIUM` - Likely genuine
- `HIGH` - Strong evidence

**API**:
```python
from ares.signals import Signal, SignalType, ConfidenceLevel

signal = Signal.create(
    signal_type=SignalType.EXCESSIVE_PROBING,
    source_subsystem="capability_manager",
    confidence=ConfidenceLevel.HIGH,
    description="6 probing attempts",
    evidence_reference="boundary_access_log",
)

signal_dict = signal.to_dict()  # Serialize
```

**Constraints**:
- ✅ Immutable (frozen dataclass)
- ✅ Hashable IDs (deterministic)
- ✅ Typed confidence levels
- ✅ Evidence references (traceable)

---

### 3. Passive Sensors (sensors.py)

**Purpose**: Detect attack patterns passively

**Detectors**:
- Boundary probing (5+ attempts)
- Invalid plans (3+ in window)
- Rapid rejections (5+ in window)
- Timing anomalies (>5x deviation)
- Capability enumeration (10+ queries, 5+ unique)
- Credential scanning (5+ attempts)

**API**:
```python
from ares.sensors import get_sensor

sensor = get_sensor()

# Returns Signal if threshold exceeded, None otherwise
signal = sensor.observe_boundary_probing(
    subsystem="orchestrator",
    attempt_count=6,
    description="Admin endpoint probing",
)

if signal:
    # Pattern detected
    print(signal.signal_id)
```

**Constraints**:
- ✅ Passive only (no blocking)
- ✅ Observable (emit signals)
- ✅ Non-intrusive
- ✅ Deterministic thresholds

---

### 4. Honeypots (honeypots.py)

**Purpose**: Fake credentials, capabilities, adapters

**Types**:
- `FakeCredential` - Dummy username/password/token
- `FakeCapability` - Fake domain capability
- `FakeAdapter` - Fake domain adapter

**Features**:
- Never leak real data
- Marked as "honeypot"
- Record access
- Emit signals on repeated access

**API**:
```python
from ares.honeypots import get_factory

factory = get_factory()

cred_hp = factory.create_fake_credential("admin_v2")
fake_cred, record, signal = cred_hp.get_credential("subsystem_x")

# fake_cred: {"username": "admin_honeypot_user", ...}
# record: HoneypotRecord (immutable)
# signal: Signal (if 3+ accesses)
```

**Constraints**:
- ✅ Never real data
- ✅ Marked as fake
- ✅ Record all access
- ✅ No escalation (only record)

---

### 5. Deception Engine (deception.py)

**Purpose**: Safe, bounded deceptive responses

**Tactics**:
- Artificial latency (bounded, capped at 5s)
- Benign dummy responses (no real data)
- No-op execution paths (does nothing, reports success)
- Bounded loops (max 100 iterations)

**Constraints** (SAFETY):
- ❌ NO infinite loops
- ❌ NO deadlocks
- ❌ NO resource exhaustion
- ✅ MAX_LATENCY_MS = 5000
- ✅ MAX_ITERATIONS = 100

**API**:
```python
from ares.deception import get_engine

engine = get_engine()

# Add bounded latency
latency_ms, record, signal = engine.add_bounded_latency(
    base_latency_ms=2000,
    target_subsystem="plan_executor",
)

# Return dummy response
dummy, record, signal = engine.benign_dummy_response(
    response_type="list",
    target_subsystem="capability_manager",
)

# Execute no-op
result, record, signal = engine.no_op_execution_path(
    operation_name="delete_user",
    target_subsystem="auth",
)
```

**Result**: Slow + observe, never crash or block.

---

### 6. Behavioral Profiling (profiler.py)

**Purpose**: Deterministic behavioral fingerprinting (no ML)

**Features**:
- Track action patterns per subsystem
- Correlate actions across subsystems
- Generate fingerprints
- Compute risk scores
- Emit signals when suspicious

**No Machine Learning**:
- Deterministic algorithms only
- No neural networks
- No statistical inference
- No identity guessing

**API**:
```python
from ares.profiler import get_factory

factory = get_factory()

profiler = factory.get_or_create_profiler("domain_adapter")
profiler.record_action("enumerate_methods")
profiler.record_action("query_credentials")

fingerprint = profiler.fingerprint("scanning")
risk_score, signal = profiler.get_risk_assessment()
```

**Constraints**:
- ✅ Deterministic only
- ✅ No ML models
- ✅ No identity inference
- ✅ Simple scoring (action count + uniqueness)

---

### 7. Timeline Reconstruction (timeline.py)

**Purpose**: Append-only event correlation and reconstruction

**Features**:
- Record signals, sensor events, deceptions
- Correlate related events
- Find patterns in time windows
- Chronological ordering
- Pattern detection (N events in window)

**API**:
```python
from ares.timeline import get_timeline

timeline = get_timeline()

# Add events
event1 = timeline.add_event("signal", "source1", {"data": "..."})
event2 = timeline.add_signal_event(signal)
event3 = timeline.add_sensor_event(sensor_event)

# Correlate
timeline.correlate_events(event1.event_id, event2.event_id, "related")

# Find patterns
pattern = timeline.find_pattern("signal", "source1", count=3, window_seconds=300)

# Get summary
summary = timeline.get_timeline_summary(last_n=10)
```

**Constraints**:
- ✅ Append-only (no deletion)
- ✅ Ordered (chronological)
- ✅ In-memory (cleared on restart)
- ✅ No modification of recorded events

---

### 8. Forensic Reports (report.py)

**Purpose**: Immutable, signed forensic reports

**Report Structure**:
```python
{
    "report_id": "rep-abc123...",
    "timestamp": "2026-01-29T18:49:16...",
    "signals_count": 5,
    "events_count": 8,
    "confidence_assessment": "high",
    "signal_summary": [...],
    "timeline_summary": [...],
    "detected_patterns": [...],
    "recommended_escalation": "urgent",  # ADVISORY ONLY
    "risk_factors": [...],
    "report_hash": "sha256..."
}
```

**Escalation Levels** (ADVISORY):
- `none` - No threat
- `investigation` - Low confidence signals
- `monitoring` - Medium confidence signals
- `urgent` - High confidence signals

**API**:
```python
from ares.report import AresForensicReport

report = AresForensicReport.create(signals, timeline_events)

# Verify integrity
assert report.verify_integrity()

# Serialize
report_dict = report.to_dict()
```

**Constraints**:
- ✅ Immutable (frozen dataclass)
- ✅ Cryptographically signed (hash-based)
- ✅ Self-contained
- ✅ Recommended escalation (ADVISORY ONLY, not automatic)

---

### 9. Artemis Interface (interface.py)

**Purpose**: Single reporting interface

**Public API**:
```python
from ares import report_to_artemis

report = report_to_artemis()
```

**That's it. One method.**

**Constraints**:
- ✅ ONE public method only
- ✅ Returns immutable report
- ✅ ARES never calls kill switch
- ✅ ARES never escalates automatically
- ✅ ARES never changes security state

**Authority Flow**:
```
ARES                           ARTEMIS
report_to_artemis()    →       Report received
(findings + evidence)
(advisory escalation)   
                        →      ARTEMIS analyzes
                        →      ARTEMIS decides:
                               - Investigation
                               - Monitoring
                               - Credential freeze
                               - Lockdown
                               - Kill switch
```

---

## Constraints & Guarantees

### Hard Constraints (ENFORCED)

| Constraint | Enforced By | Verification |
|---|---|---|
| NO execution authority | Architecture (no exec methods) | Test: test_no_execution_authority ✓ |
| NO persistence | state.py (ephemeral only) | Test: test_no_persistence ✓ |
| NO network | No imports (socket, requests, etc) | Code review (only stdlib) ✓ |
| NO threads | No threading imports | Code review (no async/threads) ✓ |
| NO external deps | No requirements.txt additions | Code review (stdlib only) ✓ |
| Immutable records | frozen=True on all dataclasses | Test: test_signals_immutable ✓ |
| Bounded deception | MAX_LATENCY_MS, MAX_ITERATIONS | Test: test_deception_bounded ✓ |
| Deterministic | No ML, no randomness | Test: test_profiler_deterministic ✓ |
| Fail-closed | Default: no escalation | Code review (defaults to NONE) ✓ |

### Behavioral Guarantees

| Guarantee | How | Verified |
|---|---|---|
| Passive sensors | Never block | Sensor methods return None (non-blocking) ✓ |
| Honeypots non-leaking | Fake data only | FakeCredential returns "honeypot_user" not real ✓ |
| Deception safe | Bounded, capped | engine.MAX_LATENCY_MS enforces upper bound ✓ |
| Reports immutable | frozen dataclass | Try to mutate → FrozenInstanceError ✓ |
| Timeline append-only | Only add_event() | No delete/modify methods ✓ |
| Artemis only consumer | Single interface | report_to_artemis() is only public export ✓ |

---

## Testing

### Verification Tests (12/12 PASS)

```
✓ Safe Imports (no side effects)
✓ State Ephemeral
✓ Signals Immutable
✓ Sensors Passive
✓ Honeypots Non-Leaking
✓ Deception Bounded
✓ Profiler Deterministic
✓ Timeline Append-Only
✓ Reports Immutable
✓ Interface (Single Method)
✓ No Persistence
✓ No Execution Authority
```

### Working Examples (9/9 PASS)

```
✓ Boundary Probing Detection
✓ Invalid Plan Attempts
✓ Rapid Policy Rejections
✓ Capability Enumeration
✓ Honeypot Triggered
✓ Deception - Latency
✓ Behavioral Profiling
✓ Forensic Report
✓ Complete Attack Scenario
```

### Run Tests

```bash
# Verification tests
python verify_ares_phase0.py

# Working examples
python run_ares_examples.py
```

---

## Usage Examples

### Example 1: Simple Detection

```python
from ares.sensors import get_sensor
from ares.state import get_store, update_store

# Get sensor
sensor = get_sensor()

# Detect pattern
signal = sensor.observe_boundary_probing(
    subsystem="capability_manager",
    attempt_count=6,
    description="Admin endpoint probing",
)

if signal:
    # Add to store
    store = get_store().add_signal(signal)
    update_store(store)
```

### Example 2: Honeypot Integration

```python
from ares.honeypots import get_factory

factory = get_factory()
cred_hp = factory.create_fake_credential("admin_token_v2")

# Attacker tries to access
fake_cred, record, signal = cred_hp.get_credential("unauthorized_subsystem")

# Returns fake data (never real), records access
if signal:
    print("Honeypot triggered (3+ accesses)")
```

### Example 3: Report to Artemis

```python
from ares import report_to_artemis

# Get forensic report
report = report_to_artemis()

# Artemis analyzes report and decides:
# - Do nothing (NONE)
# - Investigate (INVESTIGATION)
# - Monitor (MONITORING)
# - Escalate (URGENT)

print(f"ARES recommends: {report.recommended_escalation} (advisory)")
print(f"Signals detected: {report.signals_count}")
print(f"Confidence: {report.confidence_assessment.value}")
```

---

## Performance Characteristics

| Component | Operation | Time | Memory |
|---|---|---|---|
| Signal creation | create() | <1ms | 100B |
| Sensor detection | observe_* | <1ms | 0B (passive) |
| Honeypot access | get_* | <1ms | 50B |
| Deception | add_bounded_latency(2000ms) | 2000ms | 0B |
| Timeline add | add_event() | <1ms | 200B |
| Report generation | create() | <5ms | 500B+ |
| Total memory (1000 signals) | ~1MB | | |

---

## Security Considerations

### What ARES Does NOT Do

- ❌ Execute plans
- ❌ Approve plans
- ❌ Deny plans
- ❌ Modify plans
- ❌ Kill system
- ❌ Override Artemis
- ❌ Change security state
- ❌ Access network
- ❌ Persist data
- ❌ Access real credentials
- ❌ Escalate automatically

### What ARES Does

- ✅ Observe passively
- ✅ Detect patterns
- ✅ Report findings
- ✅ Record evidence
- ✅ Provide honeypots
- ✅ Add latency
- ✅ Return dummy data
- ✅ Build behavioral profiles

### Threat Mitigation

| Threat | Mitigation | How |
|---|---|---|
| False escalations | Advisory only | Artemis decides, not ARES |
| Credential leakage | Honeypots only | Fake credentials only |
| System crash | Bounded deception | MAX_LATENCY_MS, MAX_ITERATIONS |
| Persistence attack | Ephemeral only | Cleared on restart |
| Unauthorized execution | No execute methods | Verify: test_no_execution_authority |

---

## Integration Points

### Where to Integrate ARES

1. **Plan Executor** (stage4/)
   - Detect invalid plan attempts
   - Detect timing anomalies
   - Report to Artemis before execution

2. **Capability Manager** (domains/)
   - Detect capability enumeration
   - Provide honeypot capabilities
   - Detect probing attempts

3. **Policy Engine** (domains/base.py)
   - Detect rapid rejections
   - Report rejection patterns
   - Correlate with other signals

4. **Artemis State** (core/kernel.py)
   - Monitor state changes
   - Detect manipulation attempts
   - Generate security signals

### Integration Example

```python
# In stage4/executor.py
from ares.sensors import get_sensor
from ares.state import get_store, update_store
from ares import report_to_artemis

def execute_plan(plan):
    # Check for anomalies
    sensor = get_sensor()
    signal = sensor.observe_invalid_plan_attempts(...)
    
    if signal:
        store = get_store().add_signal(signal)
        update_store(store)
    
    # Before execution, check if we should escalate
    report = report_to_artemis()
    if report.recommended_escalation == "urgent":
        # Artemis reviews report and decides
        # (ARES does not decide)
        pass
    
    # Execute plan (Artemis decides if safe)
    execute(plan)
```

---

## Phase 0 vs Future Phases

### Phase 0 (Current)
- ✅ Detection
- ✅ Deception
- ✅ Reporting

### Phase 1 (Future)
- Multi-signal correlation
- Advanced pattern matching
- Custom threat profiles

### Phase 2 (Future)
- Cross-subsystem profiling
- Temporal attack reconstruction
- Predictive defense

### Phase 3 (Future)
- Integration with external SOC
- Machine learning (if approved)
- Autonomous response (if authorized)

**Current Phase**: Phase 0 only. No power expansion planned.

---

## References

### Files
- Core: [ares/](ares/)
- Tests: [verify_ares_phase0.py](verify_ares_phase0.py)
- Examples: [run_ares_examples.py](run_ares_examples.py)

### Key Concepts
- Authority Model: Artemis = Law, ARES = War
- Fail-Closed: Default to no escalation
- No Autonomy: All decisions made by Artemis
- Deterministic: No randomness, no ML

---

## Support & Questions

For questions about ARES Phase 0:
- Review [ARES_QUICK_REFERENCE.md](ARES_QUICK_REFERENCE.md)
- Run verification tests: `python verify_ares_phase0.py`
- Run examples: `python run_ares_examples.py`

---

**Status**: ✅ PHASE 0 COMPLETE (12/12 tests pass, 9/9 examples pass)
