"""
STAGE-4 EXECUTION SEMANTICS TESTS

CRITICAL CONSTRAINTS:
1. Stage-3 is LOCKED - cannot modify it
2. Stage-4 is a NEW layer ABOVE Stage-3
3. Stage-4 has NO autonomy, planning, loops, conditionals
4. Stage-4 calls Stage-3 as BLACK BOX through public interface
5. Stage-4 executes synchronously, one time only
6. Stage-4 passes parameters VERBATIM (no enrichment)
7. Stage-4 is FAIL-CLOSED (abort on any error)

Stage-4 accepts ONLY explicit JSON plans from users.
Stage-4 performs NO reasoning or decision-making.
Stage-4 is a DECLARATIVE plan executor, not an agent.

Test Organization:
- TestStage3AsBlackBox: Prove Stage-4 calls Stage-3 through public interface
- TestSynchronousExecution: Prove no async, no background, one-time only
- TestVerbatimParameters: Prove no mutation, no enrichment, no inference
- TestFailClosed: Prove abort on any error (validation, Stage-3 denial, audit)
- TestNoAutonomy: Prove no reasoning, no decision-making, no retries
- TestDeterministic: Prove same plan → same execution sequence
- TestStage3Preservation: Prove Stage-4 preserves all Stage-3 guarantees
"""

import pytest
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# STAGE-4 ORCHESTRATOR (Implementation)
# ============================================================================
# This is the Stage-4 orchestrator that calls Stage-3 as a black box.
# It accepts validated plans and executes them by calling Stage-3.

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
    
    This orchestrator does NOT:
    - Plan or infer anything
    - Make decisions
    - Retry or recover
    - Loop or repeat
    - Add conditionals
    - Enrich or transform parameters
    - Duplicate Stage-3 logic
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
# MOCK STAGE-3 ORCHESTRATOR (For Testing)
# ============================================================================
# Mock Stage-3 orchestrator to test Stage-4 behavior without real Stage-3.

