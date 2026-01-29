"""
HEARTH Live Mode Gate Examples

Demonstrates the explicit execution authority gate that controls
whether approved plans can be executed.

Key Principles:
- Default state: DRY_RUN (fail-closed)
- Explicit enable/disable with reason and user identity
- Auto-revert to DRY_RUN on security degradation
- Immutable audit trail for all transitions
- No automation, no timers, no persistence

Examples:
1. Default DRY_RUN blocking execution
2. Enable LIVE mode and execute
3. Auto-revert on security degradation
4. Manual disable after execution
5. Transition history audit
6. Integration with Hestia UI
"""

from datetime import datetime
from artemis.live_mode_gate import LiveModeGate, LiveModeState, LiveModeGateValidator
from artemis.plan_compiler import PlanCompiler, PlanDraft
from artemis.approval_executor import ApprovalExecutor, ExecutionRequest
from hestia.agent import HestiaAgent
from core.kernel import Kernel


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def example_1_default_dry_run_blocks_execution():
    """
    Example 1: Default DRY_RUN state blocks execution.
    
    Shows that:
    - LiveModeGate defaults to DRY_RUN
    - ApprovalExecutor refuses execution when gate is DRY_RUN
    - Audit trail records the gate block
    - No commands are executed
    """
    print_section("Example 1: Default DRY_RUN Blocks Execution")
    
    # Create kernel and gate
    kernel = Kernel()
    gate = LiveModeGate(kernel=kernel)
    
    print(f"Initial gate state: {gate.get_state().value}")
    print(f"Is live: {gate.is_live()}")
    print(f"Is dry run: {gate.is_dry_run()}")
    
    # Create plan compiler and approval executor
    compiler = PlanCompiler(kernel=kernel)
    executor = ApprovalExecutor(
        stage4_orchestrator=None,
        kernel=kernel,
        live_mode_gate=gate,  # Gate is DRY_RUN
    )
    
    # Create a simple plan
    goal = "List files in current directory"
    reasoning = "Testing gate enforcement"
    
    plan_draft = compiler.compile_plan(
        goal=goal,
        reasoning=reasoning,
        proposed_steps=[
            {"action": "shell", "command": "ls -la"}
        ],
    )
    
    if not plan_draft.compilation_success:
        print(f"ERROR: Plan compilation failed: {plan_draft.error_message}")
        return
    
    print(f"\nPlan compiled successfully:")
    print(f"  Goal: {plan_draft.goal}")
    print(f"  Steps: {len(plan_draft.steps)}")
    
    # Create execution request
    # User has approved the plan
    execution_request = ExecutionRequest(
        execution_id="exec-001",
        plan_id=plan_draft.plan_id,
        approved_by="user@example.com",
        approval_timestamp=datetime.now(),
        plan_hash=plan_draft.plan_hash,
    )
    
    # Attempt execution
    print("\nAttempting execution with DRY_RUN gate...")
    success, message, results = executor.execute(execution_request)
    
    print(f"\nExecution result:")
    print(f"  Success: {success}")
    print(f"  Message: {message}")
    print(f"  Results: {results}")
    
    # Check audit trail
    audit_entries = executor.get_audit_trail()
    print(f"\nAudit trail entries: {len(audit_entries)}")
    for entry in audit_entries:
        print(f"  - {entry.event_type}: {entry.details}")
    
    print("\n✓ Example 1 complete: Execution blocked by DRY_RUN gate")


def example_2_enable_live_and_execute():
    """
    Example 2: Enable LIVE mode and execute.
    
    Shows that:
    - enable_live() requires reason and user identity
    - Transition is recorded in audit trail
    - ApprovalExecutor allows execution when gate is LIVE
    - Gate records all state changes
    """
    print_section("Example 2: Enable LIVE Mode and Execute")
    
    # Create kernel and gate
    kernel = Kernel()
    gate = LiveModeGate(kernel=kernel)
    
    print(f"Initial state: {gate.get_state().value}")
    
    # Attempt to enable live mode
    print("\nEnabling live mode...")
    success, message = gate.enable_live(
        reason="Testing live mode execution",
        user_identity="alice@example.com",
    )
    
    print(f"Enable result:")
    print(f"  Success: {success}")
    print(f"  Message: {message}")
    print(f"  New state: {gate.get_state().value}")
    
    if not success:
        print("ERROR: Failed to enable live mode")
        return
    
    # Create plan compiler and approval executor
    compiler = PlanCompiler(kernel=kernel)
    executor = ApprovalExecutor(
        stage4_orchestrator=None,
        kernel=kernel,
        live_mode_gate=gate,  # Gate is now LIVE
    )
    
    # Create a simple plan
    goal = "Echo a test message"
    reasoning = "Testing live mode execution"
    
    plan_draft = compiler.compile_plan(
        goal=goal,
        reasoning=reasoning,
        proposed_steps=[
            {"action": "shell", "command": "echo 'Live mode test'"}
        ],
    )
    
    if not plan_draft.compilation_success:
        print(f"ERROR: Plan compilation failed: {plan_draft.error_message}")
        return
    
    print(f"\nPlan compiled successfully:")
    print(f"  Goal: {plan_draft.goal}")
    print(f"  Steps: {len(plan_draft.steps)}")
    
    # Create execution request
    execution_request = ExecutionRequest(
        execution_id="exec-002",
        plan_id=plan_draft.plan_id,
        approved_by="alice@example.com",
        approval_timestamp=datetime.now(),
        plan_hash=plan_draft.plan_hash,
    )
    
    # Attempt execution
    print("\nAttempting execution with LIVE gate...")
    success, message, results = executor.execute(execution_request)
    
    print(f"\nExecution result:")
    print(f"  Success: {success}")
    print(f"  Message: {message}")
    
    # Check transition history
    transitions = gate.get_transition_history()
    print(f"\nGate transition history: {len(transitions)} transitions")
    for t in transitions:
        print(f"  {t.timestamp.strftime('%H:%M:%S')}: "
              f"{t.from_state.value} → {t.to_state.value}")
        print(f"    Reason: {t.reason}")
        print(f"    User: {t.user_identity}")
    
    print("\n✓ Example 2 complete: Live mode enabled and execution allowed")


