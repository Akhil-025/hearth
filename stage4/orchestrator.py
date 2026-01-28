"""
STAGE-4 ORCHESTRATOR

User-controlled execution orchestration layer (thin, fail-closed).

Stage-4 is responsible for:
1. Accepting validated Stage4ExecutionPlan objects
2. Calling Stage-3 executor as a black box
3. Synchronous, one-time execution
4. Fail-closed semantics (abort on any error)
5. Emit Stage-4-level audit events (separate from Stage-3)

Stage-4 is NOT responsible for:
- Token validation (Stage-3 does this)
- Authorization enforcement (Stage-3 does this)
- Domain validation (Stage-3 does this)
- Parameter validation (Stage-3 does this)
- Stage-3 audit logging (Stage-3 owns its audit)

This is a DECLARATIVE executor, not an agent system.
No inference, no planning, no autonomy, no retries.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

from stage4.execution_plan import Stage4ExecutionPlan
from stage4.audit import Stage4AuditEvent


class Stage4Orchestrator:
    """
    Thin orchestration layer that calls Stage-3 as a black box.
    
    Execution Flow:
    1. Accept validated Stage4ExecutionPlan
    2. Emit "plan_received" audit event
    3. Emit "execution_started" audit event
    4. Call Stage-3 executor through public interface
    5. Collect Stage-3 results (verbatim)
    6. Emit "execution_completed" or "execution_failed" audit event
    7. Return results
    
    Fail-Closed Behavior:
    - Any exception → abort immediately
    - No retries, no recovery, no partial execution
    - Abort on Stage-3 denial
    - Abort on Stage-3 execution error
    - Abort on audit failure
    """
    
    def __init__(self, stage3_orchestrator):
        """
        Initialize Stage-4 orchestrator.
        
        Args:
            stage3_orchestrator: Stage-3 orchestrator instance (black box)
                Must implement: execute_multi_domain_plan(user_id, token_hash, 
                                                          trigger_type, steps, 
                                                          data_bindings=None)
        """
        self._stage3_orchestrator = stage3_orchestrator
        self._audit_log: List[Stage4AuditEvent] = []
        self._execution_count = 0
    
    def execute_plan(self, plan: Stage4ExecutionPlan) -> Dict[str, Any]:
        """
        Execute validated plan by calling Stage-3 as black box.
        
        Synchronous Semantics:
        - Blocks until execution completes
        - No background tasks
        - One-time only (no retries)
        
        Fail-Closed Semantics:
        - Abort immediately on any error
        - No partial execution
        - No error recovery
        - Entire execution fails if ANY step fails
        
        Parameter Handling:
        - All parameters passed verbatim to Stage-3
        - No enrichment, no transformation, no mutation
        - Stage-3 is responsible for parameter validation
        
        Authorization Handling:
        - Token passed to Stage-3 for validation
        - Stage-4 does NOT validate tokens
        - Stage-3 is sole authority for authorization
        
        Args:
            plan: Validated Stage4ExecutionPlan (immutable)
        
        Returns:
            dict: Execution results from Stage-3 (returned verbatim)
        
        Raises:
            RuntimeError: If execution fails (fail-closed)
        """
        
        # Generate unique plan ID for this execution
        plan_id = f"plan_{self._execution_count}"
        self._execution_count += 1
        
        # AUDIT: Plan received by Stage-4
        self._audit_log.append(Stage4AuditEvent(
            timestamp=datetime.now(),
            user_id=plan.user_id,
            event_type="plan_received",
            plan_id=plan_id,
            details={
                "token_hash": plan.token_hash,
                "trigger_type": plan.trigger_type,
                "step_count": len(plan.steps)
            }
        ))
        
        # AUDIT: Execution starting
        self._audit_log.append(Stage4AuditEvent(
            timestamp=datetime.now(),
            user_id=plan.user_id,
            event_type="execution_started",
            plan_id=plan_id,
            details={"steps": plan.steps}
        ))
        
        try:
            # CALL STAGE-3 AS BLACK BOX
            # Pass plan attributes verbatim (no enrichment, no mutation)
            result = self._stage3_orchestrator.execute_multi_domain_plan(
                user_id=plan.user_id,
                token_hash=plan.token_hash,
                trigger_type=plan.trigger_type,
                steps=plan.steps,
                data_bindings=plan.data_bindings
            )
            
            # AUDIT: Execution completed successfully
            self._audit_log.append(Stage4AuditEvent(
                timestamp=datetime.now(),
                user_id=plan.user_id,
                event_type="execution_completed",
                plan_id=plan_id,
                details={"result_count": len(result.get("results", []))}
            ))
            
            # Return Stage-3 results VERBATIM (no interpretation)
            return result
            
        except Exception as e:
            # AUDIT: Execution failed
            self._audit_log.append(Stage4AuditEvent(
                timestamp=datetime.now(),
                user_id=plan.user_id,
                event_type="execution_failed",
                plan_id=plan_id,
                details={"error": str(e)}
            ))
            
            # FAIL-CLOSED: Abort on any error
            # No retry, no recovery, no partial success
            raise RuntimeError(f"Stage-4 execution failed (fail-closed): {e}")
    
    def get_audit_log(self) -> List[Stage4AuditEvent]:
        """
        Get Stage-4 audit log (separate from Stage-3 audit).
        
        Returns:
            list: Copy of audit log (read-only)
        """
        return self._audit_log.copy()
