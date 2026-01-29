"""
HESTIA UI LAYER EXAMPLES

Demonstrates the human-facing UX layer for approval and plan presentation.

# UX only
# No authority
# No execution
# No autonomy

Shows:
1. Converting plans into human-readable presentations
2. Factual approval prompts (no persuasion)
3. Hestia's authority boundaries
4. User approval flow
"""

from datetime import datetime
from hestia.ui_layer import (
    PlanPresentation,
    StepPresentation,
    ApprovalPromptBuilder,
    AuthorityFlowValidator,
    HestiaUIBoundary,
    ApprovalDecision,
)
from artemis.plan_compiler import PlanDraft, PlanStep, StepType, StepFaculty


# ============================================================================
# EXAMPLE 1: Simple Plan Presentation
# ============================================================================

def example_simple_presentation():
    """
    # UX only
    # No authority
    # No execution
    # No autonomy

    Convert a simple PlanDraft into human-readable form.
    """
    print("=" * 70)
    print("EXAMPLE 1: Simple Plan Presentation")
    print("=" * 70)
    print()

    # Create steps
    step1 = StepPresentation(
        sequence=1,
        description="Retrieve user's last week of activity from Knowledge Store",
        faculty="knowledge_retrieval",
        data_accessed=["KnowledgeStore:activity_log"],
        capabilities_required=["read:knowledge", "list:knowledge"],
        estimated_duration_sec=2.0,
        irreversible=False,
    )

    step2 = StepPresentation(
        sequence=2,
        description="Analyze activity patterns for health insights",
        faculty="analysis",
        data_accessed=["activity_log", "health_metrics"],
        capabilities_required=["analyze:health"],
        estimated_duration_sec=3.0,
        irreversible=False,
    )

    step3 = StepPresentation(
        sequence=3,
        description="Store insights in user's health memory",
        faculty="memory_write",
        data_accessed=["MemoryStore:health_insights"],
        capabilities_required=["write:memory", "create:memory"],
        estimated_duration_sec=1.0,
        irreversible=False,
    )

    # Create presentation
    plan_pres = PlanPresentation(
        plan_id="plan-001",
        user_intent="Analyze my activity from last week and remember insights",
        summary="Analyze weekly activity and save insights",
        steps=(step1, step2, step3),
        faculties_involved=("knowledge_retrieval", "analysis", "memory_write"),
        data_sources_accessed=("Knowledge Store", "Health Metrics", "User Memory"),
        capabilities_required=("read:knowledge", "analyze:health", "write:memory"),
        estimated_total_duration_sec=6.0,
        estimated_risk_level="low",
        security_posture_snapshot={"state": "SECURE", "explanation": "All systems normal"},
        irreversible_actions=(),  # Read-only and append-only (reversible)
        assumptions=(
            "Knowledge Store contains activity data from last week",
            "User has health metrics available",
            "User memory store is writable",
        ),
        presentation_timestamp=datetime.utcnow().isoformat() + "Z",
    )

    # Display as human text
    print(plan_pres.to_human_text())
    print()


# ============================================================================
# EXAMPLE 2: High-Risk Plan with Irreversible Actions
# ============================================================================