def example_3_auto_revert_on_security_degradation():
    """
    Example 3: Auto-revert to DRY_RUN on security degradation.
    
    Shows that:
    - Gate monitors security state before enabling
    - COMPROMISED or LOCKDOWN triggers auto-revert
    - Auto-revert is recorded in audit trail with automatic=True
    - Execution is blocked after auto-revert
    """
    print_section("Example 3: Auto-Revert on Security Degradation")
    
    # Create kernel and gate
    kernel = Kernel()
    gate = LiveModeGate(kernel=kernel)
    
    # Enable live mode
    print("Enabling live mode...")
    success, message = gate.enable_live(
        reason="Testing auto-revert",
        user_identity="bob@example.com",
    )
    print(f"  State: {gate.get_state().value}")
    
    # Simulate security degradation
    print("\nSimulating security degradation to COMPROMISED...")
    from artemis.boundary import SecurityState
    kernel._security_state = SecurityState.COMPROMISED
    
    # Check security and revert if needed
    print("Checking security state...")
    reverted = gate.check_security_and_revert_if_needed()
    
    print(f"\nAuto-revert result:")
    print(f"  Reverted: {reverted}")
    print(f"  New state: {gate.get_state().value}")
    
    # Check transition history
    transitions = gate.get_transition_history()
    print(f"\nTransition history: {len(transitions)} transitions")
    for t in transitions:
        auto_flag = " [AUTO]" if t.automatic else ""
        print(f"  {t.from_state.value} → {t.to_state.value}{auto_flag}")
        print(f"    Reason: {t.reason}")
    
    # Try to execute (should be blocked)
    compiler = PlanCompiler(kernel=kernel)
    executor = ApprovalExecutor(
        stage4_orchestrator=None,
        kernel=kernel,
        live_mode_gate=gate,  # Gate is now DRY_RUN (auto-reverted)
    )
    
    plan_draft = compiler.compile_plan(
        goal="Test execution after revert",
        reasoning="Should be blocked",
        proposed_steps=[
            {"action": "shell", "command": "echo 'Should not execute'"}
        ],
    )
    
    execution_request = ExecutionRequest(
        execution_id="exec-003",
        plan_id=plan_draft.plan_id,
        approved_by="bob@example.com",
        approval_timestamp=datetime.now(),
        plan_hash=plan_draft.plan_hash,
    )
    
    print("\nAttempting execution after auto-revert...")
    success, message, results = executor.execute(execution_request)
    
    print(f"Execution result:")
    print(f"  Success: {success}")
    print(f"  Message: {message}")
    
    print("\n✓ Example 3 complete: Auto-revert prevented execution")


def example_4_manual_disable_after_execution():
    """
    Example 4: Manually disable LIVE mode after execution.
    
    Shows that:
    - disable_live() requires reason and user identity
    - Manual disable is recorded with automatic=False
    - Good practice: disable after completing execution
    """
    print_section("Example 4: Manual Disable After Execution")
    
    # Create kernel and gate
    kernel = Kernel()
    gate = LiveModeGate(kernel=kernel)
    
    # Enable live mode
    print("Enabling live mode...")
    gate.enable_live(
        reason="Execute specific task",
        user_identity="charlie@example.com",
    )
    print(f"  State: {gate.get_state().value}")
    
    # Execute something (simplified)
    print("\nExecuting task...")
    print("  [Task execution would happen here]")
    
    # Disable live mode after execution
    print("\nDisabling live mode after task completion...")
    success, message = gate.disable_live(
        reason="Task complete, returning to safe mode",
        user_identity="charlie@example.com",
        automatic=False,
    )
    
    print(f"Disable result:")
    print(f"  Success: {success}")
    print(f"  Message: {message}")
    print(f"  New state: {gate.get_state().value}")
    
    # Check transition history
    transitions = gate.get_transition_history()
    print(f"\nTransition history: {len(transitions)} transitions")
    for t in transitions:
        auto_flag = " [AUTO]" if t.automatic else " [MANUAL]"
        print(f"  {t.timestamp.strftime('%H:%M:%S')}: "
              f"{t.from_state.value} → {t.to_state.value}{auto_flag}")
        print(f"    Reason: {t.reason}")
        print(f"    User: {t.user_identity}")
    
    print("\n✓ Example 4 complete: Manual disable recorded")


