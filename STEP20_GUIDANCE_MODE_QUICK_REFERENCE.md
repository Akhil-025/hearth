# STEP 20: GUIDANCE MODE - QUICK REFERENCE

**TL;DR**: Advisory-only system. Surface insights, propose plans, never execute.

---

## Quick Start

```python
from artemis.guidance_mode import GuidanceObserver, TriggerType, ConfidenceLevel

# Create observer
observer = GuidanceObserver(kernel)

# Surface guidance
event = observer.surface_guidance(
    observation="5 plans in 2 hours",
    implication="Resource conflict",
    trigger_type=TriggerType.CALENDAR_CONGESTION,
    suggested_actions=["Review priorities", "Defer ops"],
    risk_notes=["Check for conflicts"],
    confidence_level=ConfidenceLevel.HIGH,
)

# Display to operator
print(hestia.display_guidance_event(event))

# Ask operator
response, reason = hestia.guidance_prompt(event)
```

---

## Components Table

| Component | Purpose | Mutability | Execution |
|-----------|---------|-----------|-----------|
| GuidanceEvent | Single piece of advice | Frozen | No |
| TriggerType | Advisory category | Enum | - |
| ConfidenceLevel | Certainty (low/med/high) | Enum | - |
| GuidanceObserver | Surfaces events | Stateful | No |
| PlanDraft | Proposed plan | Frozen | No |
| GuidancePlanner | Proposes drafts | Static | No |
| GuidanceSession | Interaction record | Frozen | No |

---

## Methods Reference

### GuidanceObserver

```python
# Create
observer = GuidanceObserver(kernel=None)

# Surface guidance (append-only)
event = observer.surface_guidance(
    observation: str,
    implication: str,
    trigger_type: TriggerType,
    suggested_actions: List[str],
    risk_notes: List[str],
    confidence_level: ConfidenceLevel,
    details: Optional[Dict] = None,
) → GuidanceEvent

# Get history (read-only)
history = observer.get_guidance_history() → Tuple[GuidanceEvent, ...]
```

### GuidancePlanner (Static)

```python
# Propose calendar optimization
draft = GuidancePlanner.propose_calendar_optimization(
    guidance_event: GuidanceEvent,
    scheduled_plans: List[Dict],
) → Optional[PlanDraft]

# Propose rejection analysis
draft = GuidancePlanner.propose_rejection_analysis(
    guidance_event: GuidanceEvent,
    rejection_history: List[Dict],
) → Optional[PlanDraft]

# Propose security checkpoint
draft = GuidancePlanner.propose_security_checkpoint(
    guidance_event: GuidanceEvent,
) → Optional[PlanDraft]
```

### Hestia UX

```python
# Display guidance
text = hestia.display_guidance_event(event: GuidanceEvent) → str

# Display draft
text = hestia.show_draft_plan(draft: PlanDraft) → str

# Ask operator
response, reason = hestia.guidance_prompt(
    event: GuidanceEvent,
    draft: Optional[PlanDraft] = None,
) → (str, str)
# response: "dismiss", "ask_more", "draft_plan"
```

---

## Trigger Types

| Trigger | What | When | Example |
|---------|------|------|---------|
| CALENDAR_CONGESTION | Multiple plans in short window | Plan scheduled | 5 plans in 2hrs |
| REPEATED_REJECTIONS | Same type rejected multiple times | After rejection | 3x constraint error |
| SECURITY_STATE_CHANGE | Artemis escalated/de-escalated | State changed | OPERATIONAL→WARNING |
| IRREVERSIBLE_ACTION_FREQUENCY | High frequency of irreversible ops | After execution | 8 in 24 hours |
| BUDGET_THRESHOLD_ALERT | Spending approaching limit | Periodic check | 85% of budget |

---

## Confidence Levels

| Level | Meaning | Use Case |
|-------|---------|----------|
| LOW | Weak signal, many unknowns | Speculative advice |
| MEDIUM | Reasonable confidence, uncertainty | Trend detection |
| HIGH | Strong signal, clear pattern | Obvious conditions |

