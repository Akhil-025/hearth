"""
HESTIA AUTHORITY FLOW UI LAYER

# UX only
# No authority
# No execution
# No autonomy

Exposes the full Think → Propose → Approve → Execute → Stop loop
to a human in a clear, inspectable way.

CONSTRAINTS:
- No execution authority in Hestia
- No background execution
- No auto-approval
- No hidden state
- Read-only inspection only
- Standard library only
- Fail-closed on ambiguity

This is the USER-FACING layer, NOT the execution layer.
Hestia's role is to make decisions VISIBLE and INSPECTABLE.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from datetime import datetime


# ============================================================================
# PLAN PRESENTATION MODEL
# ============================================================================

@dataclass(frozen=True)
class StepPresentation:
    """
    Human-readable presentation of a single plan step.

    # UX only
    # No authority
    # No execution
    # No autonomy
    """
    sequence: int
    description: str                    # Human-readable action
    faculty: str                        # Which capability
    data_accessed: List[str]            # What data this step touches
    capabilities_required: List[str]    # Permissions needed
    estimated_duration_sec: Optional[float] = None
    irreversible: bool = False          # Does this change state?


@dataclass(frozen=True)
class PlanPresentation:
    """
    Immutable, human-readable plan presentation.

    # UX only
    # No authority
    # No execution
    # No autonomy

    Presents a PlanDraft in a way humans can understand and evaluate.
    Contains NO execution logic, NO authority, NO decisions.
    Pure data for human inspection.
    """
    plan_id: str                                # Reference to original plan
    user_intent: str                           # What the user asked for
    summary: str                               # One-line summary
    steps: Tuple[StepPresentation, ...]        # Ordered steps
    faculties_involved: Tuple[str, ...]        # List of faculties used
    data_sources_accessed: Tuple[str, ...]     # Knowledge, memory, etc.
    capabilities_required: Tuple[str, ...]     # Permissions needed
    estimated_total_duration_sec: Optional[float]  # Total time estimate
    estimated_risk_level: str                  # low | medium | high | unknown
    security_posture_snapshot: Dict[str, Any]  # Artemis state at presentation time
    irreversible_actions: Tuple[str, ...]      # Actions that cannot be undone
    assumptions: Tuple[str, ...]               # Explicit assumptions
    presentation_timestamp: str                # ISO 8601 when presented

    def to_human_text(self) -> str:
        """Export as human-readable text for display."""
        # UX only
        # No authority
        # No execution
        # No autonomy
        lines = [
            f"PLAN: {self.summary}",
            f"User Intent: {self.user_intent}",
            f"",
            f"FACULTIES INVOLVED: {', '.join(self.faculties_involved)}",
            f"",
            f"STEPS ({len(self.steps)} total):",
        ]

        for step in self.steps:
            irreversible_marker = " [IRREVERSIBLE]" if step.irreversible else ""
            duration_str = (
                f" (est. {step.estimated_duration_sec}s)"
                if step.estimated_duration_sec
                else ""
            )
            lines.append(
                f"  {step.sequence}. {step.description}{duration_str}{irreversible_marker}"
            )
            if step.data_accessed:
                lines.append(f"     Data: {', '.join(step.data_accessed)}")
            lines.append(f"     Capabilities: {', '.join(step.capabilities_required)}")

        lines.extend([
            f"",
            f"DATA SOURCES: {', '.join(self.data_sources_accessed)}",
            f"CAPABILITIES NEEDED: {', '.join(self.capabilities_required)}",
            f"RISK LEVEL: {self.estimated_risk_level}",
            f"TOTAL DURATION ESTIMATE: {self.estimated_total_duration_sec}s"
            if self.estimated_total_duration_sec
            else "TOTAL DURATION ESTIMATE: Unknown",
            f"",
            f"ASSUMPTIONS:",
        ])

        for assumption in self.assumptions:
            lines.append(f"  • {assumption}")

        if self.irreversible_actions:
            lines.extend([
                f"",
                f"IRREVERSIBLE ACTIONS (cannot be undone):",
            ])
            for action in self.irreversible_actions:
                lines.append(f"  • {action}")

        lines.append(f"")
        lines.append(f"Security state at presentation: {self.security_posture_snapshot.get('state', 'unknown')}")

        return "\n".join(lines)


# ============================================================================
# APPROVAL PROMPT BUILDER
# ============================================================================

class ApprovalPromptBuilder:
    """
    Build factual approval prompts.

    # UX only
    # No authority
    # No execution
    # No autonomy

    Generates approval prompts that are:
    - Factual (no persuasion)
    - Clear (no jargon)
    - Complete (all information)
    - Neutral (no minimization or alarmism)
    - Explicit about risks and assumptions
    """

    @staticmethod
    def build_prompt(
        plan_presentation: PlanPresentation,
        security_summary: Dict[str, Any],
    ) -> str:
        """
        Build a factual approval prompt.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Args:
            plan_presentation: PlanPresentation (immutable)
            security_summary: Current Artemis state

        Returns:
            str - Human-readable approval prompt (factual, no persuasion)
        """
        lines = []

        # Header
        lines.append("=" * 70)
        lines.append("APPROVAL REQUIRED")
        lines.append("=" * 70)
        lines.append("")

        # Summary
        lines.append(f"Plan Summary: {plan_presentation.summary}")
        lines.append(f"User Intent: {plan_presentation.user_intent}")
        lines.append("")

        # Current security state
        current_state = security_summary.get("state", "unknown")
        lines.append(f"Current Security State: {current_state}")
        if security_summary.get("explanation"):
            lines.append(f"  Reason: {security_summary['explanation']}")
        lines.append("")

        # Risk assessment
        lines.append(f"Risk Level: {plan_presentation.estimated_risk_level}")
        if plan_presentation.estimated_risk_level in ["high", "medium"]:
            lines.append("  ⚠ This plan has identified risks. Review carefully.")
        lines.append("")

        # What will happen
        lines.append("WHAT THIS PLAN WILL DO:")
        lines.append("")
        for step in plan_presentation.steps:
            irreversible = " [IRREVERSIBLE]" if step.irreversible else ""
            lines.append(f"  {step.sequence}. {step.description}{irreversible}")
        lines.append("")

        # Data access
        if plan_presentation.data_sources_accessed:
            lines.append(f"DATA THAT WILL BE ACCESSED: {', '.join(plan_presentation.data_sources_accessed)}")
            lines.append("")

        # Capabilities required
        if plan_presentation.capabilities_required:
            lines.append(f"PERMISSIONS NEEDED: {', '.join(plan_presentation.capabilities_required)}")
            lines.append("")

        # Duration
        if plan_presentation.estimated_total_duration_sec:
            lines.append(
                f"ESTIMATED DURATION: {plan_presentation.estimated_total_duration_sec} seconds"
            )
            lines.append("")

        # Assumptions (EXPLICIT)
        if plan_presentation.assumptions:
            lines.append("ASSUMPTIONS (must be true for this plan to work):")
            for assumption in plan_presentation.assumptions:
                lines.append(f"  • {assumption}")
            lines.append("")

        # Irreversible actions (EXPLICIT WARNING)
        if plan_presentation.irreversible_actions:
            lines.append("⚠ IRREVERSIBLE ACTIONS (cannot be undone):")
            for action in plan_presentation.irreversible_actions:
                lines.append(f"  • {action}")
            lines.append("")

        # Approval question
        lines.append("Do you want to approve this plan?")
        lines.append("  Type: YES or NO")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def build_rejection_explanation(reason: str) -> str:
        """
        Build a human-readable explanation for a rejected plan.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Args:
            reason: The reason the plan was rejected (from system)

        Returns:
            str - Human-readable explanation
        """
        lines = [
            "=" * 70,
            "PLAN REJECTED",
            "=" * 70,
            "",
            f"Reason: {reason}",
            "",
            "This plan cannot be executed at this time.",
            "Common reasons:",
            "  • System is in LOCKDOWN (security incident)",
            "  • Plan requires capabilities you don't have",
            "  • Plan references resources that aren't available",
            "  • Plan was altered after approval",
            "",
            "You can:",
            "  • Modify the plan and try again",
            "  • Wait for system state to change",
            "  • Contact an administrator for help",
            "",
        ]
        return "\n".join(lines)


# ============================================================================
# AUTHORITY FLOW VALIDATOR
# ============================================================================

class AuthorityFlowValidator:
    """
    Validate Hestia's authority flow constraints.

    # UX only
    # No authority
    # No execution
    # No autonomy

    Ensures Hestia:
    - Cannot execute
    - Cannot approve
    - Cannot retry
    - Cannot modify plans
    """

    @staticmethod
    def ensure_no_execution_authority(hestia_instance: Any) -> None:
        """
        Verify Hestia cannot execute plans.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Raises: AssertionError if Hestia has execution methods
        """
        forbidden_methods = [
            "execute_plan",
            "auto_execute",
            "background_execute",
            "run_immediately",
        ]

        for method_name in forbidden_methods:
            if hasattr(hestia_instance, method_name):
                raise AssertionError(
                    f"Hestia has forbidden method: {method_name} "
                    "(Hestia has no execution authority)"
                )

    @staticmethod
    def ensure_no_approval_authority(hestia_instance: Any) -> None:
        """
        Verify Hestia cannot approve plans.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Hestia can only propose approval, not grant it.

        Raises: AssertionError if Hestia has approval methods
        """
        forbidden_methods = [
            "approve_plan",
            "grant_approval",
            "auto_approve",
            "override_approval",
        ]

        for method_name in forbidden_methods:
            if hasattr(hestia_instance, method_name):
                raise AssertionError(
                    f"Hestia has forbidden method: {method_name} "
                    "(Hestia has no approval authority)"
                )

    @staticmethod
    def ensure_no_retry_logic(hestia_instance: Any) -> None:
        """
        Verify Hestia cannot retry plans.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Raises: AssertionError if Hestia has retry logic
        """
        forbidden_methods = [
            "retry_plan",
            "retry_execution",
            "auto_retry",
            "failover_plan",
        ]

        for method_name in forbidden_methods:
            if hasattr(hestia_instance, method_name):
                raise AssertionError(
                    f"Hestia has forbidden method: {method_name} "
                    "(Hestia has no retry authority)"
                )

    @staticmethod
    def ensure_no_plan_mutation(plan_draft: Any) -> Tuple[bool, str]:
        """
        Verify plan cannot be mutated.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Args:
            plan_draft: PlanDraft object

        Returns:
            (bool, str) - (is_immutable, reason)
        """
        # Check if frozen (dataclass)
        if not hasattr(plan_draft, "__dataclass_fields__"):
            return False, "Not a frozen dataclass"

        # Check if frozen=True was used
        if not hasattr(plan_draft, "__setattr__"):
            return False, "Cannot verify mutability"

        try:
            # Attempt to mutate (will fail if frozen)
            original_intent = plan_draft.intent
            object.__setattr__(plan_draft, "intent", "HACKED")
            # If we get here, it's mutable (bad!)
            object.__setattr__(plan_draft, "intent", original_intent)
            return False, "Plan is mutable (SECURITY ISSUE)"
        except (AttributeError, TypeError):
            # Good: frozen dataclass prevented mutation
            return True, "Plan is properly frozen (immutable)"


# ============================================================================
# HESTIA UX METHODS (integration with HestiaAgent)
# ============================================================================

class HestiaUIBoundary:
    """
    Boundary between Hestia reasoning and execution.

    # UX only
    # No authority
    # No execution
    # No autonomy

    Methods here are PURELY UX/PRESENTATION.
    No execution logic, no decisions, no authority.
    """

    @staticmethod
    def present_plan(plan_draft: Any) -> PlanPresentation:
        """
        Convert PlanDraft into human-readable PlanPresentation.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Args:
            plan_draft: PlanDraft (immutable)

        Returns:
            PlanPresentation (immutable, human-readable)
        """
        # Build step presentations
        step_presentations = []
        irreversible_actions = []

        for plan_step in plan_draft.derived_steps:
            # Determine if step is irreversible
            # (read-only steps are reversible; write/execute steps are not)
            faculty_str = plan_step.faculty.value if hasattr(plan_step.faculty, "value") else str(plan_step.faculty)
            is_irreversible = "write" in faculty_str.lower() or "execute" in faculty_str.lower()

            if is_irreversible:
                irreversible_actions.append(plan_step.action)

            step_pres = StepPresentation(
                sequence=plan_step.sequence,
                description=plan_step.action,
                faculty=faculty_str,
                data_accessed=[],  # TODO: infer from action
                capabilities_required=sorted(plan_step.required_capabilities),
                estimated_duration_sec=plan_step.estimated_duration_sec,
                irreversible=is_irreversible,
            )
            step_presentations.append(step_pres)

        # Build faculties list
        faculties_involved = tuple(
            f.value if hasattr(f, "value") else str(f)
            for f in plan_draft.required_faculties
        )

        # Infer data sources from faculties
        data_sources = []
        if any("knowledge" in f.lower() for f in faculties_involved):
            data_sources.append("Knowledge Store")
        if any("memory" in f.lower() for f in faculties_involved):
            data_sources.append("User Memory")
        if any("habit" in f.lower() for f in faculties_involved):
            data_sources.append("Health/Wellness Data")
        if any("music" in f.lower() or "entertainment" in f.lower() for f in faculties_involved):
            data_sources.append("Entertainment Data")
        if any("code" in f.lower() for f in faculties_involved):
            data_sources.append("Code Repository")

        return PlanPresentation(
            plan_id=plan_draft.draft_id,
            user_intent=plan_draft.intent,
            summary=f"Proposal: {plan_draft.intent}",
            steps=tuple(step_presentations),
            faculties_involved=faculties_involved,
            data_sources_accessed=tuple(data_sources),
            capabilities_required=tuple(sorted(plan_draft.required_capabilities)),
            estimated_total_duration_sec=sum(
                s.estimated_duration_sec or 0
                for s in step_presentations
            ) or None,
            estimated_risk_level=plan_draft.estimated_risk_level,
            security_posture_snapshot=plan_draft.security_summary_snapshot,
            irreversible_actions=tuple(irreversible_actions),
            assumptions=plan_draft.assumptions,
            presentation_timestamp=datetime.utcnow().isoformat() + "Z",
        )

    @staticmethod
    def request_approval_from_user(plan_presentation: PlanPresentation) -> Tuple[bool, str]:
        """
        Request user approval in an interactive session.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Args:
            plan_presentation: PlanPresentation (immutable)

        Returns:
            (approved, reason_string)
            - approved: bool (True if user says YES)
            - reason_string: str (explanation)
        """
        # Build approval prompt
        security_summary = plan_presentation.security_posture_snapshot or {}
        prompt = ApprovalPromptBuilder.build_prompt(
            plan_presentation,
            security_summary,
        )

        # Display prompt
        print(prompt)

        # Request user input
        print("Approve this plan? (YES or NO): ", end="", flush=True)
        response = input().strip().upper()

        if response == "YES":
            return True, "User approved"
        elif response == "NO":
            return False, "User rejected"
        else:
            return False, "Unclear response (not YES or NO)"

    @staticmethod
    def explain_rejection(reason: str) -> str:
        """
        Build human-readable rejection explanation.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Args:
            reason: Reason for rejection

        Returns:
            str - Human-readable explanation
        """
        return ApprovalPromptBuilder.build_rejection_explanation(reason)

    @staticmethod
    def display_authority_constraints() -> str:
        """
        Display what Hestia can and cannot do.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Returns:
            str - Factual description of Hestia's boundaries
        """
        lines = [
            "HESTIA AUTHORITY BOUNDARIES",
            "=" * 70,
            "",
            "HESTIA CAN:",
            "  • Reason about plans",
            "  • Compile plans from LLM reasoning",
            "  • Present plans to you for approval",
            "  • Explain what a plan will do",
            "  • Record your approval decisions",
            "",
            "HESTIA CANNOT:",
            "  • Execute plans (no execution authority)",
            "  • Approve plans (no approval authority)",
            "  • Modify plans (plans are immutable)",
            "  • Retry or repeat (no retry authority)",
            "  • Make autonomous decisions (requires human approval)",
            "  • Access system in LOCKDOWN (security gate)",
            "",
            "YOU CONTROL:",
            "  • When plans execute",
            "  • Whether plans are approved",
            "  • What data is accessed",
            "  • When system locks down",
            "",
        ]
        return "\n".join(lines)


# ============================================================================
# HUMAN INTERACTION RECORD
# ============================================================================

@dataclass(frozen=True)
class ApprovalDecision:
    """
    Immutable record of a human approval decision.

    # UX only
    # No authority
    # No execution
    # No autonomy
    """
    decision_id: str                    # Unique ID
    plan_id: str                        # Which plan
    approved: bool                      # YES or NO
    approver_identity: str              # Who decided
    timestamp: str                      # ISO 8601
    reason: str                         # Why they decided this way
    security_state_at_decision: Dict[str, Any]  # Artemis state
