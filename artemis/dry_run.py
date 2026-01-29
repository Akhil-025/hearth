"""
HEARTH END-TO-END AUTHORITY DRY RUN

# Dry-run only
# No execution
# No authority transfer
# Inspection only

Demonstrates the full governance loop without executing anything:
    Think → Propose → Approve → [STOP - No Execute]

CONSTRAINTS:
- NO execution
- NO Stage-4 dispatch
- NO side effects
- NO background work
- Read-only inspection only
- Standard library only
- Fail-closed

This is a DEMONSTRATION tool, not an execution tool.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from uuid import uuid4


# ============================================================================
# DRY RUN REPORT (IMMUTABLE)
# ============================================================================

@dataclass(frozen=True)
class DryRunReport:
    """
    Immutable record of a dry-run governance loop.

    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only

    Contains everything that happened EXCEPT execution.
    Execution is explicitly blocked in dry-run mode.
    """
    dry_run_id: str                           # Unique ID for this dry run
    timestamp: str                            # ISO 8601 when dry run started
    user_intent: str                          # What user asked for
    
    # Phase 1: Compilation
    plan_compilation_success: bool            # Did compilation succeed?
    plan_compilation_message: str             # Success or error message
    plan_draft_summary: Optional[Dict[str, Any]]  # Summary of compiled plan (if successful)
    
    # Phase 3: Presentation
    plan_presentation_summary: Optional[Dict[str, Any]]  # Summary of presentation (if compiled)
    approval_prompt_preview: Optional[str]    # First 500 chars of approval prompt
    
    # Phase 3: Approval
    approval_requested: bool                  # Was approval requested?
    approval_granted: bool                    # Did user approve?
    approval_reason: str                      # Why approved/rejected
    approval_decision_id: Optional[str]       # ApprovalDecision ID (if requested)
    
    # Phase 2: Execution Request (if approved)
    execution_request_built: bool             # Was ExecutionRequest built?
    execution_request_summary: Optional[Dict[str, Any]]  # Summary of execution request
    execution_validation_passed: bool         # Would execution be allowed?
    execution_validation_message: str         # Why allowed/blocked
    
    # Security state throughout
    security_summary_at_start: Dict[str, Any]
    security_summary_at_approval: Dict[str, Any]
    security_summary_at_execution_check: Dict[str, Any]
    
    # Explicit statement
    execution_performed: bool = False         # ALWAYS False in dry-run
    explicit_statement: str = "NO EXECUTION PERFORMED - DRY RUN ONLY"
    
    # Failure information (if any step failed)
    failure_step: Optional[str] = None        # Which step failed (if any)
    failure_reason: Optional[str] = None      # Why it failed
    
    def to_human_text(self) -> str:
        """Export as human-readable text for display."""
        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only
        
        lines = [
            "=" * 70,
            f"DRY RUN REPORT: {self.dry_run_id}",
            "=" * 70,
            "",
            f"⚠ {self.explicit_statement}",
            "",
            f"User Intent: {self.user_intent}",
            f"Timestamp: {self.timestamp}",
            "",
            "=" * 70,
            "PHASE 1: PLAN COMPILATION",
            "=" * 70,
            f"Success: {self.plan_compilation_success}",
            f"Message: {self.plan_compilation_message}",
        ]
        
        if self.plan_draft_summary:
            lines.extend([
                "",
                "Plan Draft Summary:",
                f"  Plan ID: {self.plan_draft_summary.get('plan_id', 'unknown')}",
                f"  Steps: {self.plan_draft_summary.get('step_count', 0)}",
                f"  Faculties: {', '.join(self.plan_draft_summary.get('faculties', []))}",
                f"  Risk Level: {self.plan_draft_summary.get('risk_level', 'unknown')}",
            ])
        
        lines.extend([
            "",
            "=" * 70,
            "PHASE 3: PRESENTATION & APPROVAL",
            "=" * 70,
        ])
        
        if self.plan_presentation_summary:
            lines.extend([
                f"Presentation Created: Yes",
                f"Approval Requested: {self.approval_requested}",
            ])
            
            if self.approval_prompt_preview:
                lines.extend([
                    "",
                    "Approval Prompt Preview:",
                    self.approval_prompt_preview[:500] + "..." if len(self.approval_prompt_preview) > 500 else self.approval_prompt_preview,
                ])
        else:
            lines.append("Presentation Created: No (compilation failed)")
        
        if self.approval_requested:
            lines.extend([
                "",
                f"Approval Granted: {self.approval_granted}",
                f"Approval Reason: {self.approval_reason}",
            ])
            if self.approval_decision_id:
                lines.append(f"Approval Decision ID: {self.approval_decision_id}")
        
        lines.extend([
            "",
            "=" * 70,
            "PHASE 2: EXECUTION REQUEST (DRY RUN)",
            "=" * 70,
        ])
        
        if self.execution_request_built:
            lines.extend([
                "Execution Request Built: Yes",
                f"Validation Would Pass: {self.execution_validation_passed}",
                f"Validation Message: {self.execution_validation_message}",
            ])
            
            if self.execution_request_summary:
                lines.extend([
                    "",
                    "Execution Request Summary:",
                    f"  Request ID: {self.execution_request_summary.get('request_id', 'unknown')}",
                    f"  Plan ID: {self.execution_request_summary.get('plan_id', 'unknown')}",
                    f"  Approver: {self.execution_request_summary.get('approver', 'unknown')}",
                ])
        else:
            lines.append("Execution Request Built: No (approval not granted or compilation failed)")
        
        lines.extend([
            "",
            "=" * 70,
            "SECURITY STATE THROUGHOUT",
            "=" * 70,
            f"At Start: {self.security_summary_at_start.get('state', 'unknown')}",
            f"At Approval: {self.security_summary_at_approval.get('state', 'unknown')}",
            f"At Execution Check: {self.security_summary_at_execution_check.get('state', 'unknown')}",
        ])
        
        if self.failure_step:
            lines.extend([
                "",
                "=" * 70,
                "FAILURE INFORMATION",
                "=" * 70,
                f"Failed At: {self.failure_step}",
                f"Reason: {self.failure_reason}",
            ])
        
        lines.extend([
            "",
            "=" * 70,
            f"⚠ {self.explicit_statement}",
            "=" * 70,
        ])
        
        return "\n".join(lines)


# ============================================================================
# DRY RUN CONTROLLER
# ============================================================================

class DryRunController:
    """
    Orchestrate the full governance loop in dry-run mode.

    # Dry-run only
    # No execution
    # No authority transfer
    # Inspection only

    Demonstrates:
        Think → Propose → Approve → [STOP - No Execute]

    This controller has NO execution authority.
    It only demonstrates what WOULD happen.
    """

    def __init__(self, kernel: Optional[Any] = None, agent: Optional[Any] = None):
        """
        Initialize dry-run controller.

        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only

        Args:
            kernel: Artemis kernel (for security state inspection)
            agent: HestiaAgent (for plan compilation/presentation)
        """
        self._kernel = kernel
        self._agent = agent

    def run_full_loop(
        self,
        user_intent: str,
        mocked_llm_output: str,
        auto_approve: bool = False,
        approver_identity: str = "test-user@example.com",
    ) -> DryRunReport:
        """
        Run the full governance loop in dry-run mode.

        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only

        Args:
            user_intent: What the user asked for
            mocked_llm_output: Simulated LLM reasoning output
            auto_approve: If True, automatically approve (for testing)
            approver_identity: Identity of the approver

        Returns:
            DryRunReport (immutable, comprehensive)
        """
        dry_run_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Initialize report fields
        plan_compilation_success = False
        plan_compilation_message = ""
        plan_draft = None
        plan_draft_summary = None
        plan_presentation = None
        plan_presentation_summary = None
        approval_prompt_preview = None
        approval_requested = False
        approval_granted = False
        approval_reason = ""
        approval_decision_id = None
        execution_request_built = False
        execution_request_summary = None
        execution_validation_passed = False
        execution_validation_message = ""
        failure_step = None
        failure_reason = None

        # Capture security state at start
        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only
        security_at_start = self._get_security_snapshot()

        # ====================================================================
        # PHASE 1: PLAN COMPILATION
        # ====================================================================
        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only

        if not self._agent:
            return self._build_failure_report(
                dry_run_id=dry_run_id,
                timestamp=timestamp,
                user_intent=user_intent,
                failure_step="initialization",
                failure_reason="No HestiaAgent provided",
                security_at_start=security_at_start,
            )

        try:
            plan_draft, msg = self._agent.compile_plan(
                intent=user_intent,
                llm_output=mocked_llm_output,
            )
            
            if plan_draft:
                plan_compilation_success = True
                plan_compilation_message = msg
                
                # Build plan summary
                plan_draft_summary = {
                    "plan_id": plan_draft.draft_id,
                    "step_count": plan_draft.step_count(),
                    "faculties": list(f.value if hasattr(f, "value") else str(f) for f in plan_draft.required_faculties),
                    "capabilities": list(plan_draft.required_capabilities),
                    "risk_level": plan_draft.estimated_risk_level,
                }
            else:
                plan_compilation_success = False
                plan_compilation_message = msg
                failure_step = "plan_compilation"
                failure_reason = msg
                
                # Return early if compilation failed
                return self._build_report(
                    dry_run_id=dry_run_id,
                    timestamp=timestamp,
                    user_intent=user_intent,
                    plan_compilation_success=plan_compilation_success,
                    plan_compilation_message=plan_compilation_message,
                    plan_draft_summary=plan_draft_summary,
                    plan_presentation_summary=None,
                    approval_prompt_preview=None,
                    approval_requested=False,
                    approval_granted=False,
                    approval_reason="Compilation failed",
                    approval_decision_id=None,
                    execution_request_built=False,
                    execution_request_summary=None,
                    execution_validation_passed=False,
                    execution_validation_message="N/A - compilation failed",
                    security_at_start=security_at_start,
                    security_at_approval=self._get_security_snapshot(),
                    security_at_execution_check=self._get_security_snapshot(),
                    failure_step=failure_step,
                    failure_reason=failure_reason,
                )

        except Exception as e:
            failure_step = "plan_compilation"
            failure_reason = f"Exception during compilation: {e}"
            
            return self._build_report(
                dry_run_id=dry_run_id,
                timestamp=timestamp,
                user_intent=user_intent,
                plan_compilation_success=False,
                plan_compilation_message=f"Exception: {e}",
                plan_draft_summary=None,
                plan_presentation_summary=None,
                approval_prompt_preview=None,
                approval_requested=False,
                approval_granted=False,
                approval_reason="Compilation exception",
                approval_decision_id=None,
                execution_request_built=False,
                execution_request_summary=None,
                execution_validation_passed=False,
                execution_validation_message="N/A - compilation failed",
                security_at_start=security_at_start,
                security_at_approval=self._get_security_snapshot(),
                security_at_execution_check=self._get_security_snapshot(),
                failure_step=failure_step,
                failure_reason=failure_reason,
            )

        # ====================================================================
        # PHASE 3: PRESENTATION
        # ====================================================================
        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only

        try:
            plan_presentation = self._agent.present_plan(plan_draft)
            
            # Build presentation summary
            plan_presentation_summary = {
                "plan_id": plan_presentation.plan_id,
                "summary": plan_presentation.summary,
                "step_count": len(plan_presentation.steps),
                "risk_level": plan_presentation.estimated_risk_level,
                "irreversible_actions": list(plan_presentation.irreversible_actions),
            }
            
            # Build approval prompt (but don't show it in dry-run)
            from hestia.ui_layer import ApprovalPromptBuilder
            approval_prompt = ApprovalPromptBuilder.build_prompt(
                plan_presentation,
                plan_presentation.security_posture_snapshot,
            )
            approval_prompt_preview = approval_prompt

        except Exception as e:
            failure_step = "presentation"
            failure_reason = f"Exception during presentation: {e}"
            
            return self._build_report(
                dry_run_id=dry_run_id,
                timestamp=timestamp,
                user_intent=user_intent,
                plan_compilation_success=plan_compilation_success,
                plan_compilation_message=plan_compilation_message,
                plan_draft_summary=plan_draft_summary,
                plan_presentation_summary=None,
                approval_prompt_preview=None,
                approval_requested=False,
                approval_granted=False,
                approval_reason="Presentation failed",
                approval_decision_id=None,
                execution_request_built=False,
                execution_request_summary=None,
                execution_validation_passed=False,
                execution_validation_message="N/A - presentation failed",
                security_at_start=security_at_start,
                security_at_approval=self._get_security_snapshot(),
                security_at_execution_check=self._get_security_snapshot(),
                failure_step=failure_step,
                failure_reason=failure_reason,
            )

        # ====================================================================
        # PHASE 3: APPROVAL REQUEST
        # ====================================================================
        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only

        security_at_approval = self._get_security_snapshot()
        approval_requested = True

        if auto_approve:
            # Simulate approval for dry-run testing
            approval_granted = True
            approval_reason = "Auto-approved for dry-run testing"
            approval_decision_id = str(uuid4())
        else:
            # In real usage, this would prompt the user
            # For dry-run, we just simulate rejection
            approval_granted = False
            approval_reason = "Dry-run does not prompt for real approval"
            approval_decision_id = str(uuid4())

        # ====================================================================
        # PHASE 2: EXECUTION REQUEST (IF APPROVED)
        # ====================================================================
        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only

        security_at_execution_check = self._get_security_snapshot()

        if approval_granted:
            try:
                # Build ApprovalRequest
                from artemis.approval import ApprovalRequest
                
                approval_request = ApprovalRequest(
                    request_id=str(uuid4()),
                    plan_id=plan_draft.draft_id,
                    approver_identity=approver_identity,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    approved=True,
                    approval_reason=approval_reason,
                    security_state_at_approval=security_at_approval,
                )

                # Build ExecutionRequest
                from artemis.approval_executor import ExecutionRequest
                
                execution_request = ExecutionRequest(
                    request_id=str(uuid4()),
                    plan_draft=plan_draft,
                    approval_request=approval_request,
                    security_check=security_at_execution_check,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )
                
                execution_request_built = True
                execution_request_summary = {
                    "request_id": execution_request.request_id,
                    "plan_id": execution_request.plan_draft.draft_id,
                    "approver": approver_identity,
                    "timestamp": execution_request.timestamp,
                }

                # Validate (but don't execute)
                # Dry-run only
                # No execution
                # No authority transfer
                # Inspection only
                
                if self._kernel:
                    try:
                        from artemis.approval_executor import HandshakeValidator
                        
                        validator = HandshakeValidator(kernel=self._kernel)
                        validation_result = validator.validate(
                            execution_request=execution_request,
                        )
                        
                        execution_validation_passed = validation_result[0]
                        execution_validation_message = validation_result[1]
                        
                    except Exception as e:
                        execution_validation_passed = False
                        execution_validation_message = f"Validation exception: {e}"
                else:
                    execution_validation_passed = False
                    execution_validation_message = "No kernel provided for validation"

            except Exception as e:
                execution_request_built = False
                execution_validation_passed = False
                execution_validation_message = f"Exception building execution request: {e}"

        else:
            # Approval not granted
            execution_request_built = False
            execution_validation_passed = False
            execution_validation_message = "N/A - approval not granted"

        # ====================================================================
        # BUILD FINAL REPORT
        # ====================================================================
        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only

        return self._build_report(
            dry_run_id=dry_run_id,
            timestamp=timestamp,
            user_intent=user_intent,
            plan_compilation_success=plan_compilation_success,
            plan_compilation_message=plan_compilation_message,
            plan_draft_summary=plan_draft_summary,
            plan_presentation_summary=plan_presentation_summary,
            approval_prompt_preview=approval_prompt_preview,
            approval_requested=approval_requested,
            approval_granted=approval_granted,
            approval_reason=approval_reason,
            approval_decision_id=approval_decision_id,
            execution_request_built=execution_request_built,
            execution_request_summary=execution_request_summary,
            execution_validation_passed=execution_validation_passed,
            execution_validation_message=execution_validation_message,
            security_at_start=security_at_start,
            security_at_approval=security_at_approval,
            security_at_execution_check=security_at_execution_check,
            failure_step=failure_step,
            failure_reason=failure_reason,
        )

    def _get_security_snapshot(self) -> Dict[str, Any]:
        """
        Get current security state snapshot.

        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only
        """
        if not self._kernel:
            return {"state": "unknown", "explanation": "No kernel provided"}

        try:
            summary = self._kernel.inspect_security_state()
            if summary:
                return {
                    "state": getattr(summary, "state", "unknown"),
                    "explanation": getattr(summary, "explanation", ""),
                    "execution_allowed": getattr(summary, "execution_allowed", False),
                }
        except Exception:
            pass

        return {"state": "unknown", "explanation": "Failed to inspect"}

    def _build_report(
        self,
        dry_run_id: str,
        timestamp: str,
        user_intent: str,
        plan_compilation_success: bool,
        plan_compilation_message: str,
        plan_draft_summary: Optional[Dict[str, Any]],
        plan_presentation_summary: Optional[Dict[str, Any]],
        approval_prompt_preview: Optional[str],
        approval_requested: bool,
        approval_granted: bool,
        approval_reason: str,
        approval_decision_id: Optional[str],
        execution_request_built: bool,
        execution_request_summary: Optional[Dict[str, Any]],
        execution_validation_passed: bool,
        execution_validation_message: str,
        security_at_start: Dict[str, Any],
        security_at_approval: Dict[str, Any],
        security_at_execution_check: Dict[str, Any],
        failure_step: Optional[str],
        failure_reason: Optional[str],
    ) -> DryRunReport:
        """
        Build immutable dry-run report.

        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only
        """
        return DryRunReport(
            dry_run_id=dry_run_id,
            timestamp=timestamp,
            user_intent=user_intent,
            plan_compilation_success=plan_compilation_success,
            plan_compilation_message=plan_compilation_message,
            plan_draft_summary=plan_draft_summary,
            plan_presentation_summary=plan_presentation_summary,
            approval_prompt_preview=approval_prompt_preview,
            approval_requested=approval_requested,
            approval_granted=approval_granted,
            approval_reason=approval_reason,
            approval_decision_id=approval_decision_id,
            execution_request_built=execution_request_built,
            execution_request_summary=execution_request_summary,
            execution_validation_passed=execution_validation_passed,
            execution_validation_message=execution_validation_message,
            security_summary_at_start=security_at_start,
            security_summary_at_approval=security_at_approval,
            security_summary_at_execution_check=security_at_execution_check,
            execution_performed=False,  # ALWAYS False
            failure_step=failure_step,
            failure_reason=failure_reason,
        )

    def _build_failure_report(
        self,
        dry_run_id: str,
        timestamp: str,
        user_intent: str,
        failure_step: str,
        failure_reason: str,
        security_at_start: Dict[str, Any],
    ) -> DryRunReport:
        """
        Build failure report when initialization fails.

        # Dry-run only
        # No execution
        # No authority transfer
        # Inspection only
        """
        return DryRunReport(
            dry_run_id=dry_run_id,
            timestamp=timestamp,
            user_intent=user_intent,
            plan_compilation_success=False,
            plan_compilation_message="Failed at initialization",
            plan_draft_summary=None,
            plan_presentation_summary=None,
            approval_prompt_preview=None,
            approval_requested=False,
            approval_granted=False,
            approval_reason="Initialization failed",
            approval_decision_id=None,
            execution_request_built=False,
            execution_request_summary=None,
            execution_validation_passed=False,
            execution_validation_message="N/A",
            security_summary_at_start=security_at_start,
            security_summary_at_approval=security_at_start,
            security_summary_at_execution_check=security_at_start,
            execution_performed=False,
            failure_step=failure_step,
            failure_reason=failure_reason,
        )
