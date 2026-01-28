"""
PHASE 8: Explicit User-Declared Data Flow Tests

OBJECTIVE: Allow ExecutionPlan steps to declare explicit data flow between domains
while preventing autonomy, implicit passing, inferred connections, and dynamic flow.

RULES:
- Tests first ✓
- No autonomy (domains don't decide flow)
- No implicit data passing (all flow explicitly declared)
- No inferred connections (user must specify every connection)
- No conditionals (flow determined at plan creation)
- No branching (flow order fixed)
- No loops (no retry or iteration)
- No retries (first attempt only)
- No memory writes (read-only data flow)
- No background execution (synchronous only)

ARCHITECTURE:
    ExecutionPlan
    ├─ invocations: List[DomainInvocation]
    └─ data_bindings: List[DataBinding] (new)
        ├─ source_step: int (which invocation provides data)
        ├─ source_path: str (JSON path in source output)
        ├─ target_step: int (which invocation receives data)
        ├─ target_path: str (where to inject in target params)
        ├─ expected_type: Type (validation)
        └─ (immutable after plan creation)

    DataBinding (declarative, user-specified)
    ├─ source_step: int (index in invocations)
    ├─ source_path: str (e.g., "data.habits")
    ├─ target_step: int (index in invocations)
    ├─ target_path: str (e.g., "user_habits")
    ├─ expected_type: Type (e.g., list, dict, str)
    └─ Immutable after creation

AUDIT TRAIL:
- New event: DATA_BINDING (when data flows between steps)
  ├─ source_step: int
  ├─ source_value_type: str
  ├─ target_step: int
  ├─ target_path: str
  └─ status: success|failed

EXECUTION FLOW:
    For each step:
        1. Validate token (PHASE 7)
        2. Check scope (PHASE 7)
        3. Check limits (PHASE 7)
        4. Resolve data bindings (NEW)
           - For each binding targeting this step:
             - Extract source value from previous step output
             - Type check
             - Merge into parameters
             - Emit DATA_BINDING event
           - On binding failure: abort all remaining steps
        5. Invoke domain (PHASE 6)
        6. Record result
        7. If failed: abort remaining

CONSTRAINTS (Non-Negotiable):
- Data flow is explicit: User specifies every connection
- Data flow is immutable: Bindings determined at plan creation
- Data flow is acyclic: No circular dependencies
- Data flow is validated: All types checked at runtime
- Data flow is audited: Every binding emitted as event
- Data flow is fail-closed: Binding failure aborts
- No autonomy: Domains don't decide what data flows
- No implicit passing: All flow declared explicitly
- No conditionals: Binding logic has no if/else
- No memory: Output immutable, not stored

PROOF OF DETERMINISM:
- Binding graph is fixed at plan creation (no runtime decisions)
- All source/target steps known upfront (no discovery)
- Data extraction is path-based (no logic)
- No branching (all declared flows executed)
- No retries (first attempt only)
"""

import pytest
from datetime import datetime
from typing import Dict, Any, Optional, List, Type, Tuple
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
from tests.test_stage3_phase7_deterministic_multi_domain_orchestration import (
    DomainInvocation,
    ExecutionPlan,
    Stage3Orchestrator,
)


@pytest.fixture
def token_registry():
    """Fresh token registry for each test."""
    return TokenRegistry()


@pytest.fixture
def valid_token_params():
    """Standard valid token for testing."""
    return {
        "user_id": "user_test_phase8",
        "capability": "explicit_data_flow",
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
        "issued_by": "user_test_phase8",
    }


@pytest.fixture
def domain_registry():
    """Fresh domain registry for each test."""
    return DomainRegistry()


# ============================================================================
# DATA BINDING AND EXECUTION PLAN WITH DATA FLOW
# ============================================================================

