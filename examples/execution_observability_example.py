"""
HEARTH Execution Observability & Rollback Scaffold Examples (Step 19)

Demonstrates:
- Creating execution records
- Recording step events (hash-linked, append-only)
- Recording side effects
- Creating rollback scaffolds (NOT EXECUTED)
- Displaying execution summaries

Key Points:
- Post-execution inspection only
- No automatic recovery
- No retries
- No rollback execution
- Fail-closed
"""

from datetime import datetime
from artemis.execution_observability import (
    ExecutionObserver,
    RollbackPlanner,
    ExecutionStatus,
    StepEventType,
    SideEffectCategory,
    SecuritySnapshot,
)
from artemis.boundary import SecurityState
from core.kernel import HearthKernel
from hestia.agent import HestiaAgent


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def example_1_basic_execution_record():
    """
    Example 1: Create basic execution record.
    
    Shows that:
    - ExecutionObserver records step events
    - Events are hash-linked (append-only)
    - Step statuses are captured
    - Timestamps are recorded
    """
    print_section("Example 1: Basic Execution Record")
    
    # Create kernel and observer
    kernel = HearthKernel()
    observer = ExecutionObserver(
        execution_id="exec-001",
        plan_id="plan-001",
        kernel=kernel,
    )
    
    # Simulate execution
    print("Recording execution steps...")
    
    observer.record_step_started(0, "Initialize", {"input": "test_data"})
    observer.record_step_completed(0, "Initialize", {"output": "initialized"})
    
    observer.record_step_started(1, "Process", {"data": "test_data"})
    observer.record_step_completed(1, "Process", {"result": "processed"})
    
    observer.record_step_started(2, "Validate", {"result": "processed"})
    observer.record_step_completed(2, "Validate", {"valid": True})
    
    observer.mark_completed("All steps completed successfully")
    
    # Get record
    record = observer.get_execution_record("LIVE")
    
    print(f"\nExecution Summary:")
    print(f"  Execution ID: {record.execution_id}")
    print(f"  Plan ID: {record.plan_id}")
    print(f"  Live Mode: {record.live_mode_state}")
    print(f"  Status: {record.status.value}")
    print(f"  Steps: {len(record.step_events)}")
    print(f"  Execution Hash: {record.get_execution_hash()[:16]}...")
    
    print(f"\nStep Events (hash-linked):")
    for i, event in enumerate(record.step_events, 1):
        print(f"  {i}. {event.event_type.value} - Step {event.step_index}: {event.step_name}")
        print(f"     Time: {event.timestamp.strftime('%H:%M:%S')}")
        print(f"     Hash: {event.get_hash()[:16]}...")
        if event.previous_event_hash:
            print(f"     Previous: {event.previous_event_hash[:16]}...")
    
    print("\n✓ Example 1 complete: Execution record created with hash-linked events")


def example_2_execution_failure_and_partial_record():
    """
    Example 2: Execution failure with partial record.
    
    Shows that:
    - Failures are recorded
    - Partial execution is captured
    - Error messages are included
    - Record is still complete
    """
    print_section("Example 2: Execution Failure and Partial Record")
    
    # Create kernel and observer
    kernel = HearthKernel()
    observer = ExecutionObserver(
        execution_id="exec-002",
        plan_id="plan-002",
        kernel=kernel,
    )
    
    # Simulate execution with failure
    print("Recording execution with failure...")
    
    observer.record_step_started(0, "Initialize", {})
    observer.record_step_completed(0, "Initialize", {})
    
    observer.record_step_started(1, "Process", {})
    observer.record_step_failed(
        1,
        "Process",
        "Unexpected error: invalid input format",
        {"input": "malformed_data"}
    )
    
    # Step 2 never started because step 1 failed
    observer.mark_failed("Execution stopped: Step 1 failed")
    
    # Get record
    record = observer.get_execution_record("LIVE")
    
    print(f"\nExecution Summary:")
    print(f"  Status: {record.status.value}")
    print(f"  Steps: {len(record.step_events)}")
    print(f"  Reason: {record.completion_reason}")
    
    print(f"\nStep Events:")
    for i, event in enumerate(record.step_events, 1):
        status_icon = "✓" if event.event_type.value == "step_completed" else "✗"
        print(f"  {status_icon} {i}. {event.event_type.value} - {event.step_name}")
        if event.error_message:
            print(f"     Error: {event.error_message}")
    
    print("\n✓ Example 2 complete: Partial execution recorded with errors")


