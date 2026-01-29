"""
Verification script for Step 20: Policy-Constrained Guidance Mode
Tests core functionality without external dependencies.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_section(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def verify_imports():
    """Verify imports."""
    print_section("Verifying Imports")
    
    try:
        from artemis.guidance_mode import (
            GuidanceEvent,
            GuidanceObserver,
            GuidancePlanner,
            GuidanceSession,
            TriggerType,
            ConfidenceLevel,
            PlanDraft,
        )
        print("✓ artemis.guidance_mode imports successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_guidance_event_creation():
    """Verify GuidanceEvent creation."""
    print_section("Verifying GuidanceEvent Creation")
    
    try:
        from artemis.guidance_mode import GuidanceEvent, TriggerType, ConfidenceLevel
        
        event = GuidanceEvent.create(
            trigger_type=TriggerType.CALENDAR_CONGESTION,
            observation="5 plans scheduled in 2 hours",
            implication="Resource contention likely",
            suggested_actions=["Review priorities", "Defer non-critical ops"],
            risk_notes=["Manual review needed"],
            confidence_level=ConfidenceLevel.HIGH,
        )
        
        assert event.event_id.startswith("guid-"), "Event ID format wrong"
        assert event.observation == "5 plans scheduled in 2 hours", "Observation mismatch"
        assert len(event.suggested_actions) == 2, "Actions count wrong"
        assert event.confidence_level == ConfidenceLevel.HIGH, "Confidence mismatch"
        
        print("✓ GuidanceEvent creation works")
        print(f"  Event ID: {event.event_id}")
        print(f"  Type: {event.trigger_type.value}")
        print(f"  Confidence: {event.confidence_level.value}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_guidance_observer():
    """Verify GuidanceObserver."""
    print_section("Verifying GuidanceObserver")
    
    try:
        from artemis.guidance_mode import GuidanceObserver, TriggerType, ConfidenceLevel
        from core.kernel import HearthKernel
        
        kernel = HearthKernel()
        observer = GuidanceObserver(kernel)
        
        # Surface guidance
        event = observer.surface_guidance(
            observation="Test observation",
            implication="Test implication",
            trigger_type=TriggerType.REPEATED_REJECTIONS,
            suggested_actions=["Action 1", "Action 2"],
            risk_notes=["Risk 1"],
            confidence_level=ConfidenceLevel.MEDIUM,
        )
        
        assert event is not None, "Event creation failed"
        
        # Check history
        history = observer.get_guidance_history()
        assert len(history) == 1, "History not recorded"
        assert history[0].event_id == event.event_id, "Event ID mismatch"
        
        print("✓ GuidanceObserver works")
        print(f"  Events surfaced: {len(history)}")
        print(f"  Last event: {history[0].trigger_type.value}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_guidance_planner():
    """Verify GuidancePlanner."""
    print_section("Verifying GuidancePlanner")
    
    try:
        from artemis.guidance_mode import (
            GuidancePlanner,
            GuidanceEvent,
            TriggerType,
            ConfidenceLevel,
        )
        
        # Create guidance event
        event = GuidanceEvent.create(
            trigger_type=TriggerType.CALENDAR_CONGESTION,
            observation="Calendar congestion",
            implication="Resource conflict",
            suggested_actions=["Review"],
            risk_notes=[],
            confidence_level=ConfidenceLevel.HIGH,
        )
        
        # Test calendar optimization draft
        draft = GuidancePlanner.propose_calendar_optimization(
            event,
            [{"name": "plan1"}, {"name": "plan2"}],
        )
        
        assert draft is not None, "Draft not created"
        assert draft.draft_id.startswith("draft-"), "Draft ID format wrong"
        assert draft.guidance_event_id == event.event_id, "Event ID mismatch"
        
        print("✓ GuidancePlanner works")
        print(f"  Draft ID: {draft.draft_id}")
        print(f"  Title: {draft.title}")
        print(f"  Proposed steps: {len(draft.proposed_steps)}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_plan_draft_creation():
    """Verify PlanDraft creation."""
    print_section("Verifying PlanDraft Creation")
    
    try:
        from artemis.guidance_mode import PlanDraft
        
        draft = PlanDraft.create(
            guidance_event_id="guid-test",
            title="Test Draft",
            description="Test description",
            proposed_steps=[{"order": 1, "suggestion": "Step 1"}],
            rationale="Test rationale",
            risks=["Test risk"],
        )
        
        assert draft.draft_id.startswith("draft-"), "Draft ID format wrong"
        assert draft.title == "Test Draft", "Title mismatch"
        assert len(draft.proposed_steps) == 1, "Steps count wrong"
        
        print("✓ PlanDraft creation works")
        print(f"  Draft ID: {draft.draft_id}")
        print(f"  Title: {draft.title}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_guidance_session():
    """Verify GuidanceSession."""
    print_section("Verifying GuidanceSession")
    
    try:
        from artemis.guidance_mode import (
            GuidanceSession,
            GuidanceEvent,
            TriggerType,
            ConfidenceLevel,
        )
        
        event = GuidanceEvent.create(
            trigger_type=TriggerType.SECURITY_STATE_CHANGE,
            observation="Security state changed",
            implication="Posture degraded",
            suggested_actions=["Review"],
            risk_notes=[],
            confidence_level=ConfidenceLevel.HIGH,
        )
        
        session = GuidanceSession.create(
            guidance_event=event,
            operator_response="dismiss",
        )
        
        assert session.session_id.startswith("sess-"), "Session ID format wrong"
        assert session.guidance_event.event_id == event.event_id, "Event mismatch"
        assert session.operator_response == "dismiss", "Response mismatch"
        
        print("✓ GuidanceSession creation works")
        print(f"  Session ID: {session.session_id}")
        print(f"  Response: {session.operator_response}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_immutability():
    """Verify immutability."""
    print_section("Verifying Immutability")
    
    try:
        from artemis.guidance_mode import GuidanceEvent, TriggerType, ConfidenceLevel
        
        event = GuidanceEvent.create(
            trigger_type=TriggerType.CALENDAR_CONGESTION,
            observation="Test",
            implication="Test",
            suggested_actions=[],
            risk_notes=[],
            confidence_level=ConfidenceLevel.MEDIUM,
        )
        
        # Try to modify (should fail)
        try:
            event.observation = "Modified"
            print("✗ Event was modified (should be immutable)")
            return False
        except Exception:
            # Expected - event is frozen
            pass
        
        print("✓ GuidanceEvent is immutable (frozen)")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_serialization():
    """Verify serialization."""
    print_section("Verifying Serialization")
    
    try:
        from artemis.guidance_mode import GuidanceEvent, TriggerType, ConfidenceLevel
        import json
        
        event = GuidanceEvent.create(
            trigger_type=TriggerType.REPEATED_REJECTIONS,
            observation="Test",
            implication="Test",
            suggested_actions=["Action"],
            risk_notes=["Risk"],
            confidence_level=ConfidenceLevel.HIGH,
        )
        
        # Serialize to dict
        data = event.to_dict()
        
        # Verify structure
        assert "event_id" in data, "Missing event_id"
        assert "trigger_type" in data, "Missing trigger_type"
        assert "timestamp" in data, "Missing timestamp"
        
        # Verify JSON serializable
        json_str = json.dumps(data)
        assert json_str, "JSON serialization failed"
        
        print("✓ GuidanceEvent serialization works")
        print(f"  Dict keys: {len(data)}")
        print(f"  JSON size: {len(json_str)} bytes")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_all_trigger_types():
    """Verify all trigger types."""
    print_section("Verifying All Trigger Types")
    
    try:
        from artemis.guidance_mode import GuidanceEvent, TriggerType, ConfidenceLevel
        
        trigger_types = [
            TriggerType.CALENDAR_CONGESTION,
            TriggerType.REPEATED_REJECTIONS,
            TriggerType.SECURITY_STATE_CHANGE,
            TriggerType.IRREVERSIBLE_ACTION_FREQUENCY,
            TriggerType.BUDGET_THRESHOLD_ALERT,
        ]
        
        created = 0
        for trigger_type in trigger_types:
            event = GuidanceEvent.create(
                trigger_type=trigger_type,
                observation="Test",
                implication="Test",
                suggested_actions=["Action"],
                risk_notes=[],
                confidence_level=ConfidenceLevel.MEDIUM,
            )
            assert event.trigger_type == trigger_type, "Trigger type mismatch"
            created += 1
        
        print("✓ All trigger types work")
        print(f"  Trigger types tested: {created}/5")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_verifications():
    """Run all verifications."""
    print("=" * 70)
    print(" STEP 20: GUIDANCE MODE - VERIFICATION")
    print("=" * 70)
    print("\nTesting core functionality...")
    
    tests = [
        ("Import Verification", verify_imports),
        ("GuidanceEvent Creation", verify_guidance_event_creation),
        ("GuidanceObserver", verify_guidance_observer),
        ("GuidancePlanner", verify_guidance_planner),
        ("PlanDraft Creation", verify_plan_draft_creation),
        ("GuidanceSession", verify_guidance_session),
        ("Immutability", verify_immutability),
        ("Serialization", verify_serialization),
        ("All Trigger Types", verify_all_trigger_types),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ {test_name} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print_section("VERIFICATION SUMMARY")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print("\n" + "=" * 70)
    print(f" RESULT: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED - Guidance Mode implementation verified!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_verifications())