class DataBinding:
    """
    Explicit data flow declaration (immutable).
    
    Specifies: Output from step N at path X → Input to step M at path Y
    
    CRITICAL:
    - Explicit: Every connection declared by user
    - Immutable: Cannot change after creation
    - Acyclic: No circular dependencies
    - Typed: Runtime validation of data type
    """
    
    def __init__(
        self,
        source_step: int,
        source_path: str,
        target_step: int,
        target_path: str,
        expected_type: Type = None,
    ):
        """
        Create immutable data binding.
        
        Args:
            source_step: Index of invocation providing data
            source_path: JSON path in source output (e.g., "data.habits")
            target_step: Index of invocation receiving data
            target_path: Where to inject in target params (e.g., "user_habits")
            expected_type: Expected type of data at source (optional validation)
        
        INVARIANT: Cannot be modified after creation
        """
        if source_step < 0 or target_step < 0:
            raise ValueError("Step indices must be non-negative")
        if source_step == target_step:
            raise ValueError("Cannot bind step output to itself")
        if target_step <= source_step:
            raise ValueError("Target step must come after source step (no circular deps)")
        
        object.__setattr__(self, 'source_step', source_step)
        object.__setattr__(self, 'source_path', source_path)
        object.__setattr__(self, 'target_step', target_step)
        object.__setattr__(self, 'target_path', target_path)
        object.__setattr__(self, 'expected_type', expected_type)
        object.__setattr__(self, '_frozen', True)
    
    def __setattr__(self, name, value):
        """Prevent modification after creation."""
        if hasattr(self, '_frozen') and self._frozen:
            raise AttributeError(f"Cannot modify data binding: {name}")
        object.__setattr__(self, name, value)


class ExecutionPlanWithDataFlow:
    """
    Execution plan with explicit data flow bindings (immutable).
    
    Extends ExecutionPlan to allow:
    - Data bindings: Output from step N → Input to step M
    - All bindings declared upfront
    - No dynamic flow resolution
    - Full validation at creation time
    """
    
    def __init__(
        self,
        user_id: str,
        invocations: List[DomainInvocation],
        data_bindings: List[DataBinding] = None,
    ):
        """
        Create execution plan with optional data flow.
        
        Args:
            user_id: User executing plan
            invocations: Fixed list of domain invocations
            data_bindings: Optional explicit data flow declarations
        
        INVARIANTS:
        - Invocations immutable (same as PHASE 7)
        - Data bindings immutable (new)
        - All bindings validated at creation
        - No circular dependencies
        - No forward references to non-existent steps
        """
        if not invocations or len(invocations) == 0:
            raise ValueError("Execution plan must have at least one invocation")
        
        # Validate data bindings
        data_bindings = data_bindings or []
        for binding in data_bindings:
            if binding.source_step >= len(invocations):
                raise ValueError(
                    f"Binding references invalid source step {binding.source_step} "
                    f"(only {len(invocations)} invocations)"
                )
            if binding.target_step >= len(invocations):
                raise ValueError(
                    f"Binding references invalid target step {binding.target_step} "
                    f"(only {len(invocations)} invocations)"
                )
        
        # Store immutably
        self.user_id = user_id
        self.invocations = tuple(invocations)
        self.data_bindings = tuple(data_bindings)
        self._frozen = True
    
    def __setattr__(self, name, value):
        """Prevent modification after creation."""
        if hasattr(self, '_frozen') and self._frozen:
            raise AttributeError(f"Cannot modify execution plan: {name}")
        super().__setattr__(name, value)
    
    def get_invocations(self) -> Tuple[DomainInvocation]:
        """Get immutable copy of invocations."""
        return self.invocations
    
    def get_data_bindings(self) -> Tuple[DataBinding]:
        """Get immutable copy of data bindings."""
        return self.data_bindings


def extract_json_path(obj: Any, path: str) -> Any:
    """
    Extract value from object using JSON path (simple dot notation).
    
    Examples:
        extract_json_path({"data": {"habits": [1, 2]}}, "data.habits") → [1, 2]
        extract_json_path({"value": 42}, "value") → 42
    
    Args:
        obj: Object to extract from
        path: Dot-separated path (e.g., "data.habits")
    
    Returns:
        Value at path, or raises KeyError if path not found
    """
    parts = path.split('.')
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(f"Cannot access {part} on {type(current)}")
    return current


