# ARES Phase 0: Quick Reference

**Status**: ✅ **COMPLETE** (12/12 tests, 9/9 examples)

---

## TL;DR

**ARES** = Active Defense & Deterrence

**Purpose**: Detect threats, collect evidence, report to Artemis

**Authority**: Artemis decides. ARES only reports.

**Public API**:
```python
from ares import report_to_artemis
report = report_to_artemis()
```

**That's it.**

---

## What ARES Does

| Do | Don't |
|---|---|
| Observe passively | Execute |
| Detect patterns | Approve plans |
| Report findings | Modify plans |
| Record evidence | Kill system |
| Provide honeypots | Override Artemis |
| Add deceptive latency | Persist data |
| Build profiles | Access network |
| Emit signals | Escalate automatically |

---

## Core Modules

```python
# Detection
from ares.sensors import get_sensor
signal = sensor.observe_boundary_probing(...)

# Deception
from ares.honeypots import get_factory
factory.create_fake_credential("id")

# Recording
from ares.state import get_store, update_store
store = get_store().add_signal(signal)

# Reporting
from ares import report_to_artemis
report = report_to_artemis()
```

---

## Signal Types (8)

```python
SignalType.EXCESSIVE_PROBING              # 5+ boundary attempts
SignalType.INVALID_PLAN_ATTEMPTS          # 3+ malformed plans
SignalType.RAPID_REJECTIONS               # 5+ rejections/window
SignalType.SUSPICIOUS_TIMING              # >5x deviation
SignalType.CAPABILITY_ENUMERATION         # 10+ queries
SignalType.CREDENTIAL_SCAN                # 5+ credential attempts
SignalType.HONEYPOT_TRIGGER               # Honeypot accessed 3+
SignalType.STATE_MANIPULATION             # State change attempt
```

---

## Confidence Levels (3)

```python
ConfidenceLevel.LOW       # Possible false positive
ConfidenceLevel.MEDIUM    # Likely genuine
ConfidenceLevel.HIGH      # Strong evidence
```

---

## Quick API Reference

### Sensors (Passive Detection)

```python
from ares.sensors import get_sensor

sensor = get_sensor()

# Returns Signal if threshold exceeded, None otherwise
signal = sensor.observe_boundary_probing(subsystem, attempt_count, description)
signal = sensor.observe_invalid_plan_attempts(plan_count, time_window_sec, description)
signal = sensor.observe_rapid_rejections(rejection_count, time_window_sec, policy)
signal = sensor.observe_timing_anomaly(expected_ms, actual_ms, operation)
signal = sensor.observe_capability_enumeration(subsystem, query_count, unique_capabilities)
signal = sensor.observe_credential_scan(attempt_count, description)
```

### Honeypots (Deception)

```python
from ares.honeypots import get_factory

factory = get_factory()

# Create fake endpoints (never leak real data)
cred_hp = factory.create_fake_credential("honey_1")
cap_hp = factory.create_fake_capability("honey_2")
adapt_hp = factory.create_fake_adapter("honey_3")

# Access returns: (fake_data, record, optional_signal)
fake_cred, record, signal = cred_hp.get_credential("subsystem")
```

### State (Ephemeral Storage)

```python
from ares.state import get_store, update_store, clear_store

# Get current store
store = get_store()

# Add signal (immutable, returns new store)
store = store.add_signal(signal)

# Update global store
update_store(store)

# Clear (testing only)
clear_store()
```

### Deception (Tarpitting)

```python
from ares.deception import get_engine

engine = get_engine()

# Add bounded latency (MAX 5000ms)
latency, record, signal = engine.add_bounded_latency(2000, "subsystem")

# Return dummy response
dummy, record, signal = engine.benign_dummy_response("list", "subsystem")

# Execute no-op (returns success)
result, record, signal = engine.no_op_execution_path("operation", "subsystem")

# Bounded loop (MAX 100 iterations)
results, record, signal = engine.repeated_no_op_loop(200, "subsystem")
```

### Timeline (Correlation)

```python
from ares.timeline import get_timeline, clear_timeline

timeline = get_timeline()

# Add events
event = timeline.add_event("type", "source", {"data": {...}})
event = timeline.add_signal_event(signal)

# Correlate
timeline.correlate_events(event1_id, event2_id, "reason")

# Find patterns
pattern = timeline.find_pattern("type", "source", count=3, window_seconds=300)

# Get summary
summary = timeline.get_timeline_summary(last_n=10)
```

### Profiling (Behavioral Analysis)

```python
from ares.profiler import get_factory

factory = get_factory()

# Get or create profiler
profiler = factory.get_or_create_profiler("subsystem")

# Record actions
profiler.record_action("action_1")
profiler.record_action("action_2")

# Generate fingerprint
fp = profiler.fingerprint("scanning")

# Get risk assessment
risk_score, signal = profiler.get_risk_assessment()
```

### Reporting (Artemis Interface)

```python
from ares import report_to_artemis

# Get forensic report
report = report_to_artemis()

# Properties
report.report_id                    # Unique ID
report.timestamp                    # UTC timestamp
report.signals_count                # Number of signals
report.events_count                 # Number of events
report.confidence_assessment        # LOW/MEDIUM/HIGH
report.signal_summary               # List of signals
report.timeline_summary             # List of events
report.recommended_escalation       # ADVISORY (none/investigation/monitoring/urgent)
report.risk_factors                 # List of risk descriptions
report.report_hash                  # Integrity hash

# Verify integrity
assert report.verify_integrity()

# Serialize
report_dict = report.to_dict()
```

---

## Usage Patterns

### Pattern 1: Detect & Report

