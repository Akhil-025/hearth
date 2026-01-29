"""
Simple verification script for Live Mode Gate implementation.
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
        from artemis.live_mode_gate import LiveModeGate, LiveModeState, LiveModeTransition, LiveModeGateValidator
        print("✓ artemis.live_mode_gate imports successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import artemis.live_mode_gate: {e}")
        return False

def verify_gate_creation():
    """Verify that LiveModeGate can be created."""
    print_section("Verifying Gate Creation")
    
    try:
        from artemis.live_mode_gate import LiveModeGate, LiveModeState
        
        # Create gate without kernel (minimal test)
        gate = LiveModeGate(kernel=None)
        
        # Check default state
        assert gate.get_state() == LiveModeState.DRY_RUN, "Default state should be DRY_RUN"
        assert gate.is_dry_run(), "is_dry_run() should return True"
        assert not gate.is_live(), "is_live() should return False"
        
        print("✓ Gate defaults to DRY_RUN (fail-closed)")
        print(f"  State: {gate.get_state().value}")
        print(f"  is_dry_run(): {gate.is_dry_run()}")
        print(f"  is_live(): {gate.is_live()}")
        return True
    except Exception as e:
        print(f"✗ Failed to create gate: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_enable_disable():
    """Verify enable/disable functionality."""
    print_section("Verifying Enable/Disable")
    
    try:
        from artemis.live_mode_gate import LiveModeGate, LiveModeState
        
        gate = LiveModeGate(kernel=None)
        
        # Enable live mode
        success, message = gate.enable_live(
            reason="Testing enable",
            user_identity="test@example.com"
        )
        
        assert success, f"Enable should succeed: {message}"
        assert gate.is_live(), "Gate should be LIVE after enable"
        print("✓ Enable live mode works")
        print(f"  Success: {success}")
        print(f"  Message: {message}")
        print(f"  New state: {gate.get_state().value}")
        
        # Disable live mode
        success, message = gate.disable_live(
            reason="Testing disable",
            user_identity="test@example.com",
            automatic=False
        )
        
        assert success, f"Disable should succeed: {message}"
        assert gate.is_dry_run(), "Gate should be DRY_RUN after disable"
        print("✓ Disable live mode works")
        print(f"  Success: {success}")
        print(f"  Message: {message}")
        print(f"  New state: {gate.get_state().value}")
        
        return True
    except Exception as e:
        print(f"✗ Failed enable/disable test: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_transition_history():
    """Verify transition history recording."""
    print_section("Verifying Transition History")
    
    try:
        from artemis.live_mode_gate import LiveModeGate
        
        gate = LiveModeGate(kernel=None)
        
        # Perform multiple transitions
        gate.enable_live("First enable", "user1@example.com")
        gate.disable_live("First disable", "user1@example.com", automatic=False)
        gate.enable_live("Second enable", "user2@example.com")
        
        # Get history
        history = gate.get_transition_history()
        
        # Should have: 1 init + 3 transitions = 4 total
        assert len(history) >= 4, f"Should have at least 4 transitions (1 init + 3 explicit), got {len(history)}"
        
        # Skip initialization transition (index 0)
        # First user transition should be enable (DRY_RUN → LIVE)
        first_user_transition = history[1]
        print(f"  First user transition: {first_user_transition.from_state.value} → {first_user_transition.to_state.value}")
        assert first_user_transition.from_state.value == "DRY_RUN", "First user transition should be from DRY_RUN"
        assert first_user_transition.to_state.value == "LIVE", "First user transition should be to LIVE"
        assert first_user_transition.reason == "First enable", "First user transition reason mismatch"
        assert first_user_transition.user_identity == "user1@example.com", "First user transition user mismatch"
        assert not first_user_transition.automatic, "First user transition should not be automatic"
        
        print("✓ Transition history works")
        print(f"  Total transitions: {len(history)} (including initialization)")
        for i, t in enumerate(history, 1):
            auto_flag = " [AUTO]" if t.automatic else ""
            print(f"  {i}. {t.from_state.value} → {t.to_state.value}{auto_flag}")
            print(f"     Reason: {t.reason}")
            print(f"     User: {t.user_identity}")
        
        return True
    except Exception as e:
        print(f"✗ Failed transition history test: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_validator():
    """Verify LiveModeGateValidator."""
    print_section("Verifying Validator")
    
    try:
        from artemis.live_mode_gate import LiveModeGate, LiveModeGateValidator
        
        # Test with DRY_RUN gate
        gate = LiveModeGate(kernel=None)
        can_execute, reason = LiveModeGateValidator.can_execute(gate)
        
        assert not can_execute, "Should not allow execution in DRY_RUN"
        assert "DRY_RUN" in reason, "Reason should mention DRY_RUN"
        print("✓ Validator blocks DRY_RUN")
        print(f"  Can execute: {can_execute}")
        print(f"  Reason: {reason}")
        
        # Test with LIVE gate
        gate.enable_live("Testing validator", "test@example.com")
        can_execute, reason = LiveModeGateValidator.can_execute(gate)
        
        assert can_execute, "Should allow execution in LIVE"
        assert "LIVE" in reason, "Reason should mention LIVE"
        print("✓ Validator allows LIVE")
        print(f"  Can execute: {can_execute}")
        print(f"  Reason: {reason}")
        
        # Test with no gate
        can_execute, reason = LiveModeGateValidator.can_execute(None)
        assert not can_execute, "Should not allow execution with no gate"
        print("✓ Validator blocks when no gate configured")
        print(f"  Can execute: {can_execute}")
        print(f"  Reason: {reason}")
        
        return True
    except Exception as e:
        print(f"✗ Failed validator test: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_input_validation():
    """Verify input validation."""
    print_section("Verifying Input Validation")
    
    try:
        from artemis.live_mode_gate import LiveModeGate
        
        gate = LiveModeGate(kernel=None)
        
        # Test empty reason
        success, message = gate.enable_live("", "user@example.com")
        assert not success, "Should reject empty reason"
        assert "Reason" in message or "empty" in message.lower(), "Error should mention reason"
        print("✓ Rejects empty reason")
        print(f"  Message: {message}")
        
        # Test empty user
        success, message = gate.enable_live("Test reason", "")
        assert not success, "Should reject empty user"
        assert "User" in message or "identity" in message.lower() or "empty" in message.lower(), "Error should mention user"
        print("✓ Rejects empty user identity")
        print(f"  Message: {message}")
        
        return True
    except Exception as e:
        print(f"✗ Failed input validation test: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_verifications():
    """Run all verification tests."""
    print("=" * 70)
    print(" LIVE MODE GATE - IMPLEMENTATION VERIFICATION")
    print("=" * 70)
    print("\nTesting core functionality without full dependencies...")
    
    tests = [
        ("Import Verification", verify_imports),
        ("Gate Creation", verify_gate_creation),
        ("Enable/Disable", verify_enable_disable),
        ("Transition History", verify_transition_history),
        ("Validator", verify_validator),
        ("Input Validation", verify_input_validation),
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
        print("\n✓ ALL TESTS PASSED - Live Mode Gate implementation verified!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed - Please review errors above")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_verifications())