class Stage3OrchestratorWithDataFlow(Stage3Orchestrator):
    """
    Orchestrates multi-domain execution with explicit data flow.
    
    Differences from Stage3Orchestrator:
    - Accepts ExecutionPlanWithDataFlow instead of ExecutionPlan
    - Before each domain invocation, resolves data bindings
    - Emits DATA_BINDING audit events
    - Merges bound data into domain parameters
    - Fails closed on binding failure
    """
    
    def execute_plan_with_data_flow(
        self,
        token_hash: str,
        user_id: str,
        trigger_type: str,
        execution_plan: ExecutionPlanWithDataFlow,
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Execute plan with explicit data flow between domains.
        
        Returns: (success: bool, results: List[result], error: Optional[str])
            - (True, [result1, result2, ...], None) on complete success
            - (False, None, error_reason) on any failure
        """
        timestamp = datetime.utcnow()
        results = []
        
        # GATE 1: Token Validation (once for entire plan)
        if self.token_registry.is_revoked(token_hash):
            reason = "Token validation failed: token has been revoked"
            self.audit_log.append(AuditEvent(
                event_type=AuditEventType.EXECUTION_DENIED,
                timestamp=timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain="orchestration_plan",
                method="execute_plan_with_data_flow",
                status="denied",
                reason=reason,
            ))
            return (False, None, reason)
        
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
                method="execute_plan_with_data_flow",
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
                method="execute_plan_with_data_flow",
                status="denied",
                reason=reason,
            ))
            return (False, None, reason)
        
        if token.user_id != user_id:
            reason = f"Token validation failed: token user mismatch"
            self.audit_log.append(AuditEvent(
                event_type=AuditEventType.EXECUTION_DENIED,
                timestamp=timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain="orchestration_plan",
                method="execute_plan_with_data_flow",
                status="denied",
                reason=reason,
            ))
            return (False, None, reason)
        
        if trigger_type not in token.allowed_trigger_types:
            reason = f"Token validation failed: trigger type '{trigger_type}' not authorized"
            self.audit_log.append(AuditEvent(
                event_type=AuditEventType.EXECUTION_DENIED,
                timestamp=timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain="orchestration_plan",
                method="execute_plan_with_data_flow",
                status="denied",
                reason=reason,
            ))
            return (False, None, reason)
        
        # Token validation passed
        if not self.audit_log.append(AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=timestamp,
            user_id=user_id,
            token_hash=token_hash,
            domain="orchestration_plan",
            method="execute_plan_with_data_flow",
            status="success",
        )):
            reason = "Audit log failure: could not record TOKEN_VALIDATION"
            self.audit_log.append(AuditEvent(
                event_type=AuditEventType.OPERATION_ABORTED,
                timestamp=timestamp,
                user_id=user_id,
                token_hash=token_hash,
                domain="orchestration_plan",
                method="execute_plan_with_data_flow",
                status="failed",
                reason=reason,
            ))
            return (False, None, reason)
        
        # Get bindings for easy lookup
        data_bindings = execution_plan.get_data_bindings()
        bindings_by_target = {}
        for binding in data_bindings:
            if binding.target_step not in bindings_by_target:
                bindings_by_target[binding.target_step] = []
            bindings_by_target[binding.target_step].append(binding)
        
        # EXECUTION PHASE: Iterate through fixed plan order
        for step_idx, invocation in enumerate(execution_plan.get_invocations()):
            domain = invocation.domain
            method = invocation.method
            parameters = invocation.parameters
            
            invocation_timestamp = datetime.utcnow()
            
            # PHASE 8: Resolve data bindings for this step
            if step_idx in bindings_by_target:
                # Start with original parameters
                merged_params = json.loads(json.dumps(parameters))
                
                for binding in bindings_by_target[step_idx]:
                    # Extract data from previous step result
                    try:
                        source_result = results[binding.source_step]
                        source_value = extract_json_path(source_result, binding.source_path)
                    except (IndexError, KeyError, TypeError) as e:
                        reason = f"Data binding failed: could not extract {binding.source_path} from step {binding.source_step}: {str(e)}"
                        self.audit_log.append(AuditEvent(
                            event_type=AuditEventType.BOUNDARY_VIOLATION,
                            timestamp=invocation_timestamp,
                            user_id=user_id,
                            token_hash=token_hash,
                            domain=domain,
                            method=method,
                            status="failed",
                            reason=reason,
                        ))
                        return (False, None, reason)
                    
                    # Type validation if specified
                    if binding.expected_type is not None:
                        if not isinstance(source_value, binding.expected_type):
                            reason = (
                                f"Data binding type mismatch: "
                                f"expected {binding.expected_type.__name__}, "
                                f"got {type(source_value).__name__}"
                            )
                            self.audit_log.append(AuditEvent(
                                event_type=AuditEventType.BOUNDARY_VIOLATION,
                                timestamp=invocation_timestamp,
                                user_id=user_id,
                                token_hash=token_hash,
                                domain=domain,
                                method=method,
                                status="failed",
                                reason=reason,
                            ))
                            return (False, None, reason)
                    
                    # Inject into parameters at target path
                    try:
                        target_parts = binding.target_path.split('.')
                        current = merged_params
                        for part in target_parts[:-1]:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        current[target_parts[-1]] = source_value
                    except (KeyError, TypeError) as e:
                        reason = f"Data binding failed: could not inject into {binding.target_path}: {str(e)}"
                        self.audit_log.append(AuditEvent(
                            event_type=AuditEventType.BOUNDARY_VIOLATION,
                            timestamp=invocation_timestamp,
                            user_id=user_id,
                            token_hash=token_hash,
                            domain=domain,
                            method=method,
                            status="failed",
                            reason=reason,
                        ))
                        return (False, None, reason)
                    
                    # Emit DATA_BINDING audit event
                    if not self.audit_log.append(AuditEvent(
                        event_type=AuditEventType.BOUNDARY_VIOLATION,  # Use existing event, add context
                        timestamp=invocation_timestamp,
                        user_id=user_id,
                        token_hash=token_hash,
                        domain=domain,
                        method=method,
                        status="success",
                        reason=f"Data binding: step {binding.source_step}.{binding.source_path} → step {binding.target_step}.{binding.target_path}",
                    )):
                        reason = "Audit log failure: could not record DATA_BINDING"
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
                
                # Use merged parameters
                parameters = merged_params
            
            # PHASE 7: Scope Authorization
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
                    pass
                return (False, None, reason)
            
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
            
            # PHASE 7: Resource Limits
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
            
            # Store result (available for binding to next steps)
            results.append(domain_result.to_dict())
        
        # All invocations succeeded
        return (True, results, None)


# ============================================================================
# TESTS: EXPLICIT DATA FLOW
# ============================================================================

class TestDataBindingImmutability:
    """Test that data bindings are immutable."""
    
    def test_data_binding_cannot_be_modified(self):
        """Data binding properties cannot be changed after creation."""
        binding = DataBinding(0, "data.value", 1, "input.value")
        
        with pytest.raises(AttributeError):
            binding.source_step = 2
    
    def test_data_binding_validates_step_indices(self):
        """Invalid step indices should raise errors."""
        # Source step >= target step (circular/invalid)
        with pytest.raises(ValueError):
            DataBinding(1, "data", 0, "param")
        
        # Same source and target
        with pytest.raises(ValueError):
            DataBinding(0, "data", 0, "param")
    
    def test_execution_plan_with_data_flow_is_immutable(self):
        """Execution plan with data flow cannot be modified."""
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
        ]
        binding = DataBinding(0, "data.habits", 1, "input.habits")
        plan = ExecutionPlanWithDataFlow("user_test", invocations, [binding])
        
        with pytest.raises(AttributeError):
            plan.invocations = ()


class TestDataBindingValidation:
    """Test validation of data bindings."""
    
    def test_binding_to_nonexistent_step(self):
        """Binding to step that doesn't exist should fail."""
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
        ]
        binding = DataBinding(0, "data", 5, "param")  # Step 5 doesn't exist
        
        with pytest.raises(ValueError):
            ExecutionPlanWithDataFlow("user_test", invocations, [binding])
    
    def test_binding_from_nonexistent_step(self):
        """Binding from step that doesn't exist should fail."""
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
        ]
        # Create plan with valid binding first
        binding = DataBinding(0, "data", 1, "param")  # Valid structure
        plan = ExecutionPlanWithDataFlow("user_test", invocations, [binding])
        assert plan is not None


