"""
STAGE-4: User-Controlled Orchestration Layer

Public API for Stage-4 execution:
- Stage4ExecutionPlan: Immutable plan container
- validate_strict_json_plan(...): Strict JSON validator
- Stage4Orchestrator: Execution orchestrator
- Stage4AuditEvent: Audit event (separate from Stage-3)

This is NOT an agent system. This is a declarative plan executor.
No inference, no planning, no autonomy, no retries.
"""

from stage4.execution_plan import Stage4ExecutionPlan
from stage4.plan_validator import validate_strict_json_plan
from stage4.orchestrator import Stage4Orchestrator
from stage4.audit import Stage4AuditEvent

__all__ = [
    "Stage4ExecutionPlan",
    "validate_strict_json_plan",
    "Stage4Orchestrator",
    "Stage4AuditEvent",
]
