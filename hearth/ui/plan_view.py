# UI Layer - Plan Visualization
# Phase 1: Human Interface
# NO EXECUTION
# NO AUTONOMY
# NO MEMORY WRITES
# NO BACKGROUND THREADS

"""
Plan visualization and formatting.

Does:
- Format plan data for display
- No inference or summarization
- No omission of details
- No execution

Does NOT:
- Execute
- Call domains
- Call executor
- Modify plans
- Make decisions
"""

from .models import PlanViewModel, SecuritySnapshotView


class PlanView:
    """
    Read-only plan visualization.
    
    Does:
    - Format plan for human review
    - Display all details
    - No filtering or omission
    
    Does NOT:
    - Execute
    - Call executor
    - Call domains
    - Modify plans
    
    # UI ONLY
    # NO EXECUTION
    # NO AUTONOMY
    # NO MEMORY WRITE
    """
    
    @staticmethod
    def format_plan_header(plan: PlanViewModel) -> str:
        """
        Format plan header.
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append("=" * 70)
        output.append("PLAN REVIEW — NO EXECUTION AUTHORITY")
        output.append("=" * 70)
        output.append(f"\nPlan ID: {plan.plan_id}")
        output.append(f"Intent: {plan.intent}")
        output.append(f"Created: {plan.created_at.isoformat()}")
        output.append(f"Risk Level: {plan.risk_level.upper()}")
        output.append("")
        return "\n".join(output)
    
    @staticmethod
    def format_steps(plan: PlanViewModel) -> str:
        """
        Format plan steps (all, no omission).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append("STEPS (Explicit Order):")
        output.append("-" * 70)
        
        for step in plan.steps:
            output.append(f"\n[{step.order}] {step.action}")
            output.append(f"    Subsystem: {step.subsystem}")
            output.append(f"    Duration: {step.duration_estimate_ms}ms")
            output.append(f"    Cost: ${step.cost_estimate:.2f}")
            
            if step.parameters:
                output.append(f"    Parameters:")
                for key, value in step.parameters.items():
                    output.append(f"      {key}: {value}")
        
        output.append("")
        return "\n".join(output)
    
    @staticmethod
    def format_data_access(plan: PlanViewModel) -> str:
        """
        Format data access (all details, no omission).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append("DATA ACCESS:")
        output.append("-" * 70)
        
        if plan.data_accessed:
            for data in plan.data_accessed:
                output.append(f"  • {data}")
        else:
            output.append("  (none)")
        
        output.append("")
        return "\n".join(output)
    
    @staticmethod
    def format_credentials(plan: PlanViewModel) -> str:
        """
        Format credentials required (all, no omission).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append("CREDENTIALS REQUIRED:")
        output.append("-" * 70)
        
        if plan.credentials_required:
            for cred in plan.credentials_required:
                output.append(f"  • {cred}")
        else:
            output.append("  (none)")
        
        output.append("")
        return "\n".join(output)
    
    @staticmethod
    def format_faculties(plan: PlanViewModel) -> str:
        """
        Format faculties involved.
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append("FACULTIES INVOLVED:")
        output.append("-" * 70)
        
        if plan.faculties_involved:
            for faculty in plan.faculties_involved:
                output.append(f"  • {faculty}")
        else:
            output.append("  (none)")
        
        output.append("")
        return "\n".join(output)
    
    @staticmethod
    def format_irreversible_actions(plan: PlanViewModel) -> str:
        """
        Format irreversible actions (critical warning).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append("IRREVERSIBLE ACTIONS:")
        output.append("-" * 70)
        
        if plan.irreversible_actions:
            for action in plan.irreversible_actions:
                output.append(f"  ⚠ {action}")
        else:
            output.append("  (none)")
        
        output.append("")
        return "\n".join(output)
    
    @staticmethod
    def format_cost_and_time(plan: PlanViewModel) -> str:
        """
        Format cost and time estimates.
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append("ESTIMATES:")
        output.append("-" * 70)
        output.append(f"Duration: {plan.estimated_duration_ms}ms")
        output.append(f"Cost: ${plan.cost_estimate:.2f}")
        output.append("")
        return "\n".join(output)
    
    @staticmethod
    def format_security_snapshot(security: SecuritySnapshotView) -> str:
        """
        Format security posture (read from Artemis).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append("SECURITY POSTURE (Artemis):")
        output.append("-" * 70)
        output.append(f"State: {security.security_state.value.upper()}")
        output.append(f"Live Mode: {security.live_mode.value}")
        output.append(f"Integrity: {security.integrity_status}")
        output.append(f"Last Audit: {security.last_audit_time.isoformat()}")
        output.append(f"Guidance Active: {security.guidance_active}")
        output.append("")
        return "\n".join(output)
    
    @staticmethod
    def display_plan(plan: PlanViewModel, security: SecuritySnapshotView) -> str:
        """
        Display complete plan (all details, no execution).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        sections = [
            PlanView.format_plan_header(plan),
            PlanView.format_steps(plan),
            PlanView.format_data_access(plan),
            PlanView.format_credentials(plan),
            PlanView.format_faculties(plan),
            PlanView.format_irreversible_actions(plan),
            PlanView.format_cost_and_time(plan),
            PlanView.format_security_snapshot(security),
        ]
        
        output = "\n".join(sections)
        output += "=" * 70
        output += "\nREADY FOR APPROVAL DECISION"
        output += "\n"
        
        return output