def example_3_side_effects_tracking():
    """
    Example 3: Track side effects (best-effort observation).
    
    Shows that:
    - Side effects are recorded
    - Categories are tracked
    - Reversibility is noted
    - Observation is best-effort
    """
    print_section("Example 3: Side Effects Tracking")
    
    # Create observer
    kernel = HearthKernel()
    observer = ExecutionObserver(
        execution_id="exec-003",
        plan_id="plan-003",
        kernel=kernel,
    )
    
    # Simulate execution with side effects
    print("Recording execution with side effects...")
    
    observer.record_step_started(0, "Create Files", {})
    observer.record_side_effect(
        SideEffectCategory.FILE_SYSTEM,
        "Created file: /tmp/data.txt",
        reversible=True,
        step_index=0,
    )
    observer.record_side_effect(
        SideEffectCategory.FILE_SYSTEM,
        "Created file: /tmp/backup.db",
        reversible=True,
        step_index=0,
    )
    observer.record_step_completed(0, "Create Files", {})
    
    observer.record_step_started(1, "Modify Configuration", {})
    observer.record_side_effect(
        SideEffectCategory.CONFIGURATION,
        "Modified config: /etc/app.conf",
        reversible=True,
        step_index=1,
    )
    observer.record_step_completed(1, "Modify Configuration", {})
    
    observer.record_step_started(2, "Deploy Service", {})
    observer.record_side_effect(
        SideEffectCategory.SYSTEM,
        "Started system service: myapp-service",
        reversible=True,
        step_index=2,
    )
    observer.record_step_completed(2, "Deploy Service", {})
    
    observer.mark_completed("Execution completed with side effects")
    
    # Get record
    record = observer.get_execution_record("LIVE")
    
    print(f"\nSide Effects Observed:")
    if record.side_effects_report:
        for i, effect in enumerate(record.side_effects_report.side_effects_observed, 1):
            reversible_str = "✓ Reversible" if effect.reversible else "✗ Irreversible"
            print(f"  {i}. [{effect.category.value}] {effect.description}")
            print(f"     {reversible_str} - Step {effect.step_index}")
    
    print("\n✓ Example 3 complete: Side effects tracked and categorized")


def example_4_security_escalation_stops_execution():
    """
    Example 4: Security escalation stops execution.
    
    Shows that:
    - Security snapshots are captured
    - Escalation marks execution INCOMPLETE
    - Partial execution is recorded
    - Status shows security issue
    """
    print_section("Example 4: Security Escalation Stops Execution")
    
    # Create kernel
    kernel = HearthKernel()
    observer = ExecutionObserver(
        execution_id="exec-004",
        plan_id="plan-004",
        kernel=kernel,
    )
    
    # Simulate execution with security escalation
    print("Simulating execution with security escalation...")
    
    observer.record_step_started(0, "Safe Step", {})
    observer.record_step_completed(0, "Safe Step", {})
    
    # Simulate security degradation
    print("  [Security degraded to COMPROMISED]")
    kernel._security_state = SecurityState.COMPROMISED
    
    observer.record_step_started(1, "Dangerous Step", {})
    observer.mark_incomplete_security_escalation("Security state degraded to COMPROMISED")
    
    # Get record
    record = observer.get_execution_record("LIVE")
    
    print(f"\nExecution Summary:")
    print(f"  Status: {record.status.value}")
    print(f"  Reason: {record.completion_reason}")
    print(f"  Steps: {len(record.step_events)}")
    
    print(f"\nSecurity Snapshots:")
    print(f"  Pre-execution: {record.security_snapshot_pre.security_state}")
    print(f"  Post-execution: {record.security_snapshot_post.security_state if record.security_snapshot_post else 'N/A'}")
    
    print("\n✓ Example 4 complete: Security escalation recorded as INCOMPLETE execution")


