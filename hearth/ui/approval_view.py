# UI Layer - Approval Dialog
# Phase 1: Human Interface
# NO EXECUTION
# NO AUTONOMY
# NO MEMORY WRITES
# NO BACKGROUND THREADS

"""
Approval/rejection dialog and decision recording.

Does:
- Present approval options
- Record explicit decisions
- Validate rejection reasons
- Return immutable decision

Does NOT:
- Execute
- Call executor
- Call domains
- Modify plans
- Modify state
- Have side effects
"""

from .models import ApprovalChoice, ApprovalDecision


class ApprovalView:
    """
    Approval dialog (no execution authority).
    
    Does:
    - Present approval/reject options
    - Record user choice
    - Validate decisions
    
    Does NOT:
    - Execute
    - Call executor
    - Call domains
    - Have side effects
    - Make decisions (human decides)
    
    # UI ONLY
    # NO EXECUTION
    # NO AUTONOMY
    # NO MEMORY WRITE
    """
    
    @staticmethod
    def format_approval_prompt() -> str:
        """
        Format approval prompt.
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append("=" * 70)
        output.append("APPROVAL REQUIRED")
        output.append("=" * 70)
        output.append("")
        output.append("Options:")
        output.append("  1) APPROVE — Execute this plan")
        output.append("  2) REJECT  — Do not execute (requires reason)")
        output.append("")
        output.append("This decision is:")
        output.append("  • Explicit (not implicit)")
        output.append("  • Immutable (cannot be changed)")
        output.append("  • Recorded (audit trail)")
        output.append("")
        output.append("⚠ EXECUTION IS NOT AUTOMATIC")
        output.append("⚠ Approval ≠ Execution")
        output.append("⚠ System will STOP after approval")
        output.append("")
        return "\n".join(output)
    
    @staticmethod
    def approve(
        plan_id: str,
        user_id: str,
        reason: str = "",
    ) -> ApprovalDecision:
        """
        Record APPROVE decision (immutable).
        
        Does:
        - Creates immutable decision record
        - No execution
        - No state change
        
        Does NOT:
        - Execute plan
        - Call executor
        - Call domains
        - Modify system
        - Have side effects
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        decision = ApprovalDecision.create(
            plan_id=plan_id,
            choice=ApprovalChoice.APPROVE,
            user_id=user_id,
            reason=reason if reason else None,
        )
        
        return decision
    
    @staticmethod
    def reject(
        plan_id: str,
        user_id: str,
        reason: str,
    ) -> ApprovalDecision:
        """
        Record REJECT decision (immutable, requires reason).
        
        Does:
        - Creates immutable decision record
        - Validates reason provided
        
        Does NOT:
        - Execute plan
        - Call executor
        - Call domains
        - Modify system
        - Have side effects
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        if not reason or not reason.strip():
            raise ValueError("Rejection requires reason")
        
        decision = ApprovalDecision.create(
            plan_id=plan_id,
            choice=ApprovalChoice.REJECT,
            user_id=user_id,
            reason=reason,
        )
        
        return decision
    
    @staticmethod
    def format_approval_result(decision: ApprovalDecision) -> str:
        """
        Format approval result (immutable, recorded).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append("=" * 70)
        output.append("DECISION RECORDED")
        output.append("=" * 70)
        output.append("")
        output.append(f"Decision ID: {decision.decision_id}")
        output.append(f"Choice: {decision.choice.value.upper()}")
        output.append(f"User: {decision.user_id}")
        output.append(f"Time: {decision.timestamp.isoformat()}")
        
        if decision.reason:
            output.append(f"Reason: {decision.reason}")
        
        output.append("")
        
        if decision.choice == ApprovalChoice.APPROVE:
            output.append("✓ Plan APPROVED")
            output.append("")
            output.append("⚠ IMPORTANT:")
            output.append("  • Approval recorded (immutable)")
            output.append("  • Execution NOT automatic")
            output.append("  • System will STOP here")
            output.append("  • Executor will review decision separately")
        else:
            output.append("✗ Plan REJECTED")
            output.append("")
            output.append("Plan will NOT be executed.")
            output.append("Decision recorded in audit trail.")
        
        output.append("")
        return "\n".join(output)