```python
from ares.sensors import get_sensor
from ares.state import get_store, update_store
from ares import report_to_artemis

# Detect
sensor = get_sensor()
signal = sensor.observe_boundary_probing(subsystem, 6, "admin endpoint")

if signal:
    # Store
    store = get_store().add_signal(signal)
    update_store(store)
    
    # Report
    report = report_to_artemis()
    print(f"Escalation: {report.recommended_escalation}")
```

### Pattern 2: Honeypot Integration

```python
from ares.honeypots import get_factory
from ares.state import get_store, update_store

factory = get_factory()
hp = factory.create_fake_credential("admin_v2")

# Attacker tries
fake_cred, record, signal = hp.get_credential("attacker")

if signal:
    # Third access triggers signal
    store = get_store().add_signal(signal)
    update_store(store)
```

### Pattern 3: Timeline Reconstruction

```python
from ares.timeline import get_timeline

timeline = get_timeline()

# Record all events
timeline.add_signal_event(signal1)
timeline.add_signal_event(signal2)
timeline.add_sensor_event(sensor_event)

# Correlate
timeline.correlate_events(sig1_id, sig2_id, "same attack")

# Find pattern
if timeline.find_pattern("signal", "source", 3, 300):
    print("Attack pattern detected")
```

---

## Testing

### Run All Tests

```bash
python verify_ares_phase0.py
```

**Expected**: 12/12 PASS

### Run Examples

```bash
python run_ares_examples.py
```

**Expected**: 9/9 PASS

### Verify Constraints

Key tests verify:
- ✓ No execution authority
- ✓ No persistence
- ✓ No network
- ✓ No threads
- ✓ Immutable records
- ✓ Bounded deception
- ✓ Deterministic behavior
- ✓ Fail-closed

---

## Integration Checklist

- [ ] Import ARES modules
- [ ] Create sensors in detector
- [ ] Create honeypots in capability manager
- [ ] Store signals in state
- [ ] Call report_to_artemis() before escalation
- [ ] Verify Artemis makes final decision
- [ ] Test that ARES doesn't execute
- [ ] Run verification tests
- [ ] Document integration point

---

## Common Issues

### Issue: Import fails
**Solution**: Ensure `ares/` directory exists with all 9 modules

### Issue: Signal not recorded
**Solution**: Remember to call `update_store()` after `add_signal()`

### Issue: Honeypot not triggering signal
**Solution**: Signals only trigger on 3+ accesses

### Issue: Latency not applied
**Solution**: Actually sleep occurs, use `time.sleep()` check

### Issue: Report empty
**Solution**: Add signals to store first with `update_store()`

---

## Constraints Summary

| Constraint | Status |
|---|---|
| NO execution authority | ✅ Enforced |
| NO persistence | ✅ Ephemeral only |
| NO network | ✅ No imports |
| NO threads | ✅ Single-threaded |
| NO external deps | ✅ Stdlib only |
| Immutable records | ✅ Frozen dataclasses |
| Bounded deception | ✅ MAX_LATENCY_MS=5000 |
| Deterministic | ✅ No ML |
| Fail-closed | ✅ Default NONE |
| Advisory escalation | ✅ Artemis decides |

---

## Authority Model (CRITICAL)

```
Artemis = Law
ARES = War

Artemis:
✓ Makes decisions
✓ Escalates threats
✓ Freezes credentials
✓ Initiates lockdown
✓ Presses kill switch

ARES:
✓ Observes
✓ Reports
✓ Suggests (advisory only)
✗ Does NOT decide
✗ Does NOT escalate
✗ Does NOT kill
```

---

## File Structure

```
ares/                              # Security subsystem
├── __init__.py                    # Exports: report_to_artemis
├── state.py                       # Ephemeral storage
├── signals.py                     # Signal definitions
├── sensors.py                     # Passive detection
├── honeypots.py                   # Fake endpoints
├── deception.py                   # Deceptive responses
├── profiler.py                    # Behavioral analysis
├── timeline.py                    # Event correlation
├── report.py                      # Forensic reports
└── interface.py                   # Artemis interface

verify_ares_phase0.py              # Verification tests (12/12 PASS)
run_ares_examples.py               # Working examples (9/9 PASS)
ARES_PHASE0_SPECIFICATION.md       # Full spec
ARES_QUICK_REFERENCE.md            # This file
```

---

## Performance

| Operation | Time | Memory |
|---|---|---|
| Signal creation | <1ms | 100B |
| Sensor detection | <1ms | 0B |
| Honeypot access | <1ms | 50B |
| Deception latency | 2000ms+ | 0B |
| Timeline add | <1ms | 200B |
| Report generation | <5ms | 500B+ |

---

## Status

✅ **PHASE 0 COMPLETE**

- 12/12 verification tests pass
- 9/9 working examples pass
- All constraints enforced
- Production ready for integration

**Ready for**: Stage 4 integration, Artemis hookup, security team review

---

## Next Steps

1. **Integration** (This sprint)
   - Wire sensors into detector
   - Wire honeypots into capability manager
   - Wire report into Artemis escalation

2. **Testing** (Next sprint)
   - Integration tests
   - Attack scenario testing
   - Operator acceptance testing

3. **Monitoring** (Ongoing)
   - Track signal patterns
   - Measure operator response
   - Refine thresholds

---

## Support

- Full spec: [ARES_PHASE0_SPECIFICATION.md](ARES_PHASE0_SPECIFICATION.md)
- Tests: `python verify_ares_phase0.py`
- Examples: `python run_ares_examples.py`
- Code: [ares/](ares/)

---

**ARES Phase 0: Detect. Report. Artemis decides.**
