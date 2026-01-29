"""
STEP 20: POLICY-CONSTRAINED GUIDANCE MODE - WORKING EXAMPLES

Demonstrates:
- Creating guidance events (immutable)
- Proposing draft plans (not executed)
- Operator interactions
- Security checks (guidance disabled if Artemis compromised)
- Guidance history (append-only)

Key Points:
- Guidance is ADVISORY only
- No execution authority
- Operator must approve any action
- No memory writes
- No background tasks
- Fail-closed
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artemis.guidance_mode import (
    GuidanceEvent,
    GuidanceObserver,
    GuidancePlanner,
    GuidanceSession,
    TriggerType,
    ConfidenceLevel,
    PlanDraft,
)
from core.kernel import HearthKernel


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def example_1_calendar_congestion():
    """Example 1: Calendar congestion guidance."""
    print_section("Example 1: Calendar Congestion Guidance")
    
    kernel = HearthKernel()
    observer = GuidanceObserver(kernel)
    
    # Simulate calendar congestion detection
    event = observer.surface_guidance(
        observation="5 plans scheduled within 2-hour window (10am-12pm)",
        implication="Resource contention likely; operations may interfere",
        trigger_type=TriggerType.CALENDAR_CONGESTION,
        suggested_actions=[
            "Review plan priorities and dependencies",
            "Consider deferring non-critical operations",
            "Monitor resource utilization during window",
        ],
        risk_notes=[
            "Operator must review before any reschedule",
            "Some plans may have fixed deadlines",
        ],
        confidence_level=ConfidenceLevel.HIGH,
        details={"window": "10:00-12:00", "plan_count": 5},
    )
    
    print(f"\n✓ Guidance Event Created")
    print(f"  Event ID: {event.event_id}")
    print(f"  Type: {event.trigger_type.value}")
    print(f"  Confidence: {event.confidence_level.value}")
    print(f"  Observation: {event.observation}")
    print(f"  Suggested actions: {len(event.suggested_actions)}")
    
    # Check history
    history = observer.get_guidance_history()
    print(f"\n✓ Guidance History:")
    print(f"  Total events: {len(history)}")


def example_2_repeated_rejections():
    """Example 2: Repeated rejections guidance."""
    print_section("Example 2: Repeated Rejections Guidance")
    
    kernel = HearthKernel()
    observer = GuidanceObserver(kernel)
    
    # Simulate repeated rejection pattern
    rejection_history = [
        {"reason": "Constraint violation", "plan_id": "plan-001"},
        {"reason": "Constraint violation", "plan_id": "plan-002"},
        {"reason": "Constraint violation", "plan_id": "plan-003"},
    ]
    
    event = observer.surface_guidance(
        observation="3 consecutive rejections with same error: 'Constraint violation'",
        implication="Systematic issue in plan structure, not transient error",
        trigger_type=TriggerType.REPEATED_REJECTIONS,
        suggested_actions=[
            "Review constraint definitions",
            "Check recent changes to plan schema",
            "Validate input data quality",
        ],
        risk_notes=[
            "May indicate data corruption or schema drift",
            "Manual investigation required",
        ],
        confidence_level=ConfidenceLevel.HIGH,
        details={"rejection_count": 3, "error_type": "constraint_violation"},
    )
    
    print(f"\n✓ Guidance Event Created")
    print(f"  Event ID: {event.event_id}")
    print(f"  Type: {event.trigger_type.value}")
    print(f"  Observation: {event.observation}")
    
    # Propose draft plan for analysis
    planner = GuidancePlanner()
    draft = planner.propose_rejection_analysis(event, rejection_history)
    
    if draft:
        print(f"\n✓ Draft Plan Proposed")
        print(f"  Draft ID: {draft.draft_id}")
        print(f"  Title: {draft.title}")
        print(f"  Rationale: {draft.rationale}")
        print(f"  Steps: {len(draft.proposed_steps)}")


def example_3_security_state_change():
    """Example 3: Security state change guidance."""
    print_section("Example 3: Security State Change Guidance")
    
    kernel = HearthKernel()
    observer = GuidanceObserver(kernel)
    
    # Simulate security state change
    event = observer.surface_guidance(
        observation="Artemis transitioned from OPERATIONAL to WARNING",
        implication="Security posture degraded; execution authority may be restricted",
        trigger_type=TriggerType.SECURITY_STATE_CHANGE,
        suggested_actions=[
            "Review Artemis state change log",
            "Verify no unauthorized changes detected",
            "Consider pausing non-critical operations",
        ],
        risk_notes=[
            "Guidance is advisory only",
            "Consult security team for escalated states",
        ],
        confidence_level=ConfidenceLevel.HIGH,
        details={"previous_state": "OPERATIONAL", "new_state": "WARNING"},
    )
    
    print(f"\n✓ Guidance Event Created")
    print(f"  Event ID: {event.event_id}")
    print(f"  Type: {event.trigger_type.value}")
    print(f"  Observation: {event.observation}")
    
    # Propose checkpoint draft
    planner = GuidancePlanner()
    draft = planner.propose_security_checkpoint(event)
    
    if draft:
        print(f"\n✓ Draft Plan Proposed")
        print(f"  Draft ID: {draft.draft_id}")
        print(f"  Title: {draft.title}")
        print(f"  Rationale: {draft.rationale}")


def example_4_irreversible_action_frequency():
    """Example 4: Irreversible action frequency guidance."""
    print_section("Example 4: Irreversible Action Frequency Guidance")
    
    kernel = HearthKernel()
    observer = GuidanceObserver(kernel)
    
    # Simulate high frequency of irreversible actions
    event = observer.surface_guidance(
        observation="8 irreversible actions executed in last 24 hours",
        implication="Limited ability to recover from failures; system at higher risk",
        trigger_type=TriggerType.IRREVERSIBLE_ACTION_FREQUENCY,
        suggested_actions=[
            "Review necessity of recent irreversible operations",
            "Increase backup frequency if possible",
            "Consider reducing plan complexity temporarily",
        ],
        risk_notes=[
            "Cannot auto-rollback after irreversible operations",
            "High frequency increases recovery time if incident occurs",
        ],
        confidence_level=ConfidenceLevel.MEDIUM,
        details={"action_count": 8, "window_hours": 24},
    )
    
    print(f"\n✓ Guidance Event Created")
    print(f"  Event ID: {event.event_id}")
    print(f"  Type: {event.trigger_type.value}")
    print(f"  Confidence: {event.confidence_level.value}")


def example_5_budget_threshold():
    """Example 5: Budget threshold alert guidance."""
    print_section("Example 5: Budget Threshold Alert Guidance")
    
    kernel = HearthKernel()
    observer = GuidanceObserver(kernel)
    
    # Simulate budget threshold alert
    event = observer.surface_guidance(
        observation="Monthly spending is at 85% of budget ($42,500 of $50,000)",
        implication="Limited budget remaining; costly operations may be restricted",
        trigger_type=TriggerType.BUDGET_THRESHOLD_ALERT,
        suggested_actions=[
            "Review planned operations for cost impact",
            "Defer non-critical, high-cost operations",
            "Monitor daily spending for trend",
        ],
        risk_notes=[
            "This is a read-only alert (no budget changes)",
            "Operations may be approved up to limit",
        ],
        confidence_level=ConfidenceLevel.HIGH,
        details={"budget_percentage": 85, "amount_spent": 42500, "budget_limit": 50000},
    )
    
    print(f"\n✓ Guidance Event Created")
    print(f"  Event ID: {event.event_id}")
    print(f"  Type: {event.trigger_type.value}")
    print(f"  Observation: {event.observation}")


def example_6_guidance_session():
    """Example 6: Complete guidance session."""
    print_section("Example 6: Complete Guidance Session")
    
    kernel = HearthKernel()
    observer = GuidanceObserver(kernel)
    
    # Create guidance event
    event = observer.surface_guidance(
        observation="Plan 'maintenance-window' rejected 3 times this week",
        implication="Similar operations failing; pattern suggests systematic issue",
        trigger_type=TriggerType.REPEATED_REJECTIONS,
        suggested_actions=[
            "Review maintenance window definition",
            "Check for conflicts in resource definitions",
        ],
        risk_notes=[
            "Multiple rejections = operator review needed",
        ],
        confidence_level=ConfidenceLevel.MEDIUM,
    )
    
    print(f"\n✓ Guidance Event Created")
    print(f"  Event ID: {event.event_id}")
    
    # Propose optional draft
    planner = GuidancePlanner()
    draft = planner.propose_rejection_analysis(event, [])
    
    print(f"\n✓ Draft Plan Available: {draft is not None}")
    
    # Create session
    session = GuidanceSession.create(
        guidance_event=event,
        drafted_plan=draft,
        operator_response="ask_more",
    )
    
    print(f"\n✓ Guidance Session Created")
    print(f"  Session ID: {session.session_id}")
    print(f"  Response: {session.operator_response}")
    print(f"  Draft included: {session.drafted_plan is not None}")


def example_7_security_disabled():
    """Example 7: Guidance disabled during security incident."""
    print_section("Example 7: Guidance Disabled (Security Incident)")
    
    # Use minimal kernel (no security escalation in test)
    kernel = None  # No kernel = guidance enabled
    observer = GuidanceObserver(kernel)
    
    # Normal guidance
    event1 = observer.surface_guidance(
        observation="Test observation",
        implication="Test implication",
        trigger_type=TriggerType.CALENDAR_CONGESTION,
        suggested_actions=["Test action"],
        risk_notes=[],
        confidence_level=ConfidenceLevel.MEDIUM,
    )
    
    print(f"\n✓ Normal Guidance Enabled")
    print(f"  Event: {event1.observation}")
    
    # Disable guidance manually
    observer._disabled = True
    
    event2 = observer.surface_guidance(
        observation="Should be blocked",
        implication="Guidance is disabled",
        trigger_type=TriggerType.CALENDAR_CONGESTION,
        suggested_actions=["Should not appear"],
        risk_notes=[],
        confidence_level=ConfidenceLevel.HIGH,
    )
    
    print(f"\n✓ Guidance Disabled Check")
    print(f"  Event note: {event2.observation}")
    print(f"  (Demonstrates fail-closed behavior)")


def example_8_immutability():
    """Example 8: Guidance events are immutable."""
    print_section("Example 8: Immutable Guidance Events")
    
    # Create event
    event = GuidanceEvent.create(
        trigger_type=TriggerType.CALENDAR_CONGESTION,
        observation="Test observation",
        implication="Test implication",
        suggested_actions=["Action 1"],
        risk_notes=["Risk 1"],
        confidence_level=ConfidenceLevel.MEDIUM,
    )
    
    print(f"\n✓ Guidance Event Created")
    print(f"  Event ID: {event.event_id}")
    
    # Try to modify (should fail)
    try:
        event.observation = "Modified"
        print(f"\n✗ Event was modified (should be immutable)")
    except Exception:
        print(f"\n✓ Event is immutable (frozen dataclass)")
        print(f"  Cannot modify after creation")


def example_9_plan_draft_immutability():
    """Example 9: Draft plans are immutable."""
    print_section("Example 9: Immutable Draft Plans")
    
    # Create draft
    draft = PlanDraft.create(
        guidance_event_id="guid-test",
        title="Test Draft",
        description="Test description",
        proposed_steps=[{"order": 1, "suggestion": "Test step"}],
        rationale="Test rationale",
        risks=["Test risk"],
    )
    
    print(f"\n✓ Draft Plan Created")
    print(f"  Draft ID: {draft.draft_id}")
    
    # Try to modify (should fail)
    try:
        draft.title = "Modified Title"
        print(f"\n✗ Draft was modified (should be immutable)")
    except Exception:
        print(f"\n✓ Draft Plan is immutable (frozen dataclass)")
        print(f"  Cannot modify after creation")


def run_all_examples():
    """Run all examples."""
    print("\n" + "=" * 70)
    print(" STEP 20: POLICY-CONSTRAINED GUIDANCE MODE - EXAMPLES")
    print("=" * 70)
    
    examples = [
        example_1_calendar_congestion,
        example_2_repeated_rejections,
        example_3_security_state_change,
        example_4_irreversible_action_frequency,
        example_5_budget_threshold,
        example_6_guidance_session,
        example_7_security_disabled,
        example_8_immutability,
        example_9_plan_draft_immutability,
    ]
    
    for i, example in enumerate(examples, 1):
        try:
            example()
            print(f"\n✓ Example {i} completed successfully")
        except Exception as e:
            print(f"\n✗ Example {i} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(" ALL EXAMPLES COMPLETED")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_all_examples()
