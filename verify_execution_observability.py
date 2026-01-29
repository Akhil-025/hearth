"""
Simple verification script for Execution Observability implementation.
Tests core functionality without requiring full dependencies.
"""

import sys
import os

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_section(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def verify_imports():
    """Verify that all core modules can be imported."""
    print_section("Verifying Imports")
    
    try:
        from artemis.execution_observability import (
            ExecutionObserver,
            RollbackPlanner,
            ExecutionStatus,
            StepEventType,
            SideEffectCategory,
            ExecutionRecord,
            RollbackScaffold,
        )
        print("✓ artemis.execution_observability imports successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_execution_observer():
    """Verify ExecutionObserver functionality."""
    print_section("Verifying ExecutionObserver")
    
    try:
        from artemis.execution_observability import ExecutionObserver, ExecutionStatus
        from core.kernel import HearthKernel
        
        kernel = HearthKernel()
        observer = ExecutionObserver("exec-001", "plan-001", kernel)
        
        # Record steps
        observer.record_step_started(0, "Step 1", {"input": "test"})
        observer.record_step_completed(0, "Step 1", {"output": "result"})
        
        observer.record_step_started(1, "Step 2", {})
        observer.record_step_completed(1, "Step 2", {})
        
        observer.mark_completed("All steps completed")
        
        record = observer.get_execution_record("LIVE")
        
        assert record.execution_id == "exec-001", "Execution ID mismatch"
        assert record.plan_id == "plan-001", "Plan ID mismatch"
        assert record.status == ExecutionStatus.COMPLETED, "Status should be COMPLETED"
        assert len(record.step_events) == 4, f"Should have 4 events, got {len(record.step_events)}"
        
        print("✓ ExecutionObserver works correctly")
        print(f"  Execution ID: {record.execution_id}")
        print(f"  Status: {record.status.value}")
        print(f"  Steps: {len(record.step_events)}")
        print(f"  Execution Hash: {record.get_execution_hash()[:16]}...")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_hash_linking():
    """Verify step events are hash-linked."""
    print_section("Verifying Hash-Linked Events")
    
    try:
        from artemis.execution_observability import ExecutionObserver
        from core.kernel import HearthKernel
        
        kernel = HearthKernel()
        observer = ExecutionObserver("exec-002", "plan-002", kernel)
        
        observer.record_step_started(0, "Step 1", {})
        observer.record_step_completed(0, "Step 1", {})
        observer.record_step_started(1, "Step 2", {})
        
        record = observer.get_execution_record("LIVE")
        
        # Verify hash linking
        event_0 = record.step_events[0]
        event_1 = record.step_events[1]
        event_2 = record.step_events[2]
        
        assert event_1.previous_event_hash == event_0.get_hash(), "Event 1 should link to Event 0"
        assert event_2.previous_event_hash == event_1.get_hash(), "Event 2 should link to Event 1"
        
        print("✓ Step events are correctly hash-linked")
        print(f"  Event 0 hash: {event_0.get_hash()[:16]}...")
        print(f"  Event 1 previous: {event_1.previous_event_hash[:16]}...")
        print(f"  Event 2 previous: {event_2.previous_event_hash[:16]}...")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_failed_execution():
    """Verify recording of failed execution."""
    print_section("Verifying Failed Execution Recording")
    
    try:
        from artemis.execution_observability import ExecutionObserver, ExecutionStatus
        from core.kernel import HearthKernel
        
        kernel = HearthKernel()
        observer = ExecutionObserver("exec-003", "plan-003", kernel)
        
        observer.record_step_started(0, "Step 1", {})
        observer.record_step_completed(0, "Step 1", {})
        
        observer.record_step_started(1, "Step 2", {})
        observer.record_step_failed(1, "Step 2", "Error: constraint violated")
        
        observer.mark_failed("Execution stopped at step 2")
        
        record = observer.get_execution_record("LIVE")
        
        assert record.status == ExecutionStatus.FAILED, "Status should be FAILED"
        # Each step creates 2 events: started + completed/failed
        # So for 2 steps: 4 events total
        assert len(record.step_events) == 4, f"Should have 4 events, got {len(record.step_events)}"
        
        failed_event = record.step_events[3]
        assert failed_event.event_type.value == "step_failed", "Last event should be step_failed"
        assert failed_event.error_message == "Error: constraint violated", "Error message mismatch"
        
        print("✓ Failed execution recording works")
        print(f"  Status: {record.status.value}")
        print(f"  Reason: {record.completion_reason}")
        print(f"  Events: {len(record.step_events)}")
        print(f"  Last event type: {failed_event.event_type.value}")
        print(f"  Error: {failed_event.error_message}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_side_effects():
    """Verify side effect recording."""
    print_section("Verifying Side Effect Recording")
    
    try:
        from artemis.execution_observability import (
            ExecutionObserver,
            SideEffectCategory,
        )
        from core.kernel import HearthKernel
        
        kernel = HearthKernel()
        observer = ExecutionObserver("exec-004", "plan-004", kernel)
        
        observer.record_step_started(0, "Create Files", {})
        observer.record_side_effect(
            SideEffectCategory.FILE_SYSTEM,
            "Created /tmp/data.txt",
            reversible=True,
            step_index=0,
        )
        observer.record_side_effect(
            SideEffectCategory.CONFIGURATION,
            "Modified /etc/app.conf",
            reversible=True,
            step_index=0,
        )
        observer.record_step_completed(0, "Create Files", {})
        
        observer.mark_completed()
        
        record = observer.get_execution_record("LIVE")
        
        assert record.side_effects_report is not None, "Should have side effects report"
        assert len(record.side_effects_report.side_effects_observed) == 2, "Should have 2 side effects"
        
        effects = record.side_effects_report.side_effects_observed
        assert effects[0].category == SideEffectCategory.FILE_SYSTEM
        assert effects[1].category == SideEffectCategory.CONFIGURATION
        assert effects[0].reversible == True
        assert effects[1].reversible == True
        
        print("✓ Side effect recording works")
        print(f"  Side effects recorded: {len(effects)}")
        for i, effect in enumerate(effects, 1):
            print(f"    {i}. {effect.category.value}: {effect.description}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_rollback_scaffold():
    """Verify rollback scaffold creation."""
    print_section("Verifying Rollback Scaffold")
    
    try:
        from artemis.execution_observability import (
            ExecutionObserver,
            RollbackPlanner,
            ExecutionStatus,
            SecuritySnapshot,
        )
        from core.kernel import HearthKernel
        
        kernel = HearthKernel()
        observer = ExecutionObserver("exec-005", "plan-005", kernel)
        
        # Create a failed execution
        observer.record_step_started(0, "Create DB", {})
        observer.record_step_completed(0, "Create DB", {})
        
        observer.record_step_started(1, "Load Data", {})
        observer.record_step_failed(1, "Load Data", "Constraint error")
        
        observer.mark_failed("Data load failed")
        
        record = observer.get_execution_record("LIVE")
        
        # For rollback to be possible, security state must be OPERATIONAL
        # Since our test environment doesn't set this, let's just check
        # that the scaffold is created and has the right structure
        
        rollback_hints = [
            {
                "step_index": 0,
                "description": "Drop database",
                "actions": ["DROP DATABASE test_db;"],
                "risks": ["Irreversible"],
            }
        ]
        
        scaffold = RollbackPlanner.plan_rollback(record, rollback_hints)
        
        assert scaffold.execution_id == "exec-005", "Execution ID mismatch"
        assert len(scaffold.rollback_hints) == 1, "Should have 1 rollback hint"
        
        hint = scaffold.rollback_hints[0]
        assert hint.step_index == 0, "Hint step index mismatch"
        assert hint.description == "Drop database", "Hint description mismatch"
        
        print("✓ Rollback scaffold creation works")
        print(f"  Execution ID: {scaffold.execution_id}")
        print(f"  Rollback possible: {scaffold.is_rollback_possible}")
        print(f"  Reason: {scaffold.reason}")
        print(f"  Hints: {len(scaffold.rollback_hints)}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_security_snapshots():
    """Verify security snapshots."""
    print_section("Verifying Security Snapshots")
    
    try:
        from artemis.execution_observability import ExecutionObserver
        from core.kernel import HearthKernel
        
        kernel = HearthKernel()
        observer = ExecutionObserver("exec-006", "plan-006", kernel)
        
        observer.record_step_completed(0, "Step", {})
        observer.mark_completed()
        
        record = observer.get_execution_record("LIVE")
        
        assert record.security_snapshot_pre is not None, "Should have pre-execution snapshot"
        assert record.security_snapshot_post is not None, "Should have post-execution snapshot"
        
        pre = record.security_snapshot_pre
        post = record.security_snapshot_post
        
        assert pre.context == "Pre-execution", "Pre-snapshot context mismatch"
        assert "post" in post.context.lower(), "Post-snapshot context should mention 'post'"
        
        print("✓ Security snapshots work correctly")
        print(f"  Pre-execution: {pre.security_state}")
        print(f"  Post-execution: {post.security_state}")
        print(f"  Pre timestamp: {pre.timestamp.strftime('%H:%M:%S')}")
        print(f"  Post timestamp: {post.timestamp.strftime('%H:%M:%S')}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_immutability():
    """Verify record immutability."""
    print_section("Verifying Record Immutability")
    
    try:
        from artemis.execution_observability import ExecutionObserver
        from core.kernel import HearthKernel
        
        kernel = HearthKernel()
        observer = ExecutionObserver("exec-007", "plan-007", kernel)
        
        observer.record_step_completed(0, "Step", {})
        observer.mark_completed()
        
        record = observer.get_execution_record("LIVE")
        
        # Try to modify (should fail)
        try:
            record.execution_id = "modified"
            print("✗ Record was modified (should be immutable)")
            return False
        except Exception:
            # Expected - record is frozen
            pass
        
        print("✓ Execution records are immutable (frozen)")
        print(f"  Execution ID: {record.execution_id}")
        print(f"  (cannot be modified)")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_verifications():
    """Run all verification tests."""
    print("=" * 70)
    print(" EXECUTION OBSERVABILITY - IMPLEMENTATION VERIFICATION")
    print("=" * 70)
    print("\nTesting core functionality...")
    
    tests = [
        ("Import Verification", verify_imports),
        ("ExecutionObserver", verify_execution_observer),
        ("Hash-Linked Events", verify_hash_linking),
        ("Failed Execution", verify_failed_execution),
        ("Side Effects", verify_side_effects),
        ("Rollback Scaffold", verify_rollback_scaffold),
        ("Security Snapshots", verify_security_snapshots),
        ("Record Immutability", verify_immutability),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
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
        print("\n✓ ALL TESTS PASSED - Execution Observability implementation verified!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed - Please review errors above")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_verifications())