def example_5_rollback_scaffold_not_executed():
    """
    Example 5: Create rollback scaffold (NOT EXECUTED).
    
    Shows that:
    - Rollback hints are surfaced (verbatim from plan)
    - Irreversible steps are marked
    - Rollback is NOT executed
    - Manual guidance is provided
    """
    print_section("Example 5: Rollback Scaffold (NOT EXECUTED)")
    
    # Create observer
    kernel = HearthKernel()
    observer = ExecutionObserver(
        execution_id="exec-005",
        plan_id="plan-005",
        kernel=kernel,
    )
    
    # Simulate execution
    observer.record_step_started(0, "Create Database", {})
    observer.record_step_completed(0, "Create Database", {})
    
    observer.record_step_started(1, "Load Data", {})
    observer.record_step_failed(
        1,
        "Load Data",
        "Constraint violation: duplicate key",
        {}
    )
    
    observer.mark_failed("Execution stopped: Data load failed")
    
    # Get record
    record = observer.get_execution_record("LIVE")
    
    # Create rollback hints from plan
    rollback_hints_from_plan = [
        {
            "step_index": 0,
            "description": "Drop database if needed",
            "actions": [
                "DROP DATABASE test_db CASCADE;",
                "Verify no active connections",
            ],
            "risks": [
                "Irreversible - all data lost",
                "May take time to drop large databases",
            ],
        }
    ]
    
    # Plan rollback (NOT EXECUTED)
    rollback_scaffold = RollbackPlanner.plan_rollback(
        record,
        rollback_hints_from_plan
    )
    
    print(f"\nRollback Scaffold Summary:")
    print(f"  Execution ID: {rollback_scaffold.execution_id}")
    print(f"  Is Rollback Possible: {rollback_scaffold.is_rollback_possible}")
    print(f"  Reason: {rollback_scaffold.reason}")
    
    if rollback_scaffold.rollback_hints:
        print(f"\n  Rollback Hints (from plan, VERBATIM):")
        for i, hint in enumerate(rollback_scaffold.rollback_hints, 1):
            print(f"    {i}. {hint.description}")
            print(f"       Actions: {hint.actions}")
    
    if rollback_scaffold.warnings:
        print(f"\n  Warnings:")
        for warning in rollback_scaffold.warnings:
            print(f"    ⚠️  {warning}")
    
    print("\n  Status: Rollback NOT executed - manual only")
    
    print("\n✓ Example 5 complete: Rollback scaffold created (manual, not executed)")


def example_6_hestia_execution_display():
    """
    Example 6: Display execution with Hestia UI.
    
    Shows that:
    - Hestia displays execution summary
    - Irreversible actions are highlighted
    - Rollback guidance is clear
    - All display, no automation
    """
    print_section("Example 6: Hestia Execution Display")
    
    # Create kernel, observer, and agent
    kernel = HearthKernel()
    observer = ExecutionObserver(
        execution_id="exec-006",
        plan_id="plan-006",
        kernel=kernel,
    )
    agent = HestiaAgent(kernel=kernel)
    
    # Simulate execution
    print("Simulating execution...")
    
    observer.record_step_started(0, "Initialize", {})
    observer.record_step_completed(0, "Initialize", {})
    
    observer.record_step_started(1, "Process", {})
    observer.record_step_completed(1, "Process", {})
    
    observer.record_step_started(2, "Finalize", {})
    observer.record_step_completed(2, "Finalize", {})
    
    observer.mark_completed("Execution completed")
    
    # Get record
    record = observer.get_execution_record("LIVE")
    
    # Display via Hestia
    print("\nExecution Summary via Hestia:")
    summary = agent.display_execution_summary(record)
    print(summary)
    
    print("\nIrreversible Actions:")
    irreversible = agent.show_irreversible_actions(record)
    print(irreversible)
    
    # Rollback guidance
    rollback_scaffold = RollbackPlanner.plan_rollback(record, [])
    
    print("\nRollback Guidance:")
    guidance = agent.show_rollback_guidance(rollback_scaffold)
    print(guidance)
    
    print("\n✓ Example 6 complete: Hestia displays execution results (no automation)")


def run_all_examples():
    """Run all execution observability examples."""
    examples = [
        example_1_basic_execution_record,
        example_2_execution_failure_and_partial_record,
        example_3_side_effects_tracking,
        example_4_security_escalation_stops_execution,
        example_5_rollback_scaffold_not_executed,
        example_6_hestia_execution_display,
    ]
    
    print("=" * 70)
    print(" HEARTH EXECUTION OBSERVABILITY & ROLLBACK SCAFFOLD EXAMPLES (Step 19)")
    print("=" * 70)
    print("\nDemonstrating post-execution inspection and rollback guidance.")
    print("No automation, no retries, no rollback execution.")
    
    for i, example_func in enumerate(examples, 1):
        try:
            example_func()
            print()
        except Exception as e:
            print(f"\n✗ Example {i} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(" ALL EXAMPLES COMPLETE")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("1. ExecutionObserver records step events (hash-linked, append-only)")
    print("2. Side effects are tracked with category and reversibility")
    print("3. Security snapshots capture state before and after execution")
    print("4. RollbackScaffold surfaces hints (NOT executed)")
    print("5. Hestia displays all results for manual review")
    print("6. No automation, no retries, no background execution")
    print("=" * 70)


if __name__ == "__main__":
    run_all_examples()
