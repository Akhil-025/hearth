"""
Simplified Execution Observability Examples (No external dependencies)
Demonstrates all Step 19 features without requiring pydantic, hestia, etc.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artemis.execution_observability import (
    ExecutionObserver,
    RollbackPlanner,
    ExecutionStatus,
    SideEffectCategory,
)
from core.kernel import HearthKernel


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def example_1_basic_execution_record():
    """Example 1: Create a basic execution record with hash-linked events."""
    print_section("Example 1: Basic Execution Record (Hash-Linked Events)")
    
    kernel = HearthKernel()
    observer = ExecutionObserver("exec-001", "plan-deploy", kernel)
    
    # Record execution steps
    observer.record_step_started(0, "Deploy Database", {})
    print("  [Record] Step 0 started: Deploy Database")
    
    observer.record_step_completed(0, "Deploy Database", {})
    print("  [Record] Step 0 completed")
    
    observer.record_step_started(1, "Deploy Service", {})
    print("  [Record] Step 1 started: Deploy Service")
    
    observer.record_step_completed(1, "Deploy Service", {})
    print("  [Record] Step 1 completed")
    
    observer.mark_completed("All steps finished")
    print("  [Record] Execution marked as completed")
    
    # Get immutable record
    record = observer.get_execution_record("LIVE")
    
    print("\n  [Result] Execution Record:")
    print(f"    - Execution ID: {record.execution_id}")
    print(f"    - Plan ID: {record.plan_id}")
    print(f"    - Status: {record.status.value}")
    print(f"    - Steps recorded: {len(record.step_events)}")
    print(f"    - Execution hash: {record.get_execution_hash()[:20]}...")
    
    # Show hash linking
    print("\n  [Result] Hash-Linked Events:")
    for i, event in enumerate(record.step_events):
        if event.previous_event_hash:
            print(f"    Event {i}: {event.event_type.value} (links to {event.previous_event_hash[:16]}...)")
        else:
            print(f"    Event {i}: {event.event_type.value} (first event)")


def example_2_failed_execution():
    """Example 2: Record execution failure and partial state."""
    print_section("Example 2: Failed Execution (Partial Recording)")
    
    kernel = HearthKernel()
    observer = ExecutionObserver("exec-002", "plan-migrate", kernel)
    
    # Successful steps
    observer.record_step_started(0, "Backup Data", {})
    observer.record_step_completed(0, "Backup Data", {})
    print("  [Record] Step 0 completed: Backup Data")
    
    # Failed step
    observer.record_step_started(1, "Migrate Data", {})
    print("  [Record] Step 1 started: Migrate Data")
    
    observer.record_step_failed(1, "Migrate Data", "Foreign key constraint violation")
    print("  [Record] Step 1 failed: Foreign key constraint violation")
    
    observer.mark_failed("Migration failed at step 1")
    print("  [Record] Execution marked as FAILED")
    
    record = observer.get_execution_record("LIVE")
    
    print("\n  [Result] Execution Record:")
    print(f"    - Execution ID: {record.execution_id}")
    print(f"    - Status: {record.status.value}")
    print(f"    - Completion reason: {record.completion_reason}")
    print(f"    - Events recorded: {len(record.step_events)}")
    
    # Show partial record
    print("\n  [Result] Partial Execution State:")
    print(f"    - Step 0: COMPLETED")
    print(f"    - Step 1: FAILED")
    print(f"    - System state: PARTIALLY MODIFIED (cannot auto-rollback)")


def example_3_side_effects_tracking():
    """Example 3: Track observable side effects."""
    print_section("Example 3: Side Effects Tracking")
    
    kernel = HearthKernel()
    observer = ExecutionObserver("exec-003", "plan-setup", kernel)
    
    # Record steps with side effects
    observer.record_step_started(0, "Create Resources", {})
    print("  [Record] Step 0 started: Create Resources")
    
    # Record observable side effects
    observer.record_side_effect(
        SideEffectCategory.FILE_SYSTEM,
        "Created /data/config.json",
        reversible=True,
        step_index=0,
    )
    print("    - Side effect: FILE_SYSTEM - Created /data/config.json (reversible)")
    
    observer.record_side_effect(
        SideEffectCategory.CONFIGURATION,
        "Modified environment variables",
        reversible=True,
        step_index=0,
    )
    print("    - Side effect: CONFIGURATION - Modified environment variables (reversible)")
    
    observer.record_side_effect(
        SideEffectCategory.DATA_MUTATION,
        "Inserted 5000 records into database",
        reversible=False,
        step_index=0,
    )
    print("    - Side effect: DATA_MUTATION - Inserted 5000 records (NOT reversible)")
    
    observer.record_step_completed(0, "Create Resources", {})
    observer.mark_completed()
    
    record = observer.get_execution_record("LIVE")
    
    print("\n  [Result] Side Effects Report:")
    if record.side_effects_report:
        effects = record.side_effects_report.side_effects_observed
        print(f"    - Total effects recorded: {len(effects)}")
        
        reversible = [e for e in effects if e.reversible]
        irreversible = [e for e in effects if not e.reversible]
        
        print(f"    - Reversible: {len(reversible)}")
        for e in reversible:
            print(f"      * {e.category.value}: {e.description}")
        
        print(f"    - Irreversible: {len(irreversible)}")
        for e in irreversible:
            print(f"      * {e.category.value}: {e.description}")


def example_4_security_escalation():
    """Example 4: Security escalation stops execution."""
    print_section("Example 4: Security Escalation (Stops Execution)")
    
    kernel = HearthKernel()
    observer = ExecutionObserver("exec-004", "plan-deploy", kernel)
    
    # Normal steps
    observer.record_step_started(0, "Initialize", {})
    observer.record_step_completed(0, "Initialize", {})
    print("  [Record] Step 0 completed")
    
    # Security escalation detected - mark execution as incomplete
    observer.mark_incomplete_security_escalation("Artemis detected unauthorized access attempt")
    print("  [Security] Escalation detected - stopping execution")
    
    record = observer.get_execution_record("LIVE")
    
    print("\n  [Result] Execution Record:")
    print(f"    - Status: {record.status.value}")
    print(f"    - Reason: {record.completion_reason}")
    print(f"    - Steps recorded: {len(record.step_events)}")
    print(f"    - Execution is: PARTIAL and INCOMPLETE")
    print(f"    - Further execution: BLOCKED by Artemis")


def example_5_rollback_scaffold():
    """Example 5: Rollback scaffold (NOT executed)."""
    print_section("Example 5: Rollback Scaffold (NOT Executed)")
    
    kernel = HearthKernel()
    observer = ExecutionObserver("exec-005", "plan-deploy", kernel)
    
    # Simulate a deployment that failed
    observer.record_step_started(0, "Deploy Database", {})
    observer.record_step_completed(0, "Deploy Database", {})
    print("  [Record] Database deployed")
    
    observer.record_step_started(1, "Deploy Service", {})
    observer.record_step_failed(1, "Deploy Service", "Port already in use")
    print("  [Record] Service deployment failed")
    
    observer.mark_failed("Service deployment failed")
    
    record = observer.get_execution_record("LIVE")
    
    # Create rollback scaffold (inspection only - NOT executed)
    rollback_hints = [
        {
            "step_index": 0,
            "description": "Drop database schema",
            "actions": [
                "DROP SCHEMA IF EXISTS public CASCADE;",
            ],
            "risks": ["Irreversible", "Affects all dependent objects"],
            "estimated_duration": "30 seconds",
        },
    ]
    
    scaffold = RollbackPlanner.plan_rollback(record, rollback_hints)
    
    print("\n  [Result] Rollback Scaffold (Manual Guidance Only):")
    print(f"    - Execution ID: {scaffold.execution_id}")
    print(f"    - Rollback possible: {scaffold.is_rollback_possible}")
    print(f"    - Reason: {scaffold.reason}")
    print(f"    - Hints from plan: {len(scaffold.rollback_hints)}")
    
    if scaffold.rollback_hints:
        print("\n  [Result] Hints (to be executed MANUALLY by operator):")
        for hint in scaffold.rollback_hints:
            print(f"    - Step {hint.step_index}: {hint.description}")
            for action in hint.actions:
                print(f"      $ {action}")
            if hint.risks:
                print(f"      Risks: {', '.join(hint.risks)}")
    
    print("\n  [Important] This is a SCAFFOLD only:")
    print("    - No automatic execution")
    print("    - No rollback performed")
    print("    - Operator must review and execute manually")
    print("    - System state unchanged")


def example_6_execution_summary():
    """Example 6: Display execution summary for operator."""
    print_section("Example 6: Execution Summary Display")
    
    kernel = HearthKernel()
    observer = ExecutionObserver("exec-006", "plan-deploy", kernel)
    
    # Simulate a complete deployment
    observer.record_step_started(0, "Validate Config", {})
    observer.record_step_completed(0, "Validate Config", {})
    
    observer.record_step_started(1, "Deploy Database", {})
    observer.record_step_completed(1, "Deploy Database", {})
    
    observer.record_step_started(2, "Deploy Service", {})
    observer.record_step_completed(2, "Deploy Service", {})
    
    observer.record_side_effect(
        SideEffectCategory.FILE_SYSTEM,
        "Created service configuration files",
        reversible=True,
    )
    
    observer.mark_completed("Deployment successful")
    
    record = observer.get_execution_record("LIVE")
    
    print("\n  [Result] Execution Summary:")
    print(f"    Execution ID: {record.execution_id}")
    print(f"    Plan ID: {record.plan_id}")
    print(f"    Status: {record.status.value.upper()}")
    print(f"    Duration: {(record.timestamp_end - record.timestamp_start).total_seconds():.2f}s")
    print(f"    Steps executed: {len([e for e in record.step_events if 'COMPLETED' in str(e.event_type)])}")
    
    print(f"\n    Side Effects:")
    if record.side_effects_report:
        for effect in record.side_effects_report.side_effects_observed:
            reversible_str = "✓" if effect.reversible else "✗"
            print(f"      {reversible_str} {effect.category.value}: {effect.description}")
    
    print(f"\n    Security State:")
    print(f"      Pre-execution: {record.security_snapshot_pre.security_state}")
    print(f"      Post-execution: {record.security_snapshot_post.security_state}")
    
    print(f"\n    Immutability: Record hash = {record.get_execution_hash()[:24]}...")


def run_all_examples():
    """Run all examples."""
    print("\n" + "=" * 70)
    print(" EXECUTION OBSERVABILITY - WORKING EXAMPLES")
    print("=" * 70)
    
    examples = [
        example_1_basic_execution_record,
        example_2_failed_execution,
        example_3_side_effects_tracking,
        example_4_security_escalation,
        example_5_rollback_scaffold,
        example_6_execution_summary,
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
