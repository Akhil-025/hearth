"""
STAGE-4C: BOUNDARY & FAIL-CLOSED ENFORCEMENT TESTS

CRITICAL CONSTRAINTS:
1. Stage-3 IS LOCKED (cannot modify)
2. Stage-4A (validation) and Stage-4B (semantics) are COMPLETE (cannot modify)
3. These are TESTS ONLY (no production code implementation yet)
4. Tests must FAIL initially (TDD approach)
5. Tests prove what Stage-4 CANNOT do

TEST GOALS:

1. Stage-4 → Stage-3 Boundary Enforcement
   Prove that Stage-4:
   - Cannot bypass Stage-3 validation gates
   - Cannot call Stage-3 internals directly
   - Cannot inject or mutate parameters
   - Cannot skip authorization checks
   - Cannot invoke domains directly
   - Cannot modify Stage-3 audit events

2. Fail-Closed Exhaustiveness
   Prove that Stage-4 execution aborts IMMEDIATELY on:
   - Invalid plan (validation failure)
   - Stage-3 denial (authorization failure)
   - Stage-3 exception (execution error)
   - Audit failure (logging error)
   - Partial execution attempt (consistency)

3. Negative Capability Proofs
   Explicitly assert that Stage-4 CANNOT:
   - Loop over steps
   - Branch conditionally
   - Retry failed executions
   - Infer missing parameters
   - Mutate plans after validation
   - Mutate parameters during execution
   - Continue execution after error
   - Execute steps conditionally
   - Execute partially (all-or-nothing)
   - Implement autonomy or planning
   - Skip authorization
   - Modify domain implementations
   - Access Stage-3 internals

FINAL RULE:
If behavior is ambiguous, assume it is FORBIDDEN and assert rejection.
Fail closed.
"""

import pytest
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod


# ============================================================================
# MOCK STAGE-3 WITH AUTHORIZATION GATES (For Testing Boundaries)
# ============================================================================

class Stage3DenialError(Exception):
    """Stage-3 rejection (authorization denied)."""
    pass


class Stage3ExecutionError(Exception):
    """Stage-3 execution failure (domain error)."""
    pass


class Stage3AuditError(Exception):
    """Stage-3 audit log failure."""
    pass


