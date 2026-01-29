"""
HEARTH DRY RUN EXAMPLES

# Dry-run only
# No execution
# No authority transfer
# Inspection only

Demonstrates the full governance loop in dry-run mode:
1. Successful approval flow
2. Compilation failure
3. Approval rejection
4. Lockdown blocking

NO EXECUTION PERFORMED IN ANY EXAMPLE.
"""

from artemis.dry_run import DryRunController, DryRunReport
from hestia.agent import HestiaAgent
from core.kernel import Kernel


# ============================================================================
# EXAMPLE 1: SUCCESSFUL APPROVAL FLOW (DRY RUN)
# ============================================================================

def example_successful_approval_dry_run():
    """
    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only

    Demonstrate a successful governance loop WITHOUT execution.
    """
    print("=" * 70)
    print("EXAMPLE 1: SUCCESSFUL APPROVAL FLOW (DRY RUN)")
    print("=" * 70)
    print()

    # Initialize kernel and agent
    kernel = Kernel()
    kernel.boot()
    
    agent = HestiaAgent(kernel=kernel)

    # Create dry-run controller
    controller = DryRunController(kernel=kernel, agent=agent)

    # User intent
    user_intent = "Analyze my activity from last week and remember insights"

    # Mocked LLM output (with explicit step markers)
    mocked_llm_output = """
I will help you analyze your activity and remember insights.

PLAN_START
STEP_1: Retrieve user's last week of activity from Knowledge Store
STEP_2: Analyze activity patterns for health insights
STEP_3: Store insights in user's health memory
PLAN_END

This plan will retrieve your activity data, analyze it for patterns,
and save the insights to your memory for future reference.
"""

    # Run full loop in dry-run mode
    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only
    report = controller.run_full_loop(
        user_intent=user_intent,
        mocked_llm_output=mocked_llm_output,
        auto_approve=True,  # Auto-approve for demo
        approver_identity="demo-user@example.com",
    )

    # Display report
    print(report.to_human_text())
    print()
    print(f"⚠ EXECUTION PERFORMED: {report.execution_performed}")
    print(f"⚠ {report.explicit_statement}")
    print()


# ============================================================================
# EXAMPLE 2: COMPILATION FAILURE
# ============================================================================

def example_compilation_failure():
    """
    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only

    Demonstrate what happens when plan compilation fails.
    """
    print("=" * 70)
    print("EXAMPLE 2: COMPILATION FAILURE")
    print("=" * 70)
    print()

    # Initialize kernel and agent
    kernel = Kernel()
    kernel.boot()
    
    agent = HestiaAgent(kernel=kernel)

    # Create dry-run controller
    controller = DryRunController(kernel=kernel, agent=agent)

    # User intent
    user_intent = "Do something complex"

    # Mocked LLM output WITHOUT explicit markers (will fail parsing)
    mocked_llm_output = """
I will help you with your request.

1. First, I'll do this
2. Then, I'll do that
3. Finally, I'll do the other thing

This should work fine!
"""

    # Run full loop in dry-run mode
    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only
    report = controller.run_full_loop(
        user_intent=user_intent,
        mocked_llm_output=mocked_llm_output,
        auto_approve=True,
    )

    # Display report
    print(report.to_human_text())
    print()
    print(f"⚠ Failed at: {report.failure_step}")
    print(f"⚠ Reason: {report.failure_reason}")
    print(f"⚠ EXECUTION PERFORMED: {report.execution_performed}")
    print()


# ============================================================================
# EXAMPLE 3: APPROVAL REJECTION
# ============================================================================

def example_approval_rejection():
    """
    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only

    Demonstrate what happens when user rejects the plan.
    """
    print("=" * 70)
    print("EXAMPLE 3: APPROVAL REJECTION")
    print("=" * 70)
    print()

    # Initialize kernel and agent
    kernel = Kernel()
    kernel.boot()
    
    agent = HestiaAgent(kernel=kernel)

    # Create dry-run controller
    controller = DryRunController(kernel=kernel, agent=agent)

    # User intent
    user_intent = "Delete all my old notes"

    # Mocked LLM output
    mocked_llm_output = """
I will help you delete old notes.

PLAN_START
STEP_1: Query Knowledge Store for notes older than 1 year
STEP_2: Delete all matching notes
PLAN_END

This plan will permanently remove notes older than 1 year.
"""

    # Run full loop in dry-run mode with auto_approve=False
    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only
    report = controller.run_full_loop(
        user_intent=user_intent,
        mocked_llm_output=mocked_llm_output,
        auto_approve=False,  # User rejects
        approver_identity="demo-user@example.com",
    )

    # Display report
    print(report.to_human_text())
    print()
    print(f"⚠ Approval Granted: {report.approval_granted}")
    print(f"⚠ Reason: {report.approval_reason}")
    print(f"⚠ EXECUTION PERFORMED: {report.execution_performed}")
    print()


# ============================================================================
# EXAMPLE 4: LOCKDOWN BLOCKING APPROVAL
# ============================================================================