---

## Security

### Guidance Disabled When:
- Artemis state >= COMPROMISED
- Artemis state = LOCKDOWN
- Any exception during security check (fail-open for advisory)

### Check Automatic:
```python
is_enabled = observer.check_security_state()
```

### Result When Disabled:
```python
# Event shows:
event.observation = "[GUIDANCE DISABLED - Security escalation]"
event.suggested_actions = []
```

---

## Constraints Verification

| Constraint | Status | How |
|-----------|--------|-----|
| No execution | ✓ | GuidancePlanner returns drafts only |
| No approvals | ✓ | guidance_prompt() only records choice |
| No background tasks | ✓ | All synchronous |
| No memory writes | ✓ | No persistence (volatile) |
| No retries | ✓ | Fail-once semantics |
| No scheduling | ✓ | No background jobs |
| No looping | ✓ | No polling loops |
| No intent inference | ✓ | Explicit triggers only |
| Standard lib only | ✓ | No external dependencies |
| Fail-closed | ✓ | Disabled by default on error |

---

## Common Patterns

### Pattern: Display Guidance Only
```python
observer = GuidanceObserver(kernel)
event = observer.surface_guidance(...)
print(hestia.display_guidance_event(event))
# Operator sees guidance, no action taken
```

### Pattern: Propose Draft
```python
planner = GuidancePlanner()
draft = planner.propose_calendar_optimization(event, plans)
if draft:
    print(hestia.show_draft_plan(draft))
    # Operator reviews (not executed)
```

### Pattern: Record Interaction
```python
response, reason = hestia.guidance_prompt(event, draft)
session = GuidanceSession.create(event, draft, response)
# Immutable record of what happened
```

---

## Anti-Patterns (DO NOT DO)

❌ **Auto-execute draft**: Drafts are not meant to be auto-executed
❌ **Persist guidance**: Events are volatile (memory only)
❌ **Ignore disabled state**: Check security before surfacing
❌ **Assume confidence**: HIGH confidence is opinion, not certainty
❌ **Skip operator review**: All guidance is advisory only

---

## Serialization

### GuidanceEvent.to_dict()
```python
data = event.to_dict()
# Returns:
{
    "event_id": "guid-xxx",
    "trigger_type": "calendar_congestion",
    "timestamp": "2026-01-30T14:30:00",
    "observation": "...",
    "implication": "...",
    "suggested_actions": [...],
    "risk_notes": [...],
    "confidence_level": "high",
    "details": {},
}

# JSON serializable:
import json
json_str = json.dumps(data)
```

### PlanDraft.to_dict()
```python
data = draft.to_dict()
# Similar structure with draft-specific fields
json_str = json.dumps(data)
```

### GuidanceSession.to_dict()
```python
data = session.to_dict()
# Includes event, draft, response, timestamp
json_str = json.dumps(data)
```

---

## Testing

### Verification Script
```bash
python verify_guidance_mode.py
# Expected: 9/9 tests passed
```

### Examples Script
```bash
python run_guidance_examples.py
# Expected: 9/9 examples completed
```

---

## Files

| File | Purpose |
|------|---------|
| `artemis/guidance_mode.py` | Core implementation (394 lines) |
| `hestia/agent.py` | UX methods (added to existing) |
| `verify_guidance_mode.py` | 9 verification tests |
| `run_guidance_examples.py` | 9 working examples |
| `STEP20_GUIDANCE_MODE_SPEC.md` | Full specification |
| `STEP20_GUIDANCE_MODE_QUICK_REFERENCE.md` | This file |

---

## Status

✅ **COMPLETE AND VERIFIED**

- Core implementation: 394 lines
- Hestia UX methods: 4 methods added
- Verification tests: 9/9 PASSED
- Working examples: 9/9 PASSED
- Compilation errors: 0
- All constraints: MET

---

## Next Steps

1. **Integration**: Wire into Stage 4 execution lifecycle
2. **Testing**: Integration tests with actual plans
3. **Training**: Operator familiarization with guidance UI
4. **Monitoring**: Track guidance event patterns
