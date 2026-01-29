# UI Layer - Audit View
# Phase 1: Human Interface
# NO EXECUTION
# NO AUTONOMY
# NO MEMORY WRITES
# NO BACKGROUND THREADS

"""
Read-only audit viewer for approval decisions.

Does:
- Display approval history
- Append-only (no deletion)
- Filter by plan or user (simple selection)
- Show decision rationale

Does NOT:
- Modify decisions
- Delete records
- Execute
- Call executor
- Have filtering logic beyond simple selection
"""

from typing import List, Optional
from .models import ApprovalSession


class AuditView:
    """
    Read-only audit trail viewer.
    
    Does:
    - Display approval decisions
    - Append-only (no deletion)
    - Simple filtering (plan ID, user ID)
    
    Does NOT:
    - Modify records
    - Delete records
    - Execute
    - Have complex filtering logic
    - Have side effects
    
    # UI ONLY
    # NO EXECUTION
    # NO AUTONOMY
    # NO MEMORY WRITE
    """
    
    def __init__(self):
        """Initialize audit viewer (no side effects)."""
        self.sessions: List[ApprovalSession] = []
    
    def record_session(self, session: ApprovalSession) -> None:
        """
        Record approval session (append-only).
        
        Does:
        - Appends to audit log
        - Immutable record
        
        Does NOT:
        - Delete records
        - Modify records
        - Execute
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        self.sessions.append(session)
    
    def get_all_sessions(self) -> List[ApprovalSession]:
        """
        Get all sessions (read-only).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        return list(self.sessions)
    
    def filter_by_plan(self, plan_id: str) -> List[ApprovalSession]:
        """
        Filter sessions by plan ID (simple selection).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        return [s for s in self.sessions if s.plan.plan_id == plan_id]
    
    def filter_by_user(self, user_id: str) -> List[ApprovalSession]:
        """
        Filter sessions by user ID (simple selection).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        return [s for s in self.sessions if s.decision.user_id == user_id]
    
    def format_session_summary(self, session: ApprovalSession) -> str:
        """
        Format single session summary (read-only).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        output = []
        output.append(f"Session ID: {session.session_id}")
        output.append(f"  Plan: {session.plan.plan_id}")
        output.append(f"  Intent: {session.plan.intent}")
        output.append(f"  User: {session.decision.user_id}")
        output.append(f"  Decision: {session.decision.choice.value.upper()}")
        output.append(f"  Time: {session.decision.timestamp.isoformat()}")
        
        if session.decision.reason:
            output.append(f"  Reason: {session.decision.reason}")
        
        output.append(f"  Duration: {session.duration_ms}ms")
        output.append("")
        
        return "\n".join(output)
    
    def format_audit_trail(
        self,
        sessions: Optional[List[ApprovalSession]] = None,
    ) -> str:
        """
        Format audit trail (read-only, append-only).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        if sessions is None:
            sessions = self.sessions
        
        output = []
        output.append("=" * 70)
        output.append("AUDIT TRAIL (Append-Only, Immutable)")
        output.append("=" * 70)
        output.append("")
        
        if not sessions:
            output.append("(no sessions recorded)")
            output.append("")
        else:
            output.append(f"Total sessions: {len(sessions)}\n")
            
            for session in sessions:
                output.append(self.format_session_summary(session))
        
        output.append("=" * 70)
        output.append("END OF AUDIT TRAIL")
        output.append("=" * 70)
        
        return "\n".join(output)
    
    def display_audit_trail(self) -> str:
        """
        Display complete audit trail (read-only).
        
        # UI ONLY
        # NO EXECUTION
        # NO AUTONOMY
        # NO MEMORY WRITE
        """
        return self.format_audit_trail()


# Global audit view (singleton, append-only)
_global_audit = None


def get_audit_view() -> AuditView:
    """
    Get global audit view (singleton).
    
    # UI ONLY
    # NO EXECUTION
    # NO AUTONOMY
    # NO MEMORY WRITE
    """
    global _global_audit
    if _global_audit is None:
        _global_audit = AuditView()
    return _global_audit
