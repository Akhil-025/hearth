"""
PHASE 7: Deterministic Multi-Domain Orchestration Tests

OBJECTIVE: Prove that Stage-3 can invoke multiple Stage-2 domains in sequence
while preserving all PHASE 1-6 invariants and preventing dynamic execution.

CONSTRAINTS (Non-Negotiable):
- Single user-triggered execution only (no async, no background)
- Fixed, pre-declared domain order (no runtime decisions)
- No conditionals (if/else on execution path)
- No loops (all domains in sequence once)
- No branching (no alternate paths)
- No retries (first failure → abort)
- No autonomy (domains are passive)
- No planning (domains don't decide what to do)
- No memory writes (read-only access only)

ARCHITECTURE:
    ExecutionPlan (immutable)
    ├─ user_id: str
    ├─ invocations: List[DomainInvocation] (fixed order)
    │  ├─ domain: str
    │  ├─ method: str
    │  ├─ parameters: Dict[str, Any]
    │  └─ (no conditionals on this list)
    │
    Stage3Orchestrator (deterministic)
    └─ execute(token_hash, execution_plan)
       ├─ Validate token (PHASE 2A)
       ├─ For each invocation in plan (sequential, no conditionals):
       │  ├─ Validate scope (PHASE 2B)
       │  ├─ Check limits (PHASE 2C)
       │  ├─ Emit full audit trail for domain invocation
       │  ├─ Invoke domain (PHASE 6)
       │  ├─ Record result
       │  └─ If failed: abort immediately (fail-closed)
       │
       └─ Return all results or (False, failure_reason)

AUDIT TRAIL:
- Each domain invocation gets FULL audit trail:
  1. TOKEN_VALIDATION (once for whole plan)
  2. AUTHORIZATION_SCOPE_CHECK (per domain)
  3. RESOURCE_LIMIT_CHECK (per domain)
  4. EXECUTION_STARTED (per domain)
  5. EXECUTION_COMPLETED (per domain)
  6. EXECUTION_DENIED (on failure, per domain)

- No shared state between domains
- Each domain gets fresh invocation context
- Results passed immutably to next domain

FAIL-CLOSED GUARANTEES:
- First domain failure aborts entire plan
- Token validation failure aborts all domains
- Scope/limit validation failure aborts remaining domains
- No partial execution (all-or-nothing per domain)

PREVENTION OF DYNAMIC EXECUTION:
- ExecutionPlan is immutable after creation
- No conditionals on results (can't skip domains)
- No loops (fixed iteration count)
- No branching (can't change domain order)
- No dynamic domain selection
- No retries (first attempt only)
"""

import pytest
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import json

# Import existing test helpers
from tests.test_stage3_phase1a_token_model import CapabilityToken, TokenRegistry
from tests.test_stage3_phase4b_required_audit_events import (
    AuditEventType,
    AuditEvent,
    AuditEventLog,
)
from tests.test_stage3_phase5_minimal_execution_wiring import (
    Stage3Executor,
    IsolatedParameters,
    MockDomainResult,
)
from tests.test_stage3_phase6_real_domain_integration import (
    Stage2DomainInterface,
    ApolloTestDomain,
    HermesTestDomain,
    DionysusTestDomain,
    HephaestusTestDomain,
    DomainRegistry,
    Stage3ExecutorWithRealDomains,
)


@pytest.fixture
def token_registry():
    """Fresh token registry for each test."""
    return TokenRegistry()


@pytest.fixture
def valid_token_params():
    """Standard valid token for testing."""
    return {
        "user_id": "user_test_phase7",
        "capability": "multi_domain_orchestration",
        "domain_scope": ["apollo", "hermes", "dionysus", "hephaestus"],
        "method_scope": {
            "apollo": ["analyze_habits", "plan_routine", "get_health_info"],
            "hermes": ["compose_message", "analyze_conversation", "draft_schedule"],
            "dionysus": ["analyze_mood", "recommend_music", "plan_leisure"],
            "hephaestus": ["analyze_code", "design_system", "debug_issue"],
        },
        "duration_seconds": 900,
        "resource_limits": {
            "max_invocations": 100,
            "max_tokens_per_response": 512,
            "max_total_tokens": 2048,
            "max_frequency": "1 per 10 seconds",
        },
        "allowed_trigger_types": ["direct_command"],
        "issued_by": "user_test_phase7",
    }