class MockStage3Orchestrator:
    """Mock Stage-3 orchestrator for testing Stage-4."""
    
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self._should_fail = False
        self._fail_message = ""
    
    def execute_multi_domain_plan(
        self,
        user_id: str,
        token_hash: str,
        trigger_type: str,
        steps: List[Dict[str, Any]],
        data_bindings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Mock Stage-3 execution."""
        # Record call (for verification)
        self.calls.append({
            "user_id": user_id,
            "token_hash": token_hash,
            "trigger_type": trigger_type,
            "steps": steps,
            "data_bindings": data_bindings
        })
        
        # Simulate failure if configured
        if self._should_fail:
            raise RuntimeError(self._fail_message)
        
        # Return mock results
        return {
            "status": "completed",
            "results": [{"step": i, "output": f"result_{i}"} for i in range(len(steps))]
        }
    
    def configure_failure(self, should_fail: bool, message: str = ""):
        """Configure mock to fail on next call."""
        self._should_fail = should_fail
        self._fail_message = message


# Import Stage4ExecutionPlan from validation tests
# (In real implementation, this would be in a separate module)
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


# ============================================================================
# TEST: Stage-4 Calls Stage-3 as Black Box
# ============================================================================

class TestStage3AsBlackBox:
    """
    Prove that Stage-4 calls Stage-3 as a BLACK BOX through public interface.
    
    Stage-4 MUST NOT:
    - Duplicate Stage-3 logic
    - Access Stage-3 internals
    - Bypass Stage-3 validation gates
    - Implement Stage-3 authorization
    - Implement Stage-3 audit logging (Stage-3 does that)
    
    Stage-4 MUST:
    - Call Stage-3 through public interface only
    - Pass all parameters to Stage-3
    - Trust Stage-3 authorization decisions
    - Let Stage-3 handle its own audit logging
    """
    
    def test_stage4_calls_stage3_public_interface(self):
        """Stage-4 must call Stage-3 through execute_multi_domain_plan()."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "analyze_health", "parameters": {"data": "test"}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Stage-4 called Stage-3 public interface
        assert len(mock_stage3.calls) == 1
        call = mock_stage3.calls[0]
        assert call["user_id"] == "user123"
        assert call["token_hash"] == "token_abc"
        assert call["trigger_type"] == "manual"
        assert call["steps"] == plan.steps
        assert call["data_bindings"] == plan.data_bindings
    
    def test_stage4_passes_all_parameters_to_stage3(self):
        """Stage-4 must pass ALL plan parameters to Stage-3 (verbatim)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_xyz",
            trigger_type="scheduled",
            steps=[
                {"domain": "hermes", "method": "send_message", "parameters": {"to": "bob", "text": "hi"}},
                {"domain": "apollo", "method": "log_activity", "parameters": {"activity": "message_sent"}}
            ],
            data_bindings=[
                {"source_step": 0, "source_path": "message_id", "target_step": 1, "target_path": "message_ref"}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: All parameters passed to Stage-3 verbatim
        call = mock_stage3.calls[0]
        assert call["user_id"] == "user456"
        assert call["token_hash"] == "token_xyz"
        assert call["trigger_type"] == "scheduled"
        assert call["steps"] == plan.steps
        assert call["data_bindings"] == plan.data_bindings
    
    def test_stage4_trusts_stage3_results(self):
        """Stage-4 must return Stage-3 results verbatim (no interpretation)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_123",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        result = stage4.execute_plan(plan)
        
        # Verify: Stage-4 returns Stage-3 results verbatim
        assert result["status"] == "completed"
        assert len(result["results"]) == 1
        assert result["results"][0]["output"] == "result_0"


# ============================================================================
# TEST: Synchronous Execution Only
# ============================================================================

class TestSynchronousExecution:
    """
    Prove that Stage-4 executes plans synchronously (one time only).
    
    Stage-4 MUST NOT:
    - Execute plans asynchronously
    - Execute plans in background
    - Queue plans for later execution
    - Retry failed executions
    - Loop over steps
    
    Stage-4 MUST:
    - Execute plans immediately and synchronously
    - Block until execution completes
    - Execute each plan exactly once
    - Return results immediately after Stage-3 completes
    """
    
    def test_execution_is_synchronous(self):
        """Stage-4 must execute plans synchronously (block until complete)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute (should block until complete)
        result = stage4.execute_plan(plan)
        
        # Verify: Execution completed synchronously
        assert result is not None  # Result returned immediately
        assert len(mock_stage3.calls) == 1  # Stage-3 called exactly once
    
    def test_no_background_execution(self):
        """Stage-4 must NOT execute plans in background."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_xyz",
            trigger_type="manual",
            steps=[
                {"domain": "hermes", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        result = stage4.execute_plan(plan)
        
        # Verify: No background tasks (result returned synchronously)
        assert result["status"] == "completed"
        assert len(mock_stage3.calls) == 1
        
        # Verify: No queued tasks (all work done immediately)
        audit_log = stage4.get_audit_log()
        started_events = [e for e in audit_log if e.event_type == "execution_started"]
        completed_events = [e for e in audit_log if e.event_type == "execution_completed"]
        assert len(started_events) == 1
        assert len(completed_events) == 1
    
    def test_each_plan_executed_once(self):
        """Stage-4 must execute each plan exactly once (no loops, no retries)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_123",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute same plan multiple times
        stage4.execute_plan(plan)
        stage4.execute_plan(plan)
        stage4.execute_plan(plan)
        
        # Verify: Each execution called Stage-3 exactly once
        assert len(mock_stage3.calls) == 3  # Three separate executions
        
        # Verify: No loops within single execution
        audit_log = stage4.get_audit_log()
        started_events = [e for e in audit_log if e.event_type == "execution_started"]
        completed_events = [e for e in audit_log if e.event_type == "execution_completed"]
        assert len(started_events) == 3  # Three executions started
        assert len(completed_events) == 3  # Three executions completed


# ============================================================================
# TEST: Verbatim Parameter Passing
# ============================================================================

class TestVerbatimParameters:
    """
    Prove that Stage-4 passes parameters VERBATIM to Stage-3.
    
    Stage-4 MUST NOT:
    - Mutate parameters
    - Enrich parameters
    - Add default values
    - Transform or normalize parameters
    - Infer missing parameters
    
    Stage-4 MUST:
    - Pass parameters exactly as provided in plan
    - Preserve parameter types
    - Preserve parameter structure
    - Let Stage-3 validate parameters
    """
    
    def test_parameters_passed_verbatim(self):
        """Stage-4 must pass step parameters to Stage-3 without mutation."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with complex parameters
        original_params = {
            "user_input": "test data",
            "config": {
                "setting1": 42,
                "setting2": [1, 2, 3],
                "setting3": None
            }
        }
        
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "process", "parameters": original_params}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Parameters passed verbatim (no mutation)
        call = mock_stage3.calls[0]
        assert call["steps"][0]["parameters"] == original_params
        assert call["steps"][0]["parameters"]["user_input"] == "test data"
        assert call["steps"][0]["parameters"]["config"]["setting1"] == 42
        assert call["steps"][0]["parameters"]["config"]["setting2"] == [1, 2, 3]
        assert call["steps"][0]["parameters"]["config"]["setting3"] is None
    
    def test_no_parameter_enrichment(self):
        """Stage-4 must NOT add defaults or enrich parameters."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with minimal parameters
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_xyz",
            trigger_type="manual",
            steps=[
                {"domain": "hermes", "method": "send", "parameters": {"to": "bob"}}
                # NOTE: No "from", "subject", "body", etc. (intentionally minimal)
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: No enrichment (parameters passed as-is)
        call = mock_stage3.calls[0]
        step_params = call["steps"][0]["parameters"]
        assert step_params == {"to": "bob"}
        assert "from" not in step_params  # Not added by Stage-4
        assert "subject" not in step_params  # Not added by Stage-4
        assert "body" not in step_params  # Not added by Stage-4
    
    def test_empty_parameters_preserved(self):
        """Stage-4 must preserve empty parameters (not replace with defaults)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with empty parameters
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_123",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Empty parameters preserved
        call = mock_stage3.calls[0]
        assert call["steps"][0]["parameters"] == {}


# ============================================================================
# TEST: Fail-Closed Semantics
# ============================================================================

class TestFailClosed:
    """
    Prove that Stage-4 is FAIL-CLOSED (abort on any error).
    
    Stage-4 MUST:
    - Abort immediately on Stage-3 denial
    - Abort immediately on Stage-3 execution error
    - Abort immediately on audit write failure
    - NOT retry failed executions
    - NOT attempt error recovery
    - NOT continue after error
    
    Stage-4 MUST emit "execution_failed" audit event on error.
    """
    
    def test_abort_on_stage3_denial(self):
        """Stage-4 must abort immediately if Stage-3 denies execution."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        mock_stage3.configure_failure(should_fail=True, message="Token denied by Stage-3")
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="invalid_token",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute (should raise RuntimeError)
        with pytest.raises(RuntimeError) as exc_info:
            stage4.execute_plan(plan)
        
        # Verify: Abort message indicates fail-closed behavior
        assert "fail-closed" in str(exc_info.value).lower()
        
        # Verify: "execution_failed" audit event emitted
        audit_log = stage4.get_audit_log()
        failed_events = [e for e in audit_log if e.event_type == "execution_failed"]
        assert len(failed_events) == 1
        assert "Token denied" in failed_events[0].details["error"]
    
    def test_no_retry_on_failure(self):
        """Stage-4 must NOT retry failed executions (fail-closed)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        mock_stage3.configure_failure(should_fail=True, message="Execution failed")
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_xyz",
            trigger_type="manual",
            steps=[
                {"domain": "hermes", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute (should raise RuntimeError)
        with pytest.raises(RuntimeError):
            stage4.execute_plan(plan)
        
        # Verify: Stage-3 called exactly once (no retry)
        assert len(mock_stage3.calls) == 1
    
    def test_no_error_recovery(self):
        """Stage-4 must NOT attempt error recovery (fail-closed)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        mock_stage3.configure_failure(should_fail=True, message="Domain unavailable")
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_123",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}},
                {"domain": "hermes", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute (should raise RuntimeError)
        with pytest.raises(RuntimeError):
            stage4.execute_plan(plan)
        
        # Verify: No partial success (all-or-nothing execution)
        audit_log = stage4.get_audit_log()
        completed_events = [e for e in audit_log if e.event_type == "execution_completed"]
        assert len(completed_events) == 0  # No completion (failed immediately)


# ============================================================================
# TEST: No Autonomy
# ============================================================================

class TestNoAutonomy:
    """
    Prove that Stage-4 has NO autonomy (no reasoning, no decisions).
    
    Stage-4 MUST NOT:
    - Plan or infer anything
    - Make decisions based on context
    - Choose between alternative actions
    - Reorder steps based on dependencies
    - Skip optional steps
    - Add steps based on outcomes
    
    Stage-4 MUST:
    - Execute plans exactly as declared
    - Follow fixed execution order
    - Execute all steps (no skipping)
    - Make zero autonomous decisions
    """
    
    def test_no_step_reordering(self):
        """Stage-4 must execute steps in declared order (no reordering)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with intentionally odd order
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "hermes", "method": "step3", "parameters": {}},  # Intentionally step3 first
                {"domain": "apollo", "method": "step1", "parameters": {}},  # Then step1
                {"domain": "dionysus", "method": "step2", "parameters": {}}  # Then step2
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Steps passed to Stage-3 in declared order
        call = mock_stage3.calls[0]
        assert call["steps"][0]["method"] == "step3"  # First
        assert call["steps"][1]["method"] == "step1"  # Second
        assert call["steps"][2]["method"] == "step2"  # Third
    
    def test_no_step_skipping(self):
        """Stage-4 must execute ALL steps (no skipping)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with 5 steps
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_xyz",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "step1", "parameters": {}},
                {"domain": "hermes", "method": "step2", "parameters": {}},
                {"domain": "dionysus", "method": "step3", "parameters": {}},
                {"domain": "apollo", "method": "step4", "parameters": {}},
                {"domain": "hermes", "method": "step5", "parameters": {}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: All 5 steps passed to Stage-3
        call = mock_stage3.calls[0]
        assert len(call["steps"]) == 5
    
    def test_no_step_addition(self):
        """Stage-4 must NOT add steps based on context or outcomes."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with 2 steps
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_123",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "analyze", "parameters": {"data": "test"}},
                {"domain": "hermes", "method": "notify", "parameters": {"message": "done"}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Exactly 2 steps passed to Stage-3 (no additions)
        call = mock_stage3.calls[0]
        assert len(call["steps"]) == 2


# ============================================================================
# TEST: Deterministic Execution
# ============================================================================

class TestDeterministic:
    """
    Prove that Stage-4 execution is DETERMINISTIC.
    
    Same plan → Same execution sequence → Same Stage-3 calls
    
    Stage-4 MUST NOT:
    - Make random decisions
    - Vary behavior based on time/context
    - Use implicit state
    - Have side effects on plan
    """
    
    def test_same_plan_same_execution(self):
        """Same plan must produce same Stage-3 calls (deterministic)."""
        # Setup
        mock_stage3_1 = MockStage3Orchestrator()
        stage4_1 = Stage4Orchestrator(stage3_orchestrator=mock_stage3_1)
        
        mock_stage3_2 = MockStage3Orchestrator()
        stage4_2 = Stage4Orchestrator(stage3_orchestrator=mock_stage3_2)
        
        # Same plan
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {"value": 42}}
            ]
        )
        
        # Execute twice (different orchestrators)
        stage4_1.execute_plan(plan)
        stage4_2.execute_plan(plan)
        
        # Verify: Same Stage-3 calls
        call1 = mock_stage3_1.calls[0]
        call2 = mock_stage3_2.calls[0]
        
        assert call1["user_id"] == call2["user_id"]
        assert call1["token_hash"] == call2["token_hash"]
        assert call1["trigger_type"] == call2["trigger_type"]
        assert call1["steps"] == call2["steps"]
        assert call1["data_bindings"] == call2["data_bindings"]
    
    def test_no_implicit_state(self):
        """Stage-4 must not use implicit state (each execution independent)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Execute two different plans
        plan1 = Stage4ExecutionPlan(
            user_id="user1",
            token_hash="token1",
            trigger_type="manual",
            steps=[{"domain": "apollo", "method": "test1", "parameters": {}}]
        )
        
        plan2 = Stage4ExecutionPlan(
            user_id="user2",
            token_hash="token2",
            trigger_type="scheduled",
            steps=[{"domain": "hermes", "method": "test2", "parameters": {}}]
        )
        
        stage4.execute_plan(plan1)
        stage4.execute_plan(plan2)
        
        # Verify: Second execution not affected by first
        call1 = mock_stage3.calls[0]
        call2 = mock_stage3.calls[1]
        
        assert call1["user_id"] == "user1"
        assert call2["user_id"] == "user2"
        assert call1["steps"][0]["domain"] == "apollo"
        assert call2["steps"][0]["domain"] == "hermes"


# ============================================================================
# TEST: Stage-3 Preservation
# ============================================================================

class TestStage3Preservation:
    """
    Prove that Stage-4 preserves ALL Stage-3 guarantees.
    
    Stage-4 MUST:
    - Preserve Stage-3 authorization (token validation)
    - Preserve Stage-3 audit logging
    - Preserve Stage-3 domain boundaries
    - Preserve Stage-3 fail-closed semantics
    - Preserve Stage-3 synchronous execution
    
    Stage-4 MUST NOT:
    - Bypass Stage-3 validation gates
    - Suppress Stage-3 audit events
    - Allow cross-domain violations
    - Add async execution
    """
    
    def test_stage3_authorization_preserved(self):
        """Stage-4 must preserve Stage-3 token validation."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with token (Stage-3 validates)
        plan = Stage4ExecutionPlan(
            user_id="user123",
            token_hash="token_abc",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Token passed to Stage-3 for validation
        call = mock_stage3.calls[0]
        assert call["token_hash"] == "token_abc"
        # NOTE: Stage-3 validates token, not Stage-4
    
    def test_stage4_emits_separate_audit_log(self):
        """Stage-4 must emit its own audit log (separate from Stage-3)."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        plan = Stage4ExecutionPlan(
            user_id="user456",
            token_hash="token_xyz",
            trigger_type="manual",
            steps=[
                {"domain": "hermes", "method": "test", "parameters": {}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Stage-4 audit log contains expected events
        audit_log = stage4.get_audit_log()
        event_types = [e.event_type for e in audit_log]
        
        assert "plan_received" in event_types
        assert "execution_started" in event_types
        assert "execution_completed" in event_types
        
        # NOTE: Stage-3 has its own audit log (not visible to Stage-4)
    
    def test_stage3_domain_boundaries_preserved(self):
        """Stage-4 must preserve Stage-3 domain boundaries."""
        # Setup
        mock_stage3 = MockStage3Orchestrator()
        stage4 = Stage4Orchestrator(stage3_orchestrator=mock_stage3)
        
        # Plan with multiple domains
        plan = Stage4ExecutionPlan(
            user_id="user789",
            token_hash="token_123",
            trigger_type="manual",
            steps=[
                {"domain": "apollo", "method": "test1", "parameters": {}},
                {"domain": "hermes", "method": "test2", "parameters": {}},
                {"domain": "dionysus", "method": "test3", "parameters": {}}
            ]
        )
        
        # Execute
        stage4.execute_plan(plan)
        
        # Verify: Domain information passed to Stage-3 for enforcement
        call = mock_stage3.calls[0]
        assert call["steps"][0]["domain"] == "apollo"
        assert call["steps"][1]["domain"] == "hermes"
        assert call["steps"][2]["domain"] == "dionysus"
        # NOTE: Stage-3 enforces domain boundaries, not Stage-4