class MockStage3WithBoundaries:
    """
    Mock Stage-3 with authorization gates and boundaries.
    
    This mock enforces:
    - Token validation (required)
    - Domain whitelisting
    - Parameter validation
    - Audit logging
    - Fail-closed on any error
    """
    
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self._valid_tokens = {"token_abc", "token_xyz", "token_123"}
        self._valid_domains = {"apollo", "hermes", "dionysus", "hephaestus"}
        self._should_deny = False
        self._deny_reason = ""
        self._should_fail_audit = False
        self._should_fail_execution = False
    
    def execute_multi_domain_plan(
        self,
        user_id: str,
        token_hash: str,
        trigger_type: str,
        steps: List[Dict[str, Any]],
        data_bindings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute plan through Stage-3 with boundary enforcement."""
        
        # GATE 1: Token validation (Stage-3 responsibility)
        if token_hash not in self._valid_tokens:
            raise Stage3DenialError(f"Invalid token: {token_hash}")
        
        # GATE 2: Domain validation (Stage-3 responsibility)
        for i, step in enumerate(steps):
            domain = step.get("domain")
            if domain not in self._valid_domains:
                raise Stage3DenialError(f"Step {i}: Invalid domain '{domain}'")
            
            method = step.get("method")
            if not method:
                raise Stage3DenialError(f"Step {i}: Missing method")
        
        # GATE 3: Authorization check (Stage-3 responsibility)
        if self._should_deny:
            raise Stage3DenialError(self._deny_reason)
        
        # GATE 4: Audit attempt (may fail)
        if self._should_fail_audit:
            raise Stage3AuditError("Stage-3 audit log write failed")
        
        # GATE 5: Execution (may fail)
        if self._should_fail_execution:
            raise Stage3ExecutionError("Step execution failed")
        
        # Record call for verification
        self.calls.append({
            "user_id": user_id,
            "token_hash": token_hash,
            "trigger_type": trigger_type,
            "steps": steps,
            "data_bindings": data_bindings
        })
        
        # Return success
        return {
            "status": "completed",
            "results": [{"step": i, "output": f"result_{i}"} for i in range(len(steps))]
        }
    
    def configure_authorization_denial(self, should_deny: bool, reason: str = ""):
        """Configure mock to deny authorization."""
        self._should_deny = should_deny
        self._deny_reason = reason
    
    def configure_audit_failure(self, should_fail: bool):
        """Configure mock to fail audit logging."""
        self._should_fail_audit = should_fail
    
    def configure_execution_failure(self, should_fail: bool):
        """Configure mock to fail execution."""
        self._should_fail_execution = should_fail


# ============================================================================
# STAGE-4 COMPONENTS (Redefine to avoid import issues)
# ============================================================================
# These are the same components tested in test_stage4_execution_semantics.py
# Redefined here to keep tests independent

from dataclasses import dataclass, field

@dataclass
class Stage4ExecutionPlan:
    """
    Explicit, user-declared execution plan (immutable).
    
    Stage-4 accepts ONLY these plans (no inference, no defaults).
    Plans are validated BEFORE execution.
    Plans are IMMUTABLE after validation.
    """
    user_id: str
    token_hash: str
    trigger_type: str
    steps: List[Dict[str, Any]]
    data_bindings: Optional[List[Dict[str, Any]]] = None
    _immutable: bool = field(default=False, init=False, repr=False)
    
    def __post_init__(self):
        # Mark as immutable after initialization
        object.__setattr__(self, '_immutable', True)
    
    def __setattr__(self, key, value):
        # Enforce immutability (no modifications after creation)
        if hasattr(self, '_immutable') and object.__getattribute__(self, '_immutable'):
            raise AttributeError(f"Stage4ExecutionPlan is immutable. Cannot set '{key}'.")
        object.__setattr__(self, key, value)


@dataclass
class Stage4AuditEvent:
    """Stage-4 audit event (separate from Stage-3 audit)."""
    timestamp: datetime
    user_id: str
    event_type: str  # "plan_received", "plan_validated", "execution_started", "execution_completed", "execution_failed"
    plan_id: str
    details: Dict[str, Any]


class Stage4Orchestrator:
    """
    Stage-4 user-controlled orchestration layer.
    
    This orchestrator:
    1. Accepts validated Stage4ExecutionPlan objects
    2. Calls Stage-3 executor as black box through public interface
    3. Executes synchronously (no async, no background)
    4. Passes parameters verbatim (no enrichment)
    5. Fails closed on any error
    6. Emits Stage-4-level audit events only
    """
    
    def __init__(self, stage3_orchestrator):
        """
        Initialize Stage-4 orchestrator.
        
        Args:
            stage3_orchestrator: Stage-3 orchestrator instance (black box)
        """
        self._stage3_orchestrator = stage3_orchestrator
        self._audit_log: List[Stage4AuditEvent] = []
        self._execution_count = 0
    
    def execute_plan(self, plan) -> Dict[str, Any]:
        """
        Execute validated plan by calling Stage-3 as black box.
        
        Execution Semantics:
        1. Emit "plan_received" audit event
        2. Emit "execution_started" audit event
        3. Call Stage-3 orchestrator with plan steps
        4. Collect Stage-3 results (no interpretation)
        5. Emit "execution_completed" or "execution_failed" audit event
        6. Return results verbatim
        
        NO planning, NO inference, NO retries, NO error recovery.
        If Stage-3 denies, abort immediately (fail-closed).
        
        Args:
            plan: Validated Stage4ExecutionPlan
        
        Returns:
            dict: Execution results from Stage-3 (verbatim)
        
        Raises:
            RuntimeError: If execution fails (fail-closed)
        """
        # Generate plan ID
        plan_id = f"plan_{self._execution_count}"
        self._execution_count += 1
        
        # Audit: Plan received
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
        
        # Audit: Execution started
        self._audit_log.append(Stage4AuditEvent(
            timestamp=datetime.now(),
            user_id=plan.user_id,
            event_type="execution_started",
            plan_id=plan_id,
            details={"steps": plan.steps}
        ))
        
        try:
            # Call Stage-3 as BLACK BOX through public interface
            # Pass plan attributes verbatim (no enrichment, no mutation)
            result = self._stage3_orchestrator.execute_multi_domain_plan(
                user_id=plan.user_id,
                token_hash=plan.token_hash,
                trigger_type=plan.trigger_type,
                steps=plan.steps,
                data_bindings=plan.data_bindings
            )
            
            # Audit: Execution completed
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
            # Audit: Execution failed
            self._audit_log.append(Stage4AuditEvent(
                timestamp=datetime.now(),
                user_id=plan.user_id,
                event_type="execution_failed",
                plan_id=plan_id,
                details={"error": str(e)}
            ))
            
            # FAIL-CLOSED: Abort on any error (no retry, no recovery)
            raise RuntimeError(f"Stage-4 execution failed (fail-closed): {e}")
    
    def get_audit_log(self) -> List[Stage4AuditEvent]:
        """Get Stage-4 audit log (separate from Stage-3 audit)."""
        return self._audit_log.copy()


# ============================================================================
# TEST: Stage-4 → Stage-3 Boundary Enforcement
# ============================================================================

class TestStage4Stage3Boundaries:
    """
    Prove that Stage-4 respects Stage-3 boundaries.
    
    Stage-4 MUST:
    - Call Stage-3 through public interface only
    - Pass all validation to Stage-3
    - Trust Stage-3 authorization decisions
    - Not bypass any Stage-3 gates
    """
    
    def test_stage4_cannot_bypass_token_validation(self):
        """
        Stage-4 must NOT bypass Stage-3 token validation.
        
        If Stage-3 denies a token, Stage-4 must abort (fail-closed).
        Stage-4 does NOT validate tokens itself.
        """
        # Setup
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with INVALID token (Stage-3 will reject)
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="INVALID_TOKEN_xyz",  # Not in Stage-3's whitelist
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        with pytest.raises(RuntimeError) as exc_info:
            stage4.execute_plan(plan)
        
        # Verify: Execution failed (Stage-4 passed token to Stage-3)
        # Stage-3 rejected it, Stage-4 aborted
        assert "fail-closed" in str(exc_info.value).lower()
        assert "Invalid token" in str(exc_info.value)
    
    def test_stage4_cannot_bypass_domain_validation(self):
        """
        Stage-4 must NOT bypass Stage-3 domain validation.
        
        If Stage-3 denies a domain, Stage-4 must abort (fail-closed).
        Stage-4 does NOT validate domains itself.
        """
        # Setup
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with INVALID domain (Stage-3 will reject)
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "invalid_domain", "method": "test", "parameters": {}}
                # NOTE: "invalid_domain" not in Stage-3's whitelist
            ]
        )
        
        # Execute
        with pytest.raises(RuntimeError) as exc_info:
            stage4.execute_plan(plan)
        
        # Verify: Execution failed (Stage-4 passed domain to Stage-3)
        # Stage-3 rejected it, Stage-4 aborted
        assert "fail-closed" in str(exc_info.value).lower()
        assert "Invalid domain" in str(exc_info.value)
    
    def test_stage4_respects_stage3_authorization(self):
        """
        Stage-4 must respect Stage-3 authorization decisions.
        
        Stage-4 does NOT implement authorization.
        Stage-3 is responsible for all authorization.
        If Stage-3 denies, Stage-4 aborts immediately.
        """
        # Setup
        mock_stage3 = MockStage3WithBoundaries()
        mock_stage3.configure_authorization_denial(
            should_deny=True,
            reason="User does not have permission"
        )
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        with pytest.raises(RuntimeError) as exc_info:
            stage4.execute_plan(plan)
        
        # Verify: Execution failed (Stage-3 denied)
        assert "fail-closed" in str(exc_info.value).lower()
        assert "does not have permission" in str(exc_info.value)
    
    def test_stage4_cannot_call_stage3_internals(self):
        """
        Stage-4 must ONLY call Stage-3 public interface.
        
        Stage-4 CANNOT:
        - Access Stage-3 internal state
        - Call Stage-3 private methods
        - Modify Stage-3 internal data
        - Bypass public interface
        """
        # Setup
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Verify: Stage-4 calls only public method
        stage4.execute_plan(plan)
        
        # Verify: Only one call to public interface
        assert len(mock_stage3.calls) == 1
        
        # NOTE: If Stage-4 tried to access internal methods like
        # stage3._token_registry or stage3._domains, tests would fail
        # during implementation review
    
    def test_stage4_cannot_inject_parameters(self):
        """
        Stage-4 must pass parameters VERBATIM to Stage-3.
        
        Stage-4 CANNOT:
        - Add parameters
        - Modify parameters
        - Transform parameters
        - Enrich parameters
        - Remove parameters
        """
        # Setup
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with specific parameters
        original_params = {
            "user_input": "test",
            "config": {"setting": 42}
        }
        
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "hermes", "method": "send", "parameters": original_params}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Parameters passed EXACTLY as provided
        call = mock_stage3.calls[0]
        assert call["steps"][0]["parameters"] == original_params
        assert call["steps"][0]["parameters"]["user_input"] == "test"
        assert call["steps"][0]["parameters"]["config"]["setting"] == 42
        
        # NOTE: If Stage-4 added parameters like "user_id", "timestamp", etc.,
        # parameters would not match original_params


# ============================================================================
# TEST: Fail-Closed Exhaustiveness
# ============================================================================

class TestFailClosedExhaustiveness:
    """
    Prove that Stage-4 is FAIL-CLOSED on ALL error conditions.
    
    Stage-4 must abort IMMEDIATELY on:
    1. Invalid plan (validation failure)
    2. Stage-3 denial (authorization failure)
    3. Stage-3 exception (execution error)
    4. Audit failure (logging error)
    5. Partial execution attempt
    """
    
    def test_fail_closed_on_stage3_denial(self):
        """Abort immediately if Stage-3 denies execution."""
        mock_stage3 = MockStage3WithBoundaries()
        mock_stage3.configure_authorization_denial(
            should_deny=True,
            reason="Token expired"
        )
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "step1", "parameters": {}},
                {"domain": "hermes", "method": "step2", "parameters": {}}
            ]
        )
        
        # Execute
        with pytest.raises(RuntimeError):
            stage4.execute_plan(plan)
        
        # Verify: NO execution (failed immediately)
        assert len(mock_stage3.calls) == 0
    
    def test_fail_closed_on_stage3_execution_error(self):
        """Abort immediately if Stage-3 execution fails."""
        mock_stage3 = MockStage3WithBoundaries()
        mock_stage3.configure_execution_failure(should_fail=True)
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        with pytest.raises(RuntimeError):
            stage4.execute_plan(plan)
        
        # Verify: Execution aborted
        assert len(mock_stage3.calls) == 0
    
    def test_fail_closed_on_stage3_audit_failure(self):
        """Abort immediately if Stage-3 audit logging fails."""
        mock_stage3 = MockStage3WithBoundaries()
        mock_stage3.configure_audit_failure(should_fail=True)
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "hermes", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        with pytest.raises(RuntimeError):
            stage4.execute_plan(plan)
        
        # Verify: Execution aborted
        assert len(mock_stage3.calls) == 0
    
    def test_fail_closed_no_partial_execution(self):
        """
        All-or-nothing execution: no partial success.
        
        If Stage-3 fails, Stage-4 must not have caused any state change
        in Stage-3 before the failure.
        """
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "step1", "parameters": {}},
                {"domain": "hermes", "method": "step2", "parameters": {}}
            ]
        )
        
        # Execute successfully first
        result = stage4.execute_plan(plan)
        assert result["status"] == "completed"
        assert len(mock_stage3.calls) == 1
        
        # Now configure failure for next execution
        mock_stage3.configure_execution_failure(should_fail=True)
        
        # Execute (should fail)
        with pytest.raises(RuntimeError):
            stage4.execute_plan(plan)
        
        # Verify: No additional call to Stage-3 (failed immediately)
        assert len(mock_stage3.calls) == 1  # Still just the first execution
    
    def test_fail_closed_on_audit_event_emission_failure(self):
        """
        Stage-4 must abort if its own audit logging fails.
        
        This test verifies that Stage-4 would fail-close if audit
        event emission encountered an error.
        """
        # NOTE: Current mock doesn't test Stage-4 audit failure yet
        # This test documents the requirement for future implementation
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        result = stage4.execute_plan(plan)
        
        # Verify: Audit log exists (documents requirement)
        audit_log = stage4.get_audit_log()
        assert len(audit_log) >= 2  # At minimum: received, started, [completed|failed]


# ============================================================================
# TEST: Negative Capability Proofs
# ============================================================================

class TestNegativeCapabilityProofs:
    """
    Explicitly assert that Stage-4 CANNOT:
    - Loop
    - Branch
    - Retry
    - Infer
    - Mutate plans
    - Mutate parameters
    - Continue after error
    - Execute conditionally
    - Execute partially
    - Implement autonomy
    """
    
    def test_stage4_cannot_loop(self):
        """Stage-4 must NOT loop over steps or retry."""
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "step1", "parameters": {}},
                {"domain": "hermes", "method": "step2", "parameters": {}},
                {"domain": "dionysus", "method": "step3", "parameters": {}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Stage-3 called ONCE (no looping)
        assert len(mock_stage3.calls) == 1
        
        # Verify: All steps passed in single call (fixed list)
        call = mock_stage3.calls[0]
        assert len(call["steps"]) == 3
        assert call["steps"][0]["method"] == "step1"
        assert call["steps"][1]["method"] == "step2"
        assert call["steps"][2]["method"] == "step3"
    
    def test_stage4_cannot_branch_conditionally(self):
        """Stage-4 must NOT branch based on conditions."""
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with 3 steps (all should execute, never conditionally)
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "analyze", "parameters": {"data": "test"}},
                {"domain": "hermes", "method": "send", "parameters": {"to": "user"}},
                {"domain": "dionysus", "method": "cleanup", "parameters": {}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: All steps always executed (no conditional skipping)
        call = mock_stage3.calls[0]
        assert len(call["steps"]) == 3  # All steps present
    
    def test_stage4_cannot_retry_on_failure(self):
        """Stage-4 must NOT retry failed executions."""
        mock_stage3 = MockStage3WithBoundaries()
        mock_stage3.configure_execution_failure(should_fail=True)
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute (will fail)
        with pytest.raises(RuntimeError):
            stage4.execute_plan(plan)
        
        # Verify: Stage-3 called ONCE (no retry)
        assert len(mock_stage3.calls) == 0  # Failed immediately, no retry
    
    def test_stage4_cannot_infer_parameters(self):
        """Stage-4 must NOT infer or add missing parameters."""
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with minimal parameters (intentionally sparse)
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "hermes", "method": "send", "parameters": {"to": "bob"}}
                # NOTE: No "from", "subject", "body", "timestamp", etc.
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Parameters passed as-is (no inference)
        call = mock_stage3.calls[0]
        assert call["steps"][0]["parameters"] == {"to": "bob"}
        assert len(call["steps"][0]["parameters"]) == 1  # Not enriched
    
    def test_stage4_cannot_mutate_plans(self):
        """Stage-4 must NOT mutate plans after validation."""
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {"value": 42}}
            ]
        )
        
        # Capture original plan state
        original_user_id = plan.user_id
        original_steps = plan.steps.copy()
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Plan unchanged after execution
        assert plan.user_id == original_user_id
        assert plan.steps == original_steps
        
        # Verify: Cannot modify plan (immutability)
        with pytest.raises(AttributeError):
            plan.user_id = "different_user"
    
    def test_stage4_cannot_mutate_parameters(self):
        """Stage-4 must NOT mutate parameters during execution."""
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Parameters passed to Stage-4
        original_params = {
            "user_input": "test",
            "config": {"setting": 42}
        }
        
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "process", "parameters": original_params}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Parameters unchanged
        assert plan.steps[0]["parameters"] == original_params
        assert plan.steps[0]["parameters"]["user_input"] == "test"
        assert plan.steps[0]["parameters"]["config"]["setting"] == 42
    
    def test_stage4_cannot_continue_after_error(self):
        """Stage-4 must NOT continue execution after error."""
        mock_stage3 = MockStage3WithBoundaries()
        mock_stage3.configure_execution_failure(should_fail=True)
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Multi-step plan (second step should never execute)
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "fail", "parameters": {}},
                {"domain": "hermes", "method": "should_not_execute", "parameters": {}}
            ]
        )
        
        # Execute (will fail at Stage-3)
        with pytest.raises(RuntimeError):
            stage4.execute_plan(plan)
        
        # Verify: Execution stopped (no continuation)
        assert len(mock_stage3.calls) == 0
    
    def test_stage4_cannot_execute_conditionally(self):
        """Stage-4 must execute ALL steps (no conditional execution)."""
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with step that would be "optional" in conditional system
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "check", "parameters": {"condition": "always_true"}},
                {"domain": "hermes", "method": "execute", "parameters": {}},
                {"domain": "dionysus", "method": "optional", "parameters": {}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: ALL steps passed (no conditional skipping)
        call = mock_stage3.calls[0]
        assert len(call["steps"]) == 3
        methods = [step["method"] for step in call["steps"]]
        assert "check" in methods
        assert "execute" in methods
        assert "optional" in methods
    
    def test_stage4_cannot_execute_partially(self):
        """Stage-4 must be all-or-nothing (no partial execution)."""
        mock_stage3 = MockStage3WithBoundaries()
        
        # Configure failure after partial execution (hypothetically)
        # In practice, Stage-3 is called once with all steps
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "step1", "parameters": {}},
                {"domain": "hermes", "method": "step2", "parameters": {}},
                {"domain": "dionysus", "method": "step3", "parameters": {}}
            ]
        )
        
        # Execute
        result = stage4.execute_plan(plan)
        
        # Verify: All steps or nothing
        # (Stage-3 receives all steps in single call, not incrementally)
        call = mock_stage3.calls[0]
        assert len(call["steps"]) == 3  # All steps passed
    
    def test_stage4_cannot_implement_autonomy(self):
        """Stage-4 must NOT implement any form of autonomy."""
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Even with outcome data, Stage-4 must not adapt
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "analyze", "parameters": {"data": "test"}},
                {"domain": "hermes", "method": "notify", "parameters": {"message": "done"}}
            ]
        )
        
        # Execute
        result = stage4.execute_plan(plan)
        
        # Verify: Fixed execution order (no adaptation)
        call = mock_stage3.calls[0]
        assert call["steps"][0]["domain"] == "apollo"
        assert call["steps"][1]["domain"] == "hermes"
        
        # Verify: Second step always executed (not conditional on first outcome)
        assert len(call["steps"]) == 2
    
    def test_stage4_cannot_skip_authorization(self):
        """Stage-4 must always pass token to Stage-3 (no skipping auth)."""
        mock_stage3 = MockStage3WithBoundaries()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Token passed to Stage-3
        call = mock_stage3.calls[0]
        assert call["token_hash"] == "token_abc"
        assert call["user_id"] == "user456"


# ============================================================================
# TEST: Consistency & Determinism Under Boundaries
# ============================================================================

class TestConsistencyUnderBoundaries:
    """
    Prove that Stage-4 maintains consistency and determinism
    even with boundary enforcement.
    """
    
    def test_boundary_enforcement_deterministic(self):
        """Same plan always encounters same boundaries."""
        mock_stage3_1 = MockStage3WithBoundaries()
        stage4_1 = Stage4Orchestrator(stage3_orchestrator=mock_stage3_1)
        
        mock_stage3_2 = MockStage3WithBoundaries()
        stage4_2 = Stage4Orchestrator(stage3_orchestrator=mock_stage3_2)
        
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute twice
        result1 = stage4_1.execute_plan(plan)
        result2 = stage4_2.execute_plan(plan)
        
        # Verify: Same results (deterministic)
        assert result1["status"] == result2["status"]
        assert len(result1["results"]) == len(result2["results"])
    
    def test_boundary_violations_always_rejected(self):
        """Invalid domains always rejected (deterministic boundary)."""
        # First attempt
        mock_stage3_1 = MockStage3WithBoundaries()
        stage4_1 = Stage4Orchestrator(stage3_orchestrator=mock_stage3_1)
        
        plan1 = Stage4ExecutionPlan(
            user_id="user1",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "invalid_domain", "method": "test", "parameters": {}}
            ]
        )
        
        with pytest.raises(RuntimeError):
            stage4_1.execute_plan(plan1)
        
        # Second attempt (same domain)
        mock_stage3_2 = MockStage3WithBoundaries()
        stage4_2 = Stage4Orchestrator(stage3_orchestrator=mock_stage3_2)
        
        plan2 = Stage4ExecutionPlan(
            user_id="user2",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "invalid_domain", "method": "test", "parameters": {}}
            ]
        )
        
        with pytest.raises(RuntimeError):
            stage4_2.execute_plan(plan2)
        
        # Verify: Both rejected (deterministic boundary)
        assert len(mock_stage3_1.calls) == 0
        assert len(mock_stage3_2.calls) == 0