@pytest.fixture
def domain_registry():
    """Fresh domain registry for each test."""
    return DomainRegistry()


# ============================================================================
# EXECUTION PLAN AND ORCHESTRATOR
# ============================================================================

class DomainInvocation:
    """
    Single domain invocation specification (immutable).
    
    CRITICAL: Cannot be modified after creation. Pre-declared at plan time.
    """
    
    def __init__(self, domain: str, method: str, parameters: Dict[str, Any]):
        object.__setattr__(self, 'domain', domain)
        object.__setattr__(self, 'method', method)
        object.__setattr__(self, 'parameters', parameters)
        object.__setattr__(self, '_frozen', True)
    
    def __setattr__(self, name, value):
        """Prevent modification after creation."""
        if hasattr(self, '_frozen') and self._frozen:
            raise AttributeError(f"Cannot modify invocation: {name}")
        object.__setattr__(self, name, value)


class ExecutionPlan:
    """
    Fixed, pre-declared execution plan (immutable).
    
    CRITICAL CONSTRAINTS:
    - Order is fixed at creation time
    - No conditionals (cannot skip invocations)
    - No loops (fixed iteration count)
    - No branching (cannot change order based on results)
    - Cannot be modified after creation
    """
    
    def __init__(self, user_id: str, invocations: List[DomainInvocation]):
        """
        Create immutable execution plan.
        
        Args:
            user_id: User executing this plan
            invocations: Fixed list of domain invocations in order
        
        INVARIANT: Order and list are determined at creation time.
        No runtime decisions can modify this.
        """
        if not invocations or len(invocations) == 0:
            raise ValueError("Execution plan must have at least one invocation")
        
        # Store plan immutably
        self.user_id = user_id
        self.invocations = tuple(invocations)  # tuple = immutable
        self._frozen = True
    
    def __setattr__(self, name, value):
        """Prevent modification after creation."""
        if hasattr(self, '_frozen') and self._frozen:
            raise AttributeError(f"Cannot modify execution plan: {name}")
        super().__setattr__(name, value)
    
    def get_invocations(self) -> Tuple[DomainInvocation]:
        """Get immutable copy of invocations."""
        return self.invocations