def example_high_risk_presentation():
    """
    # UX only
    # No authority
    # No execution
    # No autonomy

    Example of a plan with irreversible actions and high risk.
    """
    print("=" * 70)
    print("EXAMPLE 2: High-Risk Plan with Irreversible Actions")
    print("=" * 70)
    print()

    # Create steps with some irreversible
    step1 = StepPresentation(
        sequence=1,
        description="Retrieve user's code repository index",
        faculty="code_retrieval",
        data_accessed=["CodeRepository:files", "CodeRepository:metadata"],
        capabilities_required=["read:repository"],
        estimated_duration_sec=1.0,
        irreversible=False,
    )

    step2 = StepPresentation(
        sequence=2,
        description="CREATE BACKUP: Archive current code version",
        faculty="code_execute",
        data_accessed=["CodeRepository:all_files"],
        capabilities_required=["backup:repository"],
        estimated_duration_sec=5.0,
        irreversible=True,  # Creates new backup (change of state)
    )

    step3 = StepPresentation(
        sequence=3,
        description="MODIFY FILES: Apply formatting changes to all Python files",
        faculty="code_execute",
        data_accessed=["CodeRepository:all_files"],
        capabilities_required=["write:repository", "execute:refactor"],
        estimated_duration_sec=10.0,
        irreversible=True,  # Modifies files (irreversible)
    )

    # Create presentation
    plan_pres = PlanPresentation(
        plan_id="plan-high-risk-001",
        user_intent="Format and backup my code repository",
        summary="Backup and reformat code repository",
        steps=(step1, step2, step3),
        faculties_involved=("code_retrieval", "code_execute"),
        data_sources_accessed=("Code Repository",),
        capabilities_required=("read:repository", "backup:repository", "write:repository", "execute:refactor"),
        estimated_total_duration_sec=16.0,
        estimated_risk_level="high",
        security_posture_snapshot={"state": "SECURE", "explanation": "All systems normal"},
        irreversible_actions=(
            "CREATE BACKUP: Archive current code version",
            "MODIFY FILES: Apply formatting changes to all Python files",
        ),
        assumptions=(
            "Code repository is accessible",
            "All files are valid Python",
            "Backup location has sufficient storage",
            "Formatting tool works correctly",
        ),
        presentation_timestamp=datetime.utcnow().isoformat() + "Z",
    )

    print(plan_pres.to_human_text())
    print()


# ============================================================================
# EXAMPLE 3: Factual Approval Prompt (No Persuasion)
# ============================================================================

def example_approval_prompt():
    """
    # UX only
    # No authority
    # No execution
    # No autonomy

    Generate a factual approval prompt without persuasion or alarmism.
    """
    print("=" * 70)
    print("EXAMPLE 3: Factual Approval Prompt")
    print("=" * 70)
    print()

    # Create a simple plan
    step1 = StepPresentation(
        sequence=1,
        description="Query Knowledge Store for recent notes",
        faculty="knowledge_retrieval",
        data_accessed=["KnowledgeStore:recent_notes"],
        capabilities_required=["read:knowledge"],
        estimated_duration_sec=1.0,
        irreversible=False,
    )

    plan_pres = PlanPresentation(
        plan_id="plan-approval-test",
        user_intent="Show me my recent notes",
        summary="Retrieve recent notes from Knowledge Store",
        steps=(step1,),
        faculties_involved=("knowledge_retrieval",),
        data_sources_accessed=("Knowledge Store",),
        capabilities_required=("read:knowledge",),
        estimated_total_duration_sec=1.0,
        estimated_risk_level="low",
        security_posture_snapshot={"state": "SECURE", "explanation": "All systems normal"},
        irreversible_actions=(),
        assumptions=(
            "Knowledge Store is available",
            "You have recent notes stored",
        ),
        presentation_timestamp=datetime.utcnow().isoformat() + "Z",
    )

    # Build approval prompt
    security_summary = plan_pres.security_posture_snapshot
    prompt = ApprovalPromptBuilder.build_prompt(plan_pres, security_summary)

    print(prompt)
    print()


# ============================================================================
# EXAMPLE 4: Rejection Explanation
# ============================================================================

def example_rejection_explanation():
    """
    # UX only
    # No authority
    # No execution
    # No autonomy

    Generate human-readable explanation for plan rejection.
    """
    print("=" * 70)
    print("EXAMPLE 4: Rejection Explanation")
    print("=" * 70)
    print()

    reasons = [
        "System is in LOCKDOWN (security incident detected)",
        "Plan requires write:repository capability which you don't have",
        "Knowledge Store is currently unavailable",
    ]

    for reason in reasons:
        explanation = ApprovalPromptBuilder.build_rejection_explanation(reason)
        print(f"Rejection Reason: {reason}")
        print()
        print(explanation)
        print()


# ============================================================================
# EXAMPLE 5: Authority Boundaries Display
# ============================================================================