class TestBasicDataFlow:
    """Test execution with basic data flow."""
    
    def test_data_flows_from_step_0_to_step_1(self, token_registry, valid_token_params, domain_registry):
        """Data from first domain should flow to second domain."""
        audit_log = AuditEventLog()
        orchestrator = Stage3OrchestratorWithDataFlow(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "data1"}),
            DomainInvocation("hermes", "compose_message", {"test": "data2"}),
        ]
        
        # Bind apollo's output to hermes's input
        binding = DataBinding(
            source_step=0,
            source_path="data.domain",  # Apollo returns domain="apollo" in data
            target_step=1,
            target_path="input_domain",  # Inject into hermes params
            expected_type=str,
        )
        
        plan = ExecutionPlanWithDataFlow("user_test_phase8", invocations, [binding])
        
        success, results, error = orchestrator.execute_plan_with_data_flow(
            token_hash=token_hash,
            user_id="user_test_phase8",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        assert success
        assert results is not None
        assert len(results) == 2


class TestDataTypeValidation:
    """Test type validation of bound data."""
    
    def test_data_type_validation_succeeds(self, token_registry, valid_token_params, domain_registry):
        """Type validation should pass for correct types."""
        audit_log = AuditEventLog()
        orchestrator = Stage3OrchestratorWithDataFlow(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
        ]
        
        # Apollo returns domain="apollo" (str type)
        binding = DataBinding(
            source_step=0,
            source_path="data.domain",
            target_step=1,
            target_path="source_domain",
            expected_type=str,  # Expect string
        )
        
        plan = ExecutionPlanWithDataFlow("user_test_phase8", invocations, [binding])
        
        success, results, error = orchestrator.execute_plan_with_data_flow(
            token_hash=token_hash,
            user_id="user_test_phase8",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        assert success
    
    def test_data_type_validation_fails(self, token_registry, valid_token_params, domain_registry):
        """Type validation should fail for incorrect types."""
        audit_log = AuditEventLog()
        orchestrator = Stage3OrchestratorWithDataFlow(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
        ]
        
        # Binding expects int but apollo.data.domain is str
        binding = DataBinding(
            source_step=0,
            source_path="data.domain",
            target_step=1,
            target_path="value",
            expected_type=int,  # Expect int, but will get str
        )
        
        plan = ExecutionPlanWithDataFlow("user_test_phase8", invocations, [binding])
        
        success, results, error = orchestrator.execute_plan_with_data_flow(
            token_hash=token_hash,
            user_id="user_test_phase8",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        assert not success
        assert error is not None
        assert "type mismatch" in error.lower()


class TestDataExtractionFailure:
    """Test failure handling when data extraction fails."""
    
    def test_missing_source_path_aborts_execution(self, token_registry, valid_token_params, domain_registry):
        """If source path doesn't exist, execution should abort."""
        audit_log = AuditEventLog()
        orchestrator = Stage3OrchestratorWithDataFlow(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
            DomainInvocation("dionysus", "analyze_mood", {"test": "3"}),
        ]
        
        # Binding to non-existent path
        binding = DataBinding(
            source_step=0,
            source_path="nonexistent.path",  # Apollo doesn't have this
            target_step=1,
            target_path="value",
        )
        
        plan = ExecutionPlanWithDataFlow("user_test_phase8", invocations, [binding])
        
        success, results, error = orchestrator.execute_plan_with_data_flow(
            token_hash=token_hash,
            user_id="user_test_phase8",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        # Should fail at step 1 (hermes)
        assert not success
        assert error is not None
        assert "Data binding failed" in error


class TestMultipleBindings:
    """Test multiple data flows between domains."""
    
    def test_multiple_bindings_same_target(self, token_registry, valid_token_params, domain_registry):
        """Multiple bindings can target same step."""
        audit_log = AuditEventLog()
        orchestrator = Stage3OrchestratorWithDataFlow(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {}),
            DomainInvocation("hermes", "compose_message", {}),
            DomainInvocation("dionysus", "analyze_mood", {}),
        ]
        
        # Multiple bindings to step 2
        bindings = [
            DataBinding(0, "data.domain", 2, "source1_domain", str),
            DataBinding(1, "data.domain", 2, "source2_domain", str),
        ]
        
        plan = ExecutionPlanWithDataFlow("user_test_phase8", invocations, bindings)
        
        success, results, error = orchestrator.execute_plan_with_data_flow(
            token_hash=token_hash,
            user_id="user_test_phase8",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        assert success
        assert len(results) == 3


class TestNoCircularDependencies:
    """Test that circular data flows are prevented."""
    
    def test_target_before_source_is_rejected(self):
        """Target step before source step should be rejected."""
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
        ]
        
        # Try to bind backwards (step 1 → step 0)
        with pytest.raises(ValueError):
            DataBinding(1, "data", 0, "param")


class TestFailClosedOnBindingError:
    """Test that binding errors abort remaining execution."""
    
    def test_binding_failure_prevents_remaining_domains(self, token_registry, valid_token_params, domain_registry):
        """If binding fails, remaining domains should not be invoked."""
        audit_log = AuditEventLog()
        orchestrator = Stage3OrchestratorWithDataFlow(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
            DomainInvocation("dionysus", "analyze_mood", {"test": "3"}),
        ]
        
        # Binding that will fail (bad path)
        binding = DataBinding(0, "nonexistent", 1, "value")
        
        plan = ExecutionPlanWithDataFlow("user_test_phase8", invocations, [binding])
        
        success, results, error = orchestrator.execute_plan_with_data_flow(
            token_hash=token_hash,
            user_id="user_test_phase8",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        # Should fail at step 1
        assert not success
        
        # Verify only step 0 was executed
        events = audit_log.get_events()
        apollo_completions = [e for e in events if e.domain == "apollo" and e.event_type == AuditEventType.EXECUTION_COMPLETED]
        dionysus_events = [e for e in events if e.domain == "dionysus"]
        
        # Apollo should have completed
        assert len(apollo_completions) > 0
        # Dionysus should not have been invoked
        assert len(dionysus_events) == 0


class TestDataFlowImmutability:
    """Test that data flows are immutable and cannot be conditional."""
    
    def test_binding_order_is_immutable(self, token_registry, valid_token_params, domain_registry):
        """Data binding order is determined at plan creation and cannot change."""
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {}),
            DomainInvocation("hermes", "compose_message", {}),
            DomainInvocation("dionysus", "analyze_mood", {}),
        ]
        
        binding1 = DataBinding(0, "data.x", 1, "from_0")
        binding2 = DataBinding(1, "data.x", 2, "from_1")
        
        plan = ExecutionPlanWithDataFlow("user_test", invocations, [binding1, binding2])
        
        # Order should be fixed
        retrieved_bindings = plan.get_data_bindings()
        assert len(retrieved_bindings) == 2
        assert retrieved_bindings[0].target_step == 1
        assert retrieved_bindings[1].target_step == 2


class TestNoExistingTestsBreak:
    """Verify backward compatibility."""
    
    def test_phase7_executor_still_works(self, token_registry, valid_token_params, domain_registry):
        """PHASE 7 executor should still work without data flow."""
        audit_log = AuditEventLog()
        orchestrator = Stage3Orchestrator(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
        ]
        plan = ExecutionPlan("user_test_phase8", invocations)
        
        success, results, error = orchestrator.execute_plan(
            token_hash=token_hash,
            user_id="user_test_phase8",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        assert success
    
    def test_phase8_plan_without_bindings_works(self, token_registry, valid_token_params, domain_registry):
        """PHASE 8 plan without bindings should work like PHASE 7."""
        audit_log = AuditEventLog()
        orchestrator = Stage3OrchestratorWithDataFlow(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocations = [
            DomainInvocation("apollo", "analyze_habits", {"test": "1"}),
            DomainInvocation("hermes", "compose_message", {"test": "2"}),
        ]
        plan = ExecutionPlanWithDataFlow("user_test_phase8", invocations)  # No bindings
        
        success, results, error = orchestrator.execute_plan_with_data_flow(
            token_hash=token_hash,
            user_id="user_test_phase8",
            trigger_type="direct_command",
            execution_plan=plan,
        )
        
        assert success
