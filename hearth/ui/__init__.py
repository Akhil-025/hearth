# UI Layer - Read-Only Plan Visualization & Approval Gating
# Phase 1: Human Interface
# NO EXECUTION
# NO AUTONOMY
# NO MEMORY WRITES
# NO BACKGROUND THREADS

"""
Phase 1 UI System for HEARTH.

Purpose:
- Display compiled plans
- Show security posture
- Allow explicit approval/rejection
- Record decisions (immutable, in-memory)

Constraints:
- UI ONLY (no execution)
- NO AUTONOMY (human decides)
- NO MEMORY WRITES (except decision recording)
- NO BACKGROUND THREADS
- NO NETWORK
- NO SIDE EFFECTS

Integration:
- Reads from: PlanCompiler, Artemis security summary
- Writes to: Decision log (in-memory immutable)
- Calls: NOTHING (pure read + decision)
"""

from .models import (
    PlanViewModel,
    PlanStep,
    ApprovalDecision,
    ApprovalChoice,
    SecuritySnapshotView,
    SecurityState,
    ApprovalSession,
    LiveMode,
)
from .plan_view import PlanView
from .approval_view import ApprovalView
from .audit_view import AuditView

__all__ = [
    "PlanViewModel",
    "PlanStep",
    "ApprovalDecision",
    "ApprovalChoice",
    "SecuritySnapshotView",
    "SecurityState",
    "ApprovalSession",
    "LiveMode",
    "PlanView",
    "ApprovalView",
    "AuditView",
]