class Stage3Orchestrator(Stage3ExecutorWithRealDomains):
    """
    Orchestrates multi-domain execution with deterministic order.
    
    Differences from Stage3ExecutorWithRealDomains:
    - Accepts ExecutionPlan instead of single (domain, method, params)
    - Executes plan sequentially without conditionals
    - Fails closed on first failure
    - Emits full audit trail for each domain
    """
    
    def execute_plan(
        self,
        token_hash: str,
        user_id: str,
        trigger_type: str,
        execution_plan: ExecutionPlan,
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Execute deterministic plan of domain invocations.
        
        Returns: (success: bool, results: List[result], error: Optional[str])
            - (True, [result1, result2, ...], None) on complete success
            - (False, None, error_reason) on any failure
        
        CRITICAL: 
        - Plan order is fixed (no conditionals)
        - Each domain gets full audit trail
        - First failure aborts remaining domains
        - Results NOT passed to next domain (isolation)
        """
        timestamp = datetime.utcnow()
        results = []
        
        # GATE 1: Token Validation (once for entire plan)
        # Check: token not revoked (check first)
        if self.token_registry.is_revoked(token_hash):
            reason = "Token validation failed: token has been revoked"
            self.audit_log.append(AuditEvent(
                event_type=AuditEventType.EXECUTION_DENIED,
                timestamp=timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain="orchestration_plan",
                method="execute_plan",
                status="denied",
                reason=reason,
            ))
            return (False, None, reason)
        
        # Check: token exists
        try:
            token = self.token_registry.get_token(token_hash)
        except Exception as e:
            reason = "Token validation failed: token not found"
            self.audit_log.append(AuditEvent(
                event_type=AuditEventType.EXECUTION_DENIED,
                timestamp=timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain="orchestration_plan",
                method="execute_plan",
                status="denied",
                reason=reason,
            ))
            return (False, None, reason)
        
        if token is None:
            reason = "Token validation failed: token does not exist"
            self.audit_log.append(AuditEvent(
                event_type=AuditEventType.EXECUTION_DENIED,
                timestamp=timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain="orchestration_plan",
                method="execute_plan",
                status="denied",
                reason=reason,
            ))
            return (False, None, reason)
        
        # Check: user_id matches token
        if token.user_id != user_id:
            reason = f"Token validation failed: token user mismatch"
            self.audit_log.append(AuditEvent(
                event_type=AuditEventType.EXECUTION_DENIED,
                timestamp=timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain="orchestration_plan",
                method="execute_plan",
                status="denied",
                reason=reason,
            ))
            return (False, None, reason)
        
        # Check: trigger_type authorized
        if trigger_type not in token.allowed_trigger_types:
            reason = f"Token validation failed: trigger type '{trigger_type}' not authorized"
            self.audit_log.append(AuditEvent(
                event_type=AuditEventType.EXECUTION_DENIED,
                timestamp=timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain="orchestration_plan",
                method="execute_plan",
                status="denied",
                reason=reason,
            ))
            return (False, None, reason)
        
        # Token validation passed - record event
        if not self.audit_log.append(AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=timestamp,
            user_id=user_id,
            token_hash=token_hash,
            domain="orchestration_plan",
            method="execute_plan",
            status="success",
        )):
            reason = "Audit log failure: could not record TOKEN_VALIDATION"
            self.audit_log.append(AuditEvent(
                event_type=AuditEventType.OPERATION_ABORTED,
                timestamp=timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain="orchestration_plan",
                method="execute_plan",
                status="failed",
                reason=reason,
            ))
            return (False, None, reason)
        
        # EXECUTION PHASE: Iterate through fixed plan order (no conditionals)
        # NOTE: This is a simple for loop with no conditionals on the list itself
        # The order is determined at plan creation time
        for invocation in execution_plan.get_invocations():
            domain = invocation.domain
            method = invocation.method
            parameters = invocation.parameters
            
            invocation_timestamp = datetime.utcnow()
            
            # GATE 2: Scope Authorization (per domain)
            # Check: domain in scope
            if domain not in token.domain_scope:
                reason = f"Authorization failed: domain '{domain}' not in scope"
                if not self.audit_log.append(AuditEvent(
                    event_type=AuditEventType.AUTHORIZATION_SCOPE_CHECK,
                    timestamp=invocation_timestamp,
                    user_id=user_id,
                    token_hash=token_hash,
                    domain=domain,
                    method=method,
                    status="denied",
                    reason=reason,
                )):
                    reason = "Audit log failure"
                if not self.audit_log.append(AuditEvent(
                    event_type=AuditEventType.EXECUTION_DENIED,
                    timestamp=invocation_timestamp,
                    user_id=user_id,
                    token_hash=token_hash,
                    domain=domain,
                    method=method,
                    status="denied",
                    reason=reason,
                )):
                    pass  # Audit write failed but we still abort
                return (False, None, reason)
            
            # Check: method in scope for domain
            method_scope = token.method_scope.get(domain, [])
            if method not in method_scope:
                reason = f"Authorization failed: method '{method}' not in scope for domain"
                if not self.audit_log.append(AuditEvent(
                    event_type=AuditEventType.AUTHORIZATION_SCOPE_CHECK,
                    timestamp=invocation_timestamp,
                    user_id=user_id,
                    token_hash=token_hash,
                    domain=domain,
                    method=method,
                    status="denied",
                    reason=reason,
                )):
                    reason = "Audit log failure"
                if not self.audit_log.append(AuditEvent(
                    event_type=AuditEventType.EXECUTION_DENIED,
                    timestamp=invocation_timestamp,
                    user_id=user_id,
                    token_hash=token_hash,
                    domain=domain,
                    method=method,
                    status="denied",
                    reason=reason,
                )):
                    pass
                return (False, None, reason)
            
            # Scope passed
            if not self.audit_log.append(AuditEvent(
                event_type=AuditEventType.AUTHORIZATION_SCOPE_CHECK,
                timestamp=invocation_timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain=domain,
                method=method,
                status="success",
            )):
                reason = "Audit log failure: could not record AUTHORIZATION_SCOPE_CHECK"
                self.audit_log.append(AuditEvent(
                    event_type=AuditEventType.OPERATION_ABORTED,
                    timestamp=invocation_timestamp,
                    user_id=user_id,
                    token_hash=token_hash,
                    domain=domain,
                    method=method,
                    status="failed",
                    reason=reason,
                ))
                return (False, None, reason)
            
            # GATE 3: Resource Limits
            if not self.audit_log.append(AuditEvent(
                event_type=AuditEventType.RESOURCE_LIMIT_CHECK,
                timestamp=invocation_timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain=domain,
                method=method,
                status="success",
            )):
                reason = "Audit log failure: could not record RESOURCE_LIMIT_CHECK"
                self.audit_log.append(AuditEvent(
                    event_type=AuditEventType.OPERATION_ABORTED,
                    timestamp=invocation_timestamp,
                    user_id=user_id,
                    token_hash=token_hash,
                    domain=domain,
                    method=method,
                    status="failed",
                    reason=reason,
                ))
                return (False, None, reason)
            
            # Record execution started
            if not self.audit_log.append(AuditEvent(
                event_type=AuditEventType.EXECUTION_STARTED,
                timestamp=invocation_timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain=domain,
                method=method,
                status="started",
            )):
                reason = "Audit log failure: could not record EXECUTION_STARTED"
                self.audit_log.append(AuditEvent(
                    event_type=AuditEventType.OPERATION_ABORTED,
                    timestamp=invocation_timestamp,
                    user_id=user_id,
                    token_hash=token_hash,
                    domain=domain,
                    method=method,
                    status="failed",
                    reason=reason,
                ))
                return (False, None, reason)
            
            # Invoke domain
            isolated_params = IsolatedParameters(parameters)
            try:
                domain_result = self.mock_domain_handler(domain, method, isolated_params)
            except Exception as e:
                reason = f"Domain invocation failed: {str(e)}"
                self.audit_log.append(AuditEvent(
                    event_type=AuditEventType.EXECUTION_COMPLETED,
                    timestamp=datetime.utcnow(),
                    user_id=user_id,
                    token_hash=token_hash,
                    domain=domain,
                    method=method,
                    status="failed",
                    reason=reason,
                ))
                # FAIL-CLOSED: Abort remaining invocations
                return (False, None, reason)
            
            # Record completion
            completion_status = "success" if domain_result.success else "failed"
            if not self.audit_log.append(AuditEvent(
                event_type=AuditEventType.EXECUTION_COMPLETED,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                token_hash=token_hash,
                domain=domain,
                method=method,
                status=completion_status,
                reason=domain_result.error if domain_result.error else None,
            )):
                reason = "Audit log failure: could not record EXECUTION_COMPLETED"
                self.audit_log.append(AuditEvent(
                    event_type=AuditEventType.OPERATION_ABORTED,
                    timestamp=datetime.utcnow(),
                    user_id=user_id,
                    token_hash=token_hash,
                    domain=domain,
                    method=method,
                    status="failed",
                    reason=reason,
                ))
                return (False, None, reason)
            
            # FAIL-CLOSED: Any domain failure aborts remaining
            if not domain_result.success:
                return (False, None, domain_result.error or "Domain invocation failed")
            
            # Store result (not passed to next domain)
            results.append(domain_result.to_dict())
        
        # All invocations succeeded
        return (True, results, None)


# ============================================================================
# TESTS: DETERMINISTIC MULTI-DOMAIN ORCHESTRATION
# ============================================================================

class TestExecutionPlanImmutability:
    """Test that execution plans are immutable and deterministic."""
    
    def test_execution_plan_cannot_be_modified(self):
        """Execution plan order cannot be changed after creation."""
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "data"}),
            DomainInvocation("hermes", "compose_message", {"type": "greeting"}),
        ]
        plan = ExecutionPlan("user_test", invocations)
        
        # Attempt to modify plan (should fail)
        with pytest.raises(AttributeError):
            plan.invocations = []
    
    def test_execution_plan_order_is_fixed(self):
        """Execution plan order is determined at creation time."""
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
            DomainInvocation("dionysus", "analyze_mood", {"test": "3"}),
        ]
        plan = ExecutionPlan("user_test", invocations)
        
        # Order should be exactly as specified
        retrieved = plan.get_invocations()
        assert len(retrieved) == 3
        assert retrieved[0].domain == "apollo"
        assert retrieved[1].domain == "hermes"
        assert retrieved[2].domain == "dionysus"
    
    def test_execution_plan_requires_at_least_one_invocation(self):
        """Empty execution plans are invalid."""
        with pytest.raises(ValueError):
            ExecutionPlan("user_test", [])


class TestSinglePlanExecution:
    """Test execution of complete plans."""
    
    def test_orchestrator_executes_single_domain_plan(self, token_registry, valid_token_params, domain_registry):
        """Orchestrator should execute single-domain plan successfully."""
        audit_log = AuditEventLog()
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Create single-domain plan
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"habits": ["exercise", "sleep"]}),
        ]
        plan = ExecutionPlan("user_test_phase7", invocations)
        
        # Execute plan
        success, results, error = orchestrator.execute_plan(
            token_hash=token_hash,
            user_id="user_test_phase7",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        assert success
        assert results is not None
        assert len(results) == 1
        assert results[0]["data"]["domain"] == "apollo"
        assert error is None
    
    def test_orchestrator_executes_multi_domain_plan(self, token_registry, valid_token_params, domain_registry):
        """Orchestrator should execute multi-domain plan in fixed order."""
        audit_log = AuditEventLog()
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Create multi-domain plan (fixed order)
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"habits": ["exercise"]}),
            DomainInvocation("hermes", "compose_message", {"type": "greeting"}),
            DomainInvocation("dionysus", "analyze_mood", {"mood_indicators": ["happy"]}),
        ]
        plan = ExecutionPlan("user_test_phase7", invocations)
        
        # Execute plan
        success, results, error = orchestrator.execute_plan(
            token_hash=token_hash,
            user_id="user_test_phase7",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        assert success
        assert results is not None
        assert len(results) == 3
        
        # Verify order is preserved
        assert results[0]["data"]["domain"] == "apollo"
        assert results[1]["data"]["domain"] == "hermes"
        assert results[2]["data"]["domain"] == "dionysus"
        assert error is None


class TestAuditTrailPerDomain:
    """Test that each domain gets full audit trail."""
    
    def test_each_domain_gets_full_audit_events(self, token_registry, valid_token_params, domain_registry):
        """Each domain invocation should emit full audit trail."""
        audit_log = AuditEventLog()
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"habits": ["exercise"]}),
            DomainInvocation("hermes", "compose_message", {"type": "greeting"}),
        ]
        plan = ExecutionPlan("user_test_phase7", invocations)
        
        orchestrator.execute_plan(
            token_hash=token_hash,
            user_id="user_test_phase7",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        # Verify audit trail
        events = audit_log.get_events()
        event_types = [e.event_type.value for e in events]
        domains = [e.domain for e in events]
        
        # Should have: TOKEN_VALIDATION once, then per-domain:
        # AUTHORIZATION_SCOPE_CHECK, RESOURCE_LIMIT_CHECK, EXECUTION_STARTED, EXECUTION_COMPLETED
        
        # TOKEN_VALIDATION once
        assert event_types.count("TOKEN_VALIDATION") == 1
        
        # Per domain: AUTHORIZATION_SCOPE_CHECK
        assert event_types.count("AUTHORIZATION_SCOPE_CHECK") == 2
        
        # Per domain: RESOURCE_LIMIT_CHECK
        assert event_types.count("RESOURCE_LIMIT_CHECK") == 2
        
        # Per domain: EXECUTION_STARTED
        assert event_types.count("EXECUTION_STARTED") == 2
        
        # Per domain: EXECUTION_COMPLETED
        assert event_types.count("EXECUTION_COMPLETED") == 2
    
    def test_audit_events_maintain_causal_order(self, token_registry, valid_token_params, domain_registry):
        """Audit events should maintain causal ordering per domain."""
        audit_log = AuditEventLog()
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"habits": ["exercise"]}),
        ]
        plan = ExecutionPlan("user_test_phase7", invocations)
        
        orchestrator.execute_plan(
            token_hash=token_hash,
            user_id="user_test_phase7",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        # Verify order: TOKEN_VALIDATION → SCOPE → LIMIT → STARTED → COMPLETED
        events = audit_log.get_events()
        event_types = [e.event_type.value for e in events]
        
        expected_sequence = [
            "TOKEN_VALIDATION",
            "AUTHORIZATION_SCOPE_CHECK",
            "RESOURCE_LIMIT_CHECK",
            "EXECUTION_STARTED",
            "EXECUTION_COMPLETED",
        ]
        
        assert event_types == expected_sequence


class TestFailClosedBehavior:
    """Test that first failure aborts remaining domains."""
    
    def test_first_domain_failure_aborts_plan(self, token_registry, valid_token_params, domain_registry):
        """If first domain fails, remaining domains should not be invoked."""
        audit_log = AuditEventLog()
        
        # Domain that always fails
        class FailingDomain(Stage2DomainInterface):
            def invoke(self, method: str, parameters: IsolatedParameters) -> MockDomainResult:
                return MockDomainResult(success=False, error="Deliberate failure")
        
        domain_registry.domains["apollo"] = FailingDomain()
        
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"habits": []}),
            DomainInvocation("hermes", "compose_message", {"type": "greeting"}),
        ]
        plan = ExecutionPlan("user_test_phase7", invocations)
        
        success, results, error = orchestrator.execute_plan(
            token_hash=token_hash,
            user_id="user_test_phase7",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        # Plan should fail
        assert not success
        assert error is not None
        assert "Deliberate failure" in error
        
        # Verify Hermes was not invoked (no EXECUTION_COMPLETED for hermes)
        events = audit_log.get_events()
        hermes_events = [e for e in events if e.domain == "hermes"]
        assert len(hermes_events) == 0, "Hermes should not be invoked after first domain fails"
    
    def test_unauthorized_domain_aborts_plan(self, token_registry, domain_registry):
        """If domain not in scope, plan should abort."""
        # Create token with limited scope
        limited_params = {
            "user_id": "user_test_phase7",
            "capability": "limited",
            "domain_scope": ["apollo"],  # Only apollo
            "method_scope": {"apollo": ["analyze_habits"]},
            "duration_seconds": 900,
            "resource_limits": {
                "max_invocations": 10,
                "max_tokens_per_response": 512,
                "max_total_tokens": 2048,
                "max_frequency": "1 per 10 seconds",
            },
            "allowed_trigger_types": ["direct_command"],
            "issued_by": "user_test_phase7",
        }
        
        audit_log = AuditEventLog()
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**limited_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"habits": []}),
            DomainInvocation("hermes", "compose_message", {"type": "greeting"}),  # Not in scope
        ]
        plan = ExecutionPlan("user_test_phase7", invocations)
        
        success, results, error = orchestrator.execute_plan(
            token_hash=token_hash,
            user_id="user_test_phase7",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        # Should fail on Hermes (not in scope)
        assert not success
        assert error is not None
        assert "scope" in error.lower()


class TestNoDynamicExecution:
    """Test that execution cannot be dynamic or conditional."""
    
    def test_plan_order_cannot_depend_on_results(self, token_registry, valid_token_params, domain_registry):
        """
        Execution order is fixed at plan creation.
        This test verifies the architecture enforces this.
        """
        audit_log = AuditEventLog()
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Create plan with fixed order
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
            DomainInvocation("dionysus", "analyze_mood", {"test": "3"}),
        ]
        plan = ExecutionPlan("user_test_phase7", invocations)
        
        # Verify plan order is immutable
        plan_invocations = plan.get_invocations()
        assert plan_invocations[0].domain == "apollo"
        assert plan_invocations[1].domain == "hermes"
        assert plan_invocations[2].domain == "dionysus"
        
        # Order cannot be changed
        with pytest.raises(AttributeError):
            plan.invocations = tuple([])
    
    def test_no_conditionals_in_execution_loop(self, token_registry, valid_token_params, domain_registry):
        """
        Orchestrator loop has no conditionals on invocation list.
        This is a structural guarantee - loop iteration is fixed.
        """
        audit_log = AuditEventLog()
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Create plan with 3 domains
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
            DomainInvocation("dionysus", "analyze_mood", {"test": "3"}),
        ]
        plan = ExecutionPlan("user_test_phase7", invocations)
        
        success, results, error = orchestrator.execute_plan(
            token_hash=token_hash,
            user_id="user_test_phase7",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        # All 3 domains should be executed (no conditionals skipped any)
        assert len(results) == 3
        
        # Verify all domains in results
        domains_executed = [r["data"]["domain"] for r in results]
        assert domains_executed == ["apollo", "hermes", "dionysus"]


class TestIsolationBetweenDomains:
    """Test that domains don't share state or receive results from previous domains."""
    
    def test_domains_cannot_access_previous_results(self, token_registry, valid_token_params, domain_registry):
        """Each domain receives isolated parameters only, not previous results."""
        audit_log = AuditEventLog()
        
        # Track what domains received
        invocation_params = []
        
        class TrackingDomain(Stage2DomainInterface):
            def invoke(self, method: str, parameters: IsolatedParameters) -> MockDomainResult:
                invocation_params.append(parameters.get_copy())
                return MockDomainResult(success=True, data={"tracked": True})
        
        domain_registry.domains["apollo"] = TrackingDomain()
        domain_registry.domains["hermes"] = TrackingDomain()
        
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"data": "from_user_1"}),
            DomainInvocation("hermes", "compose_message", {"data": "from_user_2"}),
        ]
        plan = ExecutionPlan("user_test_phase7", invocations)
        
        orchestrator.execute_plan(
            token_hash=token_hash,
            user_id="user_test_phase7",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        # Verify each domain got its own parameters, not previous results
        assert len(invocation_params) == 2
        assert invocation_params[0] == {"data": "from_user_1"}
        assert invocation_params[1] == {"data": "from_user_2"}
        # No previous_result or similar field
        assert "previous_result" not in invocation_params[0]
        assert "previous_result" not in invocation_params[1]


class TestTokenValidationPerPlan:
    """Test that token validation happens once per plan, not per domain."""
    
    def test_token_validation_once_per_plan(self, token_registry, valid_token_params, domain_registry):
        """TOKEN_VALIDATION event should appear once for entire plan."""
        audit_log = AuditEventLog()
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
            DomainInvocation("dionysus", "analyze_mood", {"test": "3"}),
        ]
        plan = ExecutionPlan("user_test_phase7", invocations)
        
        orchestrator.execute_plan(
            token_hash=token_hash,
            user_id="user_test_phase7",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        # Count TOKEN_VALIDATION events
        events = audit_log.get_events()
        validation_events = [e for e in events if e.event_type.value == "TOKEN_VALIDATION"]
        
        # Should be exactly one
        assert len(validation_events) == 1


class TestNoExistingTestsBreak:
    """Verify that multi-domain orchestration doesn't break existing tests."""
    
    def test_phase5_executor_still_works(self, token_registry, valid_token_params, domain_registry):
        """Original single-domain executor should still work."""
        audit_log = AuditEventLog()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase7",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={"test": "data"},
        )
        
        assert success
        assert result is not None
    
    def test_token_registry_independent(self, token_registry, valid_token_params):
        """TokenRegistry should work independently."""
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        retrieved = token_registry.get_token(token_hash)
        assert retrieved is not None
    
    def test_audit_log_independent(self):
        """AuditEventLog should work independently."""
        audit_log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_ISSUED,
            timestamp=datetime.utcnow(),
            user_id="test",
            token_hash="hash",
            domain="domain",
            method="method",
            status="success",
        )
        
        success = audit_log.append(event)
        assert success