def example_authority_boundaries():
    """
    # UX only
    # No authority
    # No execution
    # No autonomy

    Display what Hestia can and cannot do.
    """
    print("=" * 70)
    print("EXAMPLE 5: Authority Boundaries")
    print("=" * 70)
    print()

    boundaries = HestiaUIBoundary.display_authority_constraints()
    print(boundaries)


# ============================================================================
# EXAMPLE 6: Authority Flow Validation
# ============================================================================

def example_authority_validation():
    """
    # UX only
    # No authority
    # No execution
    # No autonomy

    Verify that Hestia has no forbidden authority.
    """
    print("=" * 70)
    print("EXAMPLE 6: Authority Flow Validation")
    print("=" * 70)
    print()

    # Create a mock Hestia instance without forbidden methods
    class MockHestia:
        pass

    hestia = MockHestia()

    print("Checking Hestia for forbidden methods:")
    print()

    try:
        AuthorityFlowValidator.ensure_no_execution_authority(hestia)
        print("✓ Hestia has no execution authority")
    except AssertionError as e:
        print(f"✗ VIOLATION: {e}")

    try:
        AuthorityFlowValidator.ensure_no_approval_authority(hestia)
        print("✓ Hestia has no approval authority")
    except AssertionError as e:
        print(f"✗ VIOLATION: {e}")

    try:
        AuthorityFlowValidator.ensure_no_retry_logic(hestia)
        print("✓ Hestia has no retry logic")
    except AssertionError as e:
        print(f"✗ VIOLATION: {e}")

    print()


# ============================================================================
# EXAMPLE 7: Immutable Plan Verification
# ============================================================================

def example_plan_immutability():
    """
    # UX only
    # No authority
    # No execution
    # No autonomy

    Verify that plans cannot be mutated after creation.
    """
    print("=" * 70)
    print("EXAMPLE 7: Plan Immutability Verification")
    print("=" * 70)
    print()

    # Create a step (frozen dataclass)
    step = StepPresentation(
        sequence=1,
        description="Test step",
        faculty="test_faculty",
        data_accessed=["test_data"],
        capabilities_required=["test:capability"],
        estimated_duration_sec=1.0,
        irreversible=False,
    )

    print(f"Original step: {step.description}")
    print()

    # Try to mutate (should fail)
    print("Attempting to mutate step...")
    try:
        object.__setattr__(step, "description", "HACKED")
        print("✗ SECURITY ISSUE: Step was mutable!")
    except (AttributeError, TypeError):
        print("✓ Step is properly frozen (immutable)")

    print()


# ============================================================================
# EXAMPLE 8: Approval Decision Record
# ============================================================================

def example_approval_decision_record():
    """
    # UX only
    # No authority
    # No execution
    # No autonomy

    Create an immutable record of a user's approval decision.
    """
    print("=" * 70)
    print("EXAMPLE 8: Approval Decision Record")
    print("=" * 70)
    print()

    from uuid import uuid4

    decision = ApprovalDecision(
        decision_id=str(uuid4()),
        plan_id="plan-001",
        approved=True,
        approver_identity="user@example.com",
        timestamp=datetime.utcnow().isoformat() + "Z",
        reason="Plan is low-risk and achieves user's intent",
        security_state_at_decision={"state": "SECURE"},
    )

    print(f"Decision ID: {decision.decision_id}")
    print(f"Plan ID: {decision.plan_id}")
    print(f"Approved: {decision.approved}")
    print(f"Approver: {decision.approver_identity}")
    print(f"Timestamp: {decision.timestamp}")
    print(f"Reason: {decision.reason}")
    print(f"Security State: {decision.security_state_at_decision['state']}")
    print()

    print("Attempting to mutate decision...")
    try:
        object.__setattr__(decision, "approved", False)
        print("✗ SECURITY ISSUE: Decision was mutable!")
    except (AttributeError, TypeError):
        print("✓ Decision is properly frozen (immutable)")

    print()


if __name__ == "__main__":
    example_simple_presentation()
    example_high_risk_presentation()
    example_approval_prompt()
    example_rejection_explanation()
    example_authority_boundaries()
    example_authority_validation()
    example_plan_immutability()
    example_approval_decision_record()

    print("=" * 70)
    print("All examples completed")
    print("=" * 70)
