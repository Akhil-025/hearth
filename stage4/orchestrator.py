"""
STAGE-4 ORCHESTRATOR

User-controlled execution orchestration layer (thin, fail-closed).

Stage-4 is responsible for:
1. Accepting validated Stage4ExecutionPlan objects
2. Enforcing Artemis security policy BEFORE execution
3. Calling Stage-3 executor as a black box
4. Synchronous, one-time execution
5. Fail-closed semantics (abort on any error)
6. Emit Stage-4-level audit events (separate from Stage-3)

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
from typing import Dict, List, Any, Optional, Tuple

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
    
    def __init__(self, stage3_orchestrator, kernel=None):
        """
        Initialize Stage-4 orchestrator.
        
        Args:
            stage3_orchestrator: Stage-3 orchestrator instance (black box)
                Must implement: execute_multi_domain_plan(user_id, token_hash, 
                                                          trigger_type, steps, 
                                                          data_bindings=None)
            kernel: Hearth kernel for policy enforcement (optional for v0.1)
        """
        self._stage3_orchestrator = stage3_orchestrator
        self._kernel = kernel
        # Audit log is append-only; writes allowed only within Stage-4.
        self._audit_log: List[Stage4AuditEvent] = []
        self._execution_count = 0
    
    def execute_plan(self, plan: Stage4ExecutionPlan) -> Dict[str, Any]:
        """
        Artemis Enforcement:
        - Check execution policy BEFORE any step execution
        - Check network policy for steps that require it
        - Check domain policy for domain steps
        - Abort IMMEDIATELY if policy blocks (no retries)
        
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
        # Artemis fault containment
        # Blast radius limited
        # Fail closed
        # No recovery without restart

        fault_recorded = False

        try:
            # ────────────────────────────────────────────────────────────────
            # EXECUTION GATE: Integrity verification before Stage-4 execution
            # ────────────────────────────────────────────────────────────────
            # Artemis integrity gate
            # Fail closed
            # No execution past this point
            # Artemis attack-surface reduction
            # Fail closed
            # No recovery without restart
            
            if self._kernel and self._kernel._artemis:
                # Artemis attack-surface reduction
                # Fail closed
                # No recovery without restart
                self._kernel._artemis.assert_single_process_execution()

                try:
                    is_valid, mismatches = self._kernel._artemis.verify_integrity()
                    
                    if not is_valid:
                        # Integrity check failed - Artemis escalated state
                        artemis_state = self._kernel._artemis.get_state().name
                        print(f"[Artemis] STAGE-4 EXECUTION GATE: Integrity verification failed")
                        print(f"[Artemis] State escalated to: {artemis_state}")
                        
                        for mismatch in mismatches:
                            print(f"  - {mismatch['file']}: {mismatch['status']}")
                        
                        # AUDIT: Execution blocked by integrity failure
                        plan_id = f"plan_{self._execution_count}"
                        self._append_audit_event(Stage4AuditEvent(
                            timestamp=datetime.now(),
                            user_id=plan.user_id,
                            event_type="execution_blocked",
                            plan_id=plan_id,
                            details={"reason": f"Integrity failure: {artemis_state}"}
                        ))
                        if self._kernel and self._kernel._artemis:
                            reason = f"Integrity gate failed (state: {artemis_state})"
                            self._kernel._artemis.record_execution_block("stage4", reason)
                        fault_recorded = True
                        
                        raise RuntimeError(
                            f"Stage-4 execution blocked: Artemis integrity gate failed (state: {artemis_state})"
                        )
                except RuntimeError as e:
                    if "Integrity monitor not configured" not in str(e):
                        # Re-raise integrity failures
                        raise RuntimeError(f"Stage-4 integrity gate failed: {e}")
            
            # ARTEMIS ENFORCEMENT BOUNDARY #1: Check execution policy
            # Fail-closed by design
            # Do not bypass
            if self._kernel:
                policy = self._kernel.get_security_policy()
                artemis_state = (
                    self._kernel._artemis.get_state().name
                    if self._kernel._artemis else "UNKNOWN"
                )
                
                if not policy.allow_execution:
                    # AUDIT: Execution blocked by Artemis
                    self._append_audit_event(Stage4AuditEvent(
                        timestamp=datetime.now(),
                        user_id=plan.user_id,
                        event_type="execution_blocked",
                        plan_id=f"plan_{self._execution_count}",
                        details={"reason": f"Artemis policy {artemis_state}"}
                    ))
                    if self._kernel and self._kernel._artemis:
                        reason = f"Policy blocked execution (state: {artemis_state})"
                        self._kernel._artemis.record_execution_block("stage4", reason)
                    fault_recorded = True
                    
                    raise RuntimeError(
                        f"Stage-4 execution blocked by Artemis security policy: {artemis_state}"
                    )
            
            # Generate unique plan ID for this execution
            plan_id = f"plan_{self._execution_count}"
            self._execution_count += 1
            
            # AUDIT: Plan received by Stage-4
            self._append_audit_event(Stage4AuditEvent(
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
            self._append_audit_event(Stage4AuditEvent(
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
                self._append_audit_event(Stage4AuditEvent(
                    timestamp=datetime.now(),
                    user_id=plan.user_id,
                    event_type="execution_completed",
                    plan_id=plan_id,
                    details={"result_count": len(result.get("results", []))}
                ))
                
                # Return Stage-3 results VERBATIM (no interpretation)
                return result
                
            except Exception:
                # AUDIT: Execution failed
                self._append_audit_event(Stage4AuditEvent(
                    timestamp=datetime.now(),
                    user_id=plan.user_id,
                    event_type="execution_failed",
                    plan_id=plan_id,
                    details={"error": "Stage-3 execution failed"}
                ))
                fault_recorded = True
                raise
        except Exception as e:
            if not fault_recorded:
                self._append_audit_event(Stage4AuditEvent(
                    timestamp=datetime.now(),
                    user_id=plan.user_id,
                    event_type="execution_failed",
                    plan_id=f"plan_{self._execution_count}",
                    details={"error": str(e)}
                ))

            if self._kernel and self._kernel._artemis:
                self._kernel._artemis.handle_boundary_error(e, "stage4")

            # FAIL-CLOSED: Abort on any error
            # No retry, no recovery, no partial success
            raise RuntimeError(f"Stage-4 execution failed (fail-closed): {e}")
    
    def _append_audit_event(self, event: Stage4AuditEvent) -> None:
        """
        Append a Stage-4 audit event.

        Artemis attack-surface reduction
        Fail closed
        No recovery without restart

        Writes allowed only here (append-only).
        """
        self._audit_log.append(event)

    def get_audit_log(self) -> tuple[Stage4AuditEvent, ...]:
        """
        Get Stage-4 audit log (separate from Stage-3 audit).
        
        Returns:
            tuple: Snapshot of audit log (read-only)
        """
        return tuple(self._audit_log)

    def inspect_security_state(self) -> Dict[str, str | None]:
        """
        Inspect current security state (read-only).

        Artemis inspection surface
        Read-only
        No side effects
        Safe in LOCKDOWN
        """
        if not self._kernel or not self._kernel._artemis:
            return {"state": "UNKNOWN", "last_escalation_reason": None}
        return self._kernel._artemis.inspect_security_state()

    def inspect_security_summary(self):
        """
        Inspect current security summary (read-only).

        Artemis security UX
        Informational only
        No authority
        No side effects
        """ 
        if not self._kernel or not self._kernel._artemis:
            return None
        return self._kernel._artemis.inspect_security_summary()

    def inspect_recent_events(self, limit: int = 10) -> tuple[dict, ...]:
        """
        Inspect recent Artemis events (read-only).

        Artemis inspection surface
        Read-only
        No side effects
        Safe in LOCKDOWN
        """
        if not self._kernel or not self._kernel._artemis:
            return tuple()
        return self._kernel._artemis.inspect_recent_events(limit)