def example_lockdown_blocking():
    """
    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only

    Demonstrate what happens when system is in LOCKDOWN.
    """
    print("=" * 70)
    print("EXAMPLE 4: LOCKDOWN BLOCKING APPROVAL")
    print("=" * 70)
    print()

    # Initialize kernel and agent
    kernel = Kernel()
    kernel.boot()
    
    # Trigger LOCKDOWN
    from artemis.kill_switch import KillSwitch
    kill_switch = KillSwitch(kernel=kernel)
    kill_switch.engage(reason="Demonstration of LOCKDOWN blocking")
    
    agent = HestiaAgent(kernel=kernel)

    # Create dry-run controller
    controller = DryRunController(kernel=kernel, agent=agent)

    # User intent
    user_intent = "Show me my recent notes"

    # Mocked LLM output
    mocked_llm_output = """
I will help you view your recent notes.

PLAN_START
STEP_1: Query Knowledge Store for recent notes
STEP_2: Format and display results
PLAN_END

This plan will retrieve and display your recent notes.
"""

    # Run full loop in dry-run mode
    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only
    report = controller.run_full_loop(
        user_intent=user_intent,
        mocked_llm_output=mocked_llm_output,
        auto_approve=True,  # Try to approve
        approver_identity="demo-user@example.com",
    )

    # Display report
    print(report.to_human_text())
    print()
    print(f"⚠ Security State at Execution Check: {report.security_summary_at_execution_check.get('state')}")
    print(f"⚠ Validation Would Pass: {report.execution_validation_passed}")
    print(f"⚠ Validation Message: {report.execution_validation_message}")
    print(f"⚠ EXECUTION PERFORMED: {report.execution_performed}")
    print()


# ============================================================================
# EXAMPLE 5: IMMUTABILITY VERIFICATION
# ============================================================================

def example_immutability_verification():
    """
    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only

    Verify that DryRunReport is immutable.
    """
    print("=" * 70)
    print("EXAMPLE 5: IMMUTABILITY VERIFICATION")
    print("=" * 70)
    print()

    # Initialize kernel and agent
    kernel = Kernel()
    kernel.boot()
    
    agent = HestiaAgent(kernel=kernel)

    # Create dry-run controller
    controller = DryRunController(kernel=kernel, agent=agent)

    # User intent
    user_intent = "Test immutability"

    # Mocked LLM output
    mocked_llm_output = """
PLAN_START
STEP_1: Test step
PLAN_END
"""

    # Run dry-run
    report = controller.run_full_loop(
        user_intent=user_intent,
        mocked_llm_output=mocked_llm_output,
        auto_approve=True,
    )

    print(f"Original report ID: {report.dry_run_id}")
    print(f"Execution performed: {report.execution_performed}")
    print()

    # Try to mutate (should fail)
    print("Attempting to mutate report...")
    try:
        object.__setattr__(report, "execution_performed", True)
        print("✗ SECURITY ISSUE: Report is mutable!")
    except (AttributeError, TypeError) as e:
        print(f"✓ Report is properly frozen (immutable): {type(e).__name__}")

    print()


# ============================================================================
# EXAMPLE 6: COMPARE APPROVED VS REJECTED
# ============================================================================

def example_compare_approved_vs_rejected():
    """
    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only

    Compare approved vs rejected flows side-by-side.
    """
    print("=" * 70)
    print("EXAMPLE 6: COMPARE APPROVED VS REJECTED")
    print("=" * 70)
    print()

    # Initialize kernel and agent
    kernel = Kernel()
    kernel.boot()
    
    agent = HestiaAgent(kernel=kernel)
    controller = DryRunController(kernel=kernel, agent=agent)

    # Same intent and LLM output
    user_intent = "Show me my notes"
    mocked_llm_output = """
PLAN_START
STEP_1: Query Knowledge Store for notes
STEP_2: Display results
PLAN_END
"""

    # Run with approval
    report_approved = controller.run_full_loop(
        user_intent=user_intent,
        mocked_llm_output=mocked_llm_output,
        auto_approve=True,
    )

    # Run with rejection
    report_rejected = controller.run_full_loop(
        user_intent=user_intent,
        mocked_llm_output=mocked_llm_output,
        auto_approve=False,
    )

    print("APPROVED FLOW:")
    print(f"  Approval Granted: {report_approved.approval_granted}")
    print(f"  Execution Request Built: {report_approved.execution_request_built}")
    print(f"  Validation Would Pass: {report_approved.execution_validation_passed}")
    print(f"  Execution Performed: {report_approved.execution_performed}")
    print()

    print("REJECTED FLOW:")
    print(f"  Approval Granted: {report_rejected.approval_granted}")
    print(f"  Execution Request Built: {report_rejected.execution_request_built}")
    print(f"  Validation Would Pass: {report_rejected.execution_validation_passed}")
    print(f"  Execution Performed: {report_rejected.execution_performed}")
    print()

    print(f"⚠ NEITHER FLOW EXECUTED ANYTHING")
    print()


if __name__ == "__main__":
    example_successful_approval_dry_run()
    example_compilation_failure()
    example_approval_rejection()
    example_lockdown_blocking()
    example_immutability_verification()
    example_compare_approved_vs_rejected()

    print("=" * 70)
    print("All dry-run examples completed")
    print("⚠ NO EXECUTION PERFORMED IN ANY EXAMPLE")
    print("=" * 70)