def example_5_transition_history_audit():
    """
    Example 5: Examining transition history for audit.
    
    Shows that:
    - All transitions are recorded immutably
    - History includes timestamp, states, reason, user, automatic flag
    - Audit trail is complete and tamper-evident
    """
    print_section("Example 5: Transition History Audit")
    
    # Create kernel and gate
    kernel = Kernel()
    gate = LiveModeGate(kernel=kernel)
    
    # Perform several transitions
    print("Performing multiple transitions...")
    
    # Transition 1: Enable
    gate.enable_live("Initial test", "alice@example.com")
    
    # Transition 2: Disable
    gate.disable_live("Test complete", "alice@example.com", automatic=False)
    
    # Transition 3: Enable again
    gate.enable_live("Second test", "bob@example.com")
    
    # Transition 4: Auto-revert (simulate)
    kernel._security_state = kernel._security_state.__class__.COMPROMISED
    gate.check_security_and_revert_if_needed()
    
    # Transition 5: Manual enable after recovery
    kernel._security_state = kernel._security_state.__class__.OPERATIONAL
    gate.enable_live("Security recovered", "admin@example.com")
    
    # Transition 6: Final disable
    gate.disable_live("End of session", "admin@example.com", automatic=False)
    
    # Display complete audit trail
    transitions = gate.get_transition_history()
    print(f"\nComplete transition history: {len(transitions)} transitions")
    print("-" * 70)
    
    for i, t in enumerate(transitions, 1):
        print(f"\nTransition {i}:")
        print(f"  Timestamp: {t.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  From: {t.from_state.value}")
        print(f"  To: {t.to_state.value}")
        print(f"  Reason: {t.reason}")
        print(f"  User: {t.user_identity}")
        print(f"  Automatic: {t.automatic}")
    
    print("\n" + "-" * 70)
    print("\n✓ Example 5 complete: Audit trail is complete and immutable")


def example_6_hestia_ui_integration():
    """
    Example 6: Integration with Hestia UI layer.
    
    Shows that:
    - Hestia provides user-friendly gate control methods
    - Status display shows current state and recent history
    - Consequences explanation helps users understand risks
    - Enable/disable methods provide clear feedback
    """
    print_section("Example 6: Hestia UI Integration")
    
    # Create kernel, gate, and agent
    kernel = Kernel()
    gate = LiveModeGate(kernel=kernel)
    agent = HestiaAgent(kernel=kernel)
    
    # Display initial status
    print("Initial status:")
    status = agent.display_live_mode_status(gate)
    print(status)
    
    # Show consequences explanation
    print("\nRequesting consequences explanation...")
    consequences = agent.explain_live_mode_consequences()
    print(consequences[:500] + "...\n[Explanation truncated for brevity]")
    
    # Enable live mode via Hestia
    print("\nEnabling live mode via Hestia...")
    success, message = agent.enable_live_mode(
        live_mode_gate=gate,
        reason="Production deployment",
        user_identity="operator@example.com",
    )
    print(f"\n{message}")
    
    # Display status after enable
    print("\nStatus after enable:")
    status = agent.display_live_mode_status(gate)
    print(status)
    
    # Disable live mode via Hestia
    print("\nDisabling live mode via Hestia...")
    success, message = agent.disable_live_mode(
        live_mode_gate=gate,
        reason="Deployment complete",
        user_identity="operator@example.com",
    )
    print(f"\n{message}")
    
    # Display final status
    print("\nFinal status:")
    status = agent.display_live_mode_status(gate)
    print(status)
    
    print("\n✓ Example 6 complete: Hestia UI integration demonstrated")


def run_all_examples():
    """Run all live mode gate examples."""
    examples = [
        example_1_default_dry_run_blocks_execution,
        example_2_enable_live_and_execute,
        example_3_auto_revert_on_security_degradation,
        example_4_manual_disable_after_execution,
        example_5_transition_history_audit,
        example_6_hestia_ui_integration,
    ]
    
    print("=" * 70)
    print(" HEARTH LIVE MODE GATE EXAMPLES")
    print("=" * 70)
    print("\nDemonstrating explicit execution authority gate control.")
    print("Default state: DRY_RUN (fail-closed)")
    print("Execution: Opt-in, explicit, audited")
    
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
    print("1. LiveModeGate defaults to DRY_RUN (fail-closed)")
    print("2. Execution requires explicit enable_live() with reason and user")
    print("3. Security degradation triggers automatic revert to DRY_RUN")
    print("4. All transitions are recorded immutably")
    print("5. Hestia provides user-friendly gate control")
    print("6. No automation, no timers, no persistence")
    print("=" * 70)


if __name__ == "__main__":
    run_all_examples()
