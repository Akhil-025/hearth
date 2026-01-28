"""
PHASE 6: Stage-3 ↔ Stage-2 Real Domain Integration Tests

OBJECTIVE: Replace mocked Stage-2 handlers with a real Stage-2 domain interface
and prove:

1. Stage-3 invokes Stage-2 ONLY AFTER all gates pass
2. Parameters are passed immutably to Stage-2
3. Stage-2 cannot call back into Stage-3
4. Stage-2 cannot access tokens, audit logs, or context internals
5. Audit events are identical to PHASE 5 (no missing or reordered events)

CONSTRAINTS:
- Tests only (no production wiring changes)
- No new triggers, background execution, scheduling, or retries
- No refactors of PHASE 1-5 tests
- No new autonomy (Stage-2 must be passive)
- Single-shot, synchronous invocation only

ARCHITECTURE:
The Stage-2 domain interface is simple and passive:
- Can read immutable parameters only
- Cannot read Stage-3 internals (tokens, logs, audit context)
- Cannot call back into Stage-3
- Cannot spawn threads, schedule work, or access shared state
- Must return deterministic result or error

Stage-3 boundary enforcement:
- Create IsolatedParameters from request
- Call Stage-2 with isolated params + domain/method name only
- No token, registry, or audit log references passed
- Cannot Stage-2 bypass validation gates

Audit trail identical to PHASE 5:
- Same event types in same order
- Same causal ordering (validation → auth → execution → completion)
- No new events, no missing events, no reordered events
"""

import pytest
from datetime import datetime
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from enum import Enum
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


@pytest.fixture
def token_registry():
    """Fresh token registry for each test."""
    return TokenRegistry()


@pytest.fixture
def valid_token_params():
    """Standard valid token for testing."""
    return {
        "user_id": "user_test_phase6",
        "capability": "test_capability",
        "domain_scope": ["apollo", "hermes", "dionysus", "hephaestus"],
        "method_scope": {
            "apollo": ["analyze_habits", "plan_routine", "get_health_info"],
            "hermes": ["compose_message", "analyze_conversation", "draft_schedule"],
            "dionysus": ["analyze_mood", "recommend_music", "plan_leisure"],
            "hephaestus": ["analyze_code", "design_system", "debug_issue"],
        },
        "duration_seconds": 900,
        "resource_limits": {
            "max_invocations": 10,
            "max_tokens_per_response": 512,
            "max_total_tokens": 2048,
            "max_frequency": "1 per 10 seconds",
        },
        "allowed_trigger_types": ["direct_command"],
        "issued_by": "user_test_phase6",
    }


# ============================================================================
# STAGE-2 DOMAIN INTERFACE AND IMPLEMENTATIONS
# ============================================================================

class Stage2DomainInterface(ABC):
    """
    Abstract interface that Stage-2 domains must implement.
    
    CRITICAL CONSTRAINTS:
    - Must be stateless (no shared state, no persistence)
    - Must be passive (cannot call back to Stage-3)
    - Must accept only immutable parameters
    - Must NOT have access to tokens, audit logs, or executor context
    - Must return deterministic results
    """
    
    @abstractmethod
    def invoke(
        self,
        method: str,
        parameters: IsolatedParameters,
    ) -> MockDomainResult:
        """
        Invoke domain method with isolated parameters.
        
        Args:
            method: Method name (e.g., "analyze_habits")
            parameters: Immutable, isolated parameters container
        
        Returns:
            MockDomainResult with success bool and data/error
        
        Raises:
            Nothing - must catch exceptions and return error result
        """
        pass


class ApolloTestDomain(Stage2DomainInterface):
    """Test implementation of Apollo domain (health/wellness)."""
    
    def invoke(self, method: str, parameters: IsolatedParameters) -> MockDomainResult:
        """Invoke Apollo domain method with isolated parameters."""
        try:
            # Get immutable copy of parameters
            params = parameters.get_copy()
            
            # Route to method
            if method == "analyze_habits":
                return self._analyze_habits(params)
            elif method == "plan_routine":
                return self._plan_routine(params)
            elif method == "get_health_info":
                return self._get_health_info(params)
            else:
                return MockDomainResult(
                    success=False,
                    error=f"Unknown method: {method}"
                )
        except Exception as e:
            return MockDomainResult(
                success=False,
                error=f"Apollo domain error: {str(e)}"
            )
    
    def _analyze_habits(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic habit analysis."""
        habits = params.get("habits", [])
        return MockDomainResult(
            success=True,
            data={
                "domain": "apollo",
                "method": "analyze_habits",
                "habits_analyzed": len(habits),
                "analysis": {"pattern": "regular", "consistency": 0.85}
            }
        )
    
    def _plan_routine(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic routine planning."""
        goals = params.get("goals", [])
        return MockDomainResult(
            success=True,
            data={
                "domain": "apollo",
                "method": "plan_routine",
                "goals_count": len(goals),
                "routine": {"duration_days": 30, "checkpoint_interval": 7}
            }
        )
    
    def _get_health_info(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic health information retrieval."""
        topic = params.get("topic", "general")
        return MockDomainResult(
            success=True,
            data={
                "domain": "apollo",
                "method": "get_health_info",
                "topic": topic,
                "info": "Educational health information (no medical advice)"
            }
        )


class HermesTestDomain(Stage2DomainInterface):
    """Test implementation of Hermes domain (communication)."""
    
    def invoke(self, method: str, parameters: IsolatedParameters) -> MockDomainResult:
        """Invoke Hermes domain method with isolated parameters."""
        try:
            params = parameters.get_copy()
            
            if method == "compose_message":
                return self._compose_message(params)
            elif method == "analyze_conversation":
                return self._analyze_conversation(params)
            elif method == "draft_schedule":
                return self._draft_schedule(params)
            else:
                return MockDomainResult(
                    success=False,
                    error=f"Unknown method: {method}"
                )
        except Exception as e:
            return MockDomainResult(
                success=False,
                error=f"Hermes domain error: {str(e)}"
            )
    
    def _compose_message(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic message composition."""
        message_type = params.get("type", "generic")
        return MockDomainResult(
            success=True,
            data={
                "domain": "hermes",
                "method": "compose_message",
                "type": message_type,
                "message": f"Composed {message_type} message"
            }
        )
    
    def _analyze_conversation(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic conversation analysis."""
        messages = params.get("messages", [])
        return MockDomainResult(
            success=True,
            data={
                "domain": "hermes",
                "method": "analyze_conversation",
                "message_count": len(messages),
                "analysis": {"tone": "neutral", "sentiment": 0.5}
            }
        )
    
    def _draft_schedule(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic schedule drafting."""
        events = params.get("events", [])
        return MockDomainResult(
            success=True,
            data={
                "domain": "hermes",
                "method": "draft_schedule",
                "events_count": len(events),
                "schedule": {"duration_days": 7, "status": "ready"}
            }
        )


class DionysusTestDomain(Stage2DomainInterface):
    """Test implementation of Dionysus domain (creativity/leisure)."""
    
    def invoke(self, method: str, parameters: IsolatedParameters) -> MockDomainResult:
        """Invoke Dionysus domain method with isolated parameters."""
        try:
            params = parameters.get_copy()
            
            if method == "analyze_mood":
                return self._analyze_mood(params)
            elif method == "recommend_music":
                return self._recommend_music(params)
            elif method == "plan_leisure":
                return self._plan_leisure(params)
            else:
                return MockDomainResult(
                    success=False,
                    error=f"Unknown method: {method}"
                )
        except Exception as e:
            return MockDomainResult(
                success=False,
                error=f"Dionysus domain error: {str(e)}"
            )
    
    def _analyze_mood(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic mood analysis."""
        indicators = params.get("mood_indicators", [])
        return MockDomainResult(
            success=True,
            data={
                "domain": "dionysus",
                "method": "analyze_mood",
                "indicators_count": len(indicators),
                "mood": "balanced"
            }
        )
    
    def _recommend_music(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic music recommendation."""
        mood = params.get("mood", "neutral")
        return MockDomainResult(
            success=True,
            data={
                "domain": "dionysus",
                "method": "recommend_music",
                "mood": mood,
                "recommendations": ["track_1", "track_2", "track_3"]
            }
        )
    
    def _plan_leisure(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic leisure planning."""
        preferences = params.get("preferences", [])
        return MockDomainResult(
            success=True,
            data={
                "domain": "dionysus",
                "method": "plan_leisure",
                "preferences_count": len(preferences),
                "plan": {"activities": ["read", "walk", "create"]}
            }
        )


class HephaestusTestDomain(Stage2DomainInterface):
    """Test implementation of Hephaestus domain (technology/engineering)."""
    
    def invoke(self, method: str, parameters: IsolatedParameters) -> MockDomainResult:
        """Invoke Hephaestus domain method with isolated parameters."""
        try:
            params = parameters.get_copy()
            
            if method == "analyze_code":
                return self._analyze_code(params)
            elif method == "design_system":
                return self._design_system(params)
            elif method == "debug_issue":
                return self._debug_issue(params)
            else:
                return MockDomainResult(
                    success=False,
                    error=f"Unknown method: {method}"
                )
        except Exception as e:
            return MockDomainResult(
                success=False,
                error=f"Hephaestus domain error: {str(e)}"
            )
    
    def _analyze_code(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic code analysis."""
        code_snippets = params.get("code", [])
        return MockDomainResult(
            success=True,
            data={
                "domain": "hephaestus",
                "method": "analyze_code",
                "snippets_analyzed": len(code_snippets),
                "analysis": {"style_score": 0.85, "complexity": "moderate"}
            }
        )
    
    def _design_system(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic system design."""
        requirements = params.get("requirements", [])
        return MockDomainResult(
            success=True,
            data={
                "domain": "hephaestus",
                "method": "design_system",
                "requirements_count": len(requirements),
                "design": {"architecture": "layered", "scalability": "high"}
            }
        )
    
    def _debug_issue(self, params: Dict[str, Any]) -> MockDomainResult:
        """Deterministic debugging assistance."""
        issue = params.get("issue", "")
        return MockDomainResult(
            success=True,
            data={
                "domain": "hephaestus",
                "method": "debug_issue",
                "issue": issue,
                "diagnosis": {"root_cause": "identified", "solution": "provided"}
            }
        )


class DomainRegistry:
    """Maps domain names to domain implementations."""
    
    def __init__(self):
        """Initialize domain registry with test implementations."""
        self.domains: Dict[str, Stage2DomainInterface] = {
            "apollo": ApolloTestDomain(),
            "hermes": HermesTestDomain(),
            "dionysus": DionysusTestDomain(),
            "hephaestus": HephaestusTestDomain(),
        }
    
    def get_domain(self, domain: str) -> Optional[Stage2DomainInterface]:
        """Get domain implementation."""
        return self.domains.get(domain)


@pytest.fixture
def domain_registry():
    """Fresh domain registry for each test."""
    return DomainRegistry()


# ============================================================================
# STAGE-3 EXECUTOR WITH REAL DOMAIN INTEGRATION
# ============================================================================

class Stage3ExecutorWithRealDomains(Stage3Executor):
    """
    Extended Stage3Executor that invokes real Stage-2 domains instead of mocks.
    Inherits all validation gates from Stage3Executor.
    """
    
    def __init__(
        self,
        token_registry: TokenRegistry,
        audit_log: AuditEventLog,
        domain_registry: DomainRegistry,
    ):
        """
        Initialize executor with real domain registry.
        
        Args:
            token_registry: Token validation
            audit_log: Audit event recording
            domain_registry: Stage-2 domain implementations
        """
        # Initialize parent with no-op handler (will override)
        super().__init__(token_registry, audit_log, self._domain_handler)
        self.domain_registry = domain_registry
    
    def _domain_handler(
        self,
        domain: str,
        method: str,
        params: IsolatedParameters
    ) -> MockDomainResult:
        """
        Route to real Stage-2 domain.
        
        CRITICAL: Domain receives ONLY isolated parameters, never:
        - Token registry
        - Audit log
        - Executor internals
        - User context
        - Any Stage-3 references
        """
        # Get domain
        domain_impl = self.domain_registry.get_domain(domain)
        if not domain_impl:
            return MockDomainResult(
                success=False,
                error=f"Domain not found: {domain}"
            )
        
        # Invoke domain with isolated parameters only
        return domain_impl.invoke(method, params)


# ============================================================================
# TESTS: REAL DOMAIN INTEGRATION
# ============================================================================

class TestRealDomainInvocation:
    """Test that Stage-3 invokes real Stage-2 domains correctly."""
    
    def test_stage3_invokes_apollo_domain(self, token_registry, valid_token_params):
        """Stage-3 should invoke Apollo domain after all gates pass."""
        audit_log = AuditEventLog()
        domain_registry = DomainRegistry()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        # Create and register token
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Execute Apollo method
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={"habits": ["exercise", "sleep", "nutrition"]},
        )
        
        # Should succeed
        assert success
        assert result is not None
        assert error is None
        
        # Result should be from Apollo domain
        assert result["data"]["domain"] == "apollo"
        assert result["data"]["method"] == "analyze_habits"
        assert result["data"]["habits_analyzed"] == 3
    
    def test_stage3_invokes_hermes_domain(self, token_registry, valid_token_params):
        """Stage-3 should invoke Hermes domain after all gates pass."""
        audit_log = AuditEventLog()
        domain_registry = DomainRegistry()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Execute Hermes method
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="hermes",
            method="compose_message",
            parameters={"type": "greeting"},
        )
        
        # Should succeed
        assert success
        assert result is not None
        assert result["data"]["domain"] == "hermes"
        assert result["data"]["method"] == "compose_message"
    
    def test_stage3_invokes_dionysus_domain(self, token_registry, valid_token_params):
        """Stage-3 should invoke Dionysus domain after all gates pass."""
        audit_log = AuditEventLog()
        domain_registry = DomainRegistry()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Execute Dionysus method
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="dionysus",
            method="analyze_mood",
            parameters={"mood_indicators": ["happy", "energetic"]},
        )
        
        assert success
        assert result["data"]["domain"] == "dionysus"
        assert result["data"]["method"] == "analyze_mood"
    
    def test_stage3_invokes_hephaestus_domain(self, token_registry, valid_token_params):
        """Stage-3 should invoke Hephaestus domain after all gates pass."""
        audit_log = AuditEventLog()
        domain_registry = DomainRegistry()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Execute Hephaestus method
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="hephaestus",
            method="analyze_code",
            parameters={"code": ["def foo(): pass", "def bar(): return 42"]},
        )
        
        assert success
        assert result["data"]["domain"] == "hephaestus"
        assert result["data"]["method"] == "analyze_code"


class TestValidationGatesEnforcedBeforeDomainInvocation:
    """Test that all validation gates must pass before domain invocation."""
    
    def test_revoked_token_prevents_domain_invocation(self, token_registry, valid_token_params):
        """Revoked token should prevent domain invocation."""
        audit_log = AuditEventLog()
        domain_registry = DomainRegistry()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Revoke token
        token_registry.revoke_token(token_hash)
        
        # Try to invoke domain
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={},
        )
        
        # Should not invoke domain
        assert not success
        assert error is not None
        assert "revoked" in error.lower()
        
        # Verify no EXECUTION_STARTED event (domain was not invoked)
        events = audit_log.get_events()
        event_types = [e.event_type.value for e in events]
        assert "EXECUTION_STARTED" not in event_types
    
    def test_unauthorized_domain_prevents_invocation(self, token_registry, valid_token_params):
        """Unauthorized domain should prevent invocation."""
        # Create token with limited domains
        limited_token_params = valid_token_params.copy()
        limited_token_params["domain_scope"] = ["apollo"]  # Only apollo
        limited_token_params["method_scope"] = {"apollo": ["analyze_habits", "plan_routine", "get_health_info"]}
        
        audit_log = AuditEventLog()
        domain_registry = DomainRegistry()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**limited_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Try to invoke unauthorized domain
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="hermes",  # Not in scope
            method="compose_message",
            parameters={},
        )
        
        # Should not invoke domain
        assert not success
        assert error is not None
        assert "domain" in error.lower() and "scope" in error.lower()
        
        # Verify no EXECUTION_STARTED event
        events = audit_log.get_events()
        event_types = [e.event_type.value for e in events]
        assert "EXECUTION_STARTED" not in event_types
    
    def test_unauthorized_method_prevents_invocation(self, token_registry, valid_token_params):
        """Unauthorized method should prevent invocation."""
        # Create token with limited methods
        limited_token_params = valid_token_params.copy()
        limited_token_params["method_scope"] = {
            "apollo": ["analyze_habits"]  # Only this method
        }
        
        audit_log = AuditEventLog()
        domain_registry = DomainRegistry()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**limited_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Try to invoke unauthorized method
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="plan_routine",  # Not in scope
            parameters={},
        )
        
        # Should not invoke domain
        assert not success
        assert error is not None
        
        # Verify no EXECUTION_STARTED event
        events = audit_log.get_events()
        event_types = [e.event_type.value for e in events]
        assert "EXECUTION_STARTED" not in event_types


class TestParameterImmutabilityAcrossBoundary:
    """Test that parameters remain immutable when passed to Stage-2."""
    
    def test_domain_receives_only_isolated_parameters(self, token_registry, valid_token_params):
        """Domain should receive only IsolatedParameters, never raw dicts or internals."""
        audit_log = AuditEventLog()
        
        # Track what domain received
        received_params = []
        
        class ParameterCheckingDomain(Stage2DomainInterface):
            def invoke(self, method: str, parameters: IsolatedParameters) -> MockDomainResult:
                received_params.append(parameters)
                # Verify parameters are IsolatedParameters instance
                if isinstance(parameters, IsolatedParameters):
                    return MockDomainResult(success=True, data={"type_correct": True})
                return MockDomainResult(success=False, error="Parameters not IsolatedParameters")
        
        # Domain registry with checking domain
        domain_registry = DomainRegistry()
        domain_registry.domains["apollo"] = ParameterCheckingDomain()
        
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Execute
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={"habits": ["exercise"]},
        )
        
        assert success
        assert result["data"]["type_correct"] is True
        # Verify domain received IsolatedParameters
        assert len(received_params) > 0
        assert isinstance(received_params[0], IsolatedParameters)
    
    def test_domain_cannot_modify_isolated_parameters(self, token_registry, valid_token_params):
        """Domain should not be able to modify immutable parameters."""
        audit_log = AuditEventLog()
        
        class ParameterModifyingDomain(Stage2DomainInterface):
            def invoke(self, method: str, parameters: IsolatedParameters) -> MockDomainResult:
                # Try to modify parameters (should fail with AttributeError)
                try:
                    parameters._params = {"modified": True}
                    return MockDomainResult(success=False, error="Modified parameters!")
                except AttributeError:
                    # Expected - parameters should be immutable
                    return MockDomainResult(success=True, data={"immutable": True})
        
        domain_registry = DomainRegistry()
        domain_registry.domains["apollo"] = ParameterModifyingDomain()
        
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={"habits": ["exercise"]},
        )
        
        assert success
        assert result["data"]["immutable"] is True


class TestStage2CannotAccessStage3Internals:
    """Test that Stage-2 cannot access Stage-3 internal state."""
    
    def test_stage2_receives_only_isolated_parameters(self, token_registry, valid_token_params):
        """Domain should receive ONLY isolated parameters, never internals."""
        audit_log = AuditEventLog()
        
        class SecurityCheckingDomain(Stage2DomainInterface):
            def invoke(self, method: str, parameters: IsolatedParameters) -> MockDomainResult:
                # Verify that ONLY isolated parameters were passed, nothing else
                # Cannot access:
                # - token_registry
                # - audit_log
                # - executor context
                # - user identity beyond method name
                # Only isolation check: is parameters an IsolatedParameters?
                if isinstance(parameters, IsolatedParameters):
                    # Get immutable copy - this is safe
                    params_dict = parameters.get_copy()
                    if isinstance(params_dict, dict):
                        return MockDomainResult(success=True, data={"security": "pass"})
                return MockDomainResult(success=False, error="Security check failed")
        
        domain_registry = DomainRegistry()
        domain_registry.domains["apollo"] = SecurityCheckingDomain()
        
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={"data": "test"},
        )
        
        assert success
        assert result["data"]["security"] == "pass"
    
    def test_stage2_cannot_access_executor_context(self, token_registry, valid_token_params):
        """Domain methods should not receive token registry or audit log."""
        audit_log = AuditEventLog()
        
        class InvasionAttemptDomain(Stage2DomainInterface):
            def invoke(self, method: str, parameters: IsolatedParameters) -> MockDomainResult:
                # Try to access Stage-3 internals via parameters (should not be there)
                params_dict = parameters.get_copy()
                
                # These should NOT be in parameters
                invasive_keys = ["token_registry", "audit_log", "executor", "user_id", "token_hash"]
                for key in invasive_keys:
                    if key in params_dict:
                        return MockDomainResult(success=False, error=f"Found {key} in parameters!")
                
                # Only parameters passed should be user-provided ones
                return MockDomainResult(success=True, data={"isolated": True})
        
        domain_registry = DomainRegistry()
        domain_registry.domains["apollo"] = InvasionAttemptDomain()
        
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={"user_data": "should_be_safe"},
        )
        
        assert success
        assert result["data"]["isolated"] is True


class TestAuditEventsIdenticalToPhase5:
    """Test that audit events are identical to PHASE 5 (no changes in event stream)."""
    
    def test_successful_execution_emits_identical_events_to_phase5(self, token_registry, valid_token_params):
        """Successful execution should emit same audit events as PHASE 5."""
        audit_log = AuditEventLog()
        domain_registry = DomainRegistry()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Execute successfully
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={"habits": ["exercise"]},
        )
        
        assert success
        
        # Verify event sequence matches PHASE 5 specification
        events = audit_log.get_events()
        event_types = [e.event_type.value for e in events]
        
        # Expected event sequence for successful execution:
        # 1. TOKEN_VALIDATION
        # 2. AUTHORIZATION_SCOPE_CHECK
        # 3. RESOURCE_LIMIT_CHECK
        # 4. EXECUTION_STARTED
        # 5. EXECUTION_COMPLETED
        expected_sequence = [
            "TOKEN_VALIDATION",
            "AUTHORIZATION_SCOPE_CHECK",
            "RESOURCE_LIMIT_CHECK",
            "EXECUTION_STARTED",
            "EXECUTION_COMPLETED",
        ]
        
        assert event_types == expected_sequence, \
            f"Event sequence mismatch. Got: {event_types}, Expected: {expected_sequence}"
    
    def test_failed_execution_emits_identical_denial_events(self, token_registry, valid_token_params):
        """Failed execution should emit same denial events as PHASE 5."""
        audit_log = AuditEventLog()
        domain_registry = DomainRegistry()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        # Execute with invalid token
        success, result, error = executor.execute(
            token_hash="invalid_token",
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={},
        )
        
        assert not success
        
        # Verify only EXECUTION_DENIED event is present
        events = audit_log.get_events()
        event_types = [e.event_type.value for e in events]
        
        # Should only have EXECUTION_DENIED
        assert event_types == ["EXECUTION_DENIED"], \
            f"Failed execution should only emit EXECUTION_DENIED. Got: {event_types}"
    
    def test_denied_events_have_reasons_identical_to_phase5(self, token_registry, valid_token_params):
        """All EXECUTION_DENIED events should have reasons."""
        audit_log = AuditEventLog()
        domain_registry = DomainRegistry()
        executor = Stage3ExecutorWithRealDomains(token_registry, audit_log, domain_registry)
        
        # Execute with invalid domain
        success, result, error = executor.execute(
            token_hash="invalid",
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={},
        )
        
        assert not success
        
        # Verify all denial events have reasons
        events = audit_log.get_events()
        denial_events = [e for e in events if e.event_type.value == "EXECUTION_DENIED"]
        
        assert len(denial_events) > 0
        for event in denial_events:
            assert event.reason is not None, "Denial event must have reason"
            assert len(event.reason) > 0, "Reason must be non-empty"


class TestNoExistingTestsBreak:
    """Verify that new real domain integration doesn't break existing tests."""
    
    def test_phase5_executor_still_works(self, token_registry, valid_token_params):
        """Original Stage3Executor from PHASE 5 should still work."""
        audit_log = AuditEventLog()
        executor = Stage3Executor(token_registry, audit_log)
        
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        success, result, error = executor.execute(
            token_hash=token_hash,
            user_id="user_test_phase6",
            trigger_type="direct_command",
            domain="apollo",
            method="analyze_habits",
            parameters={"test": "data"},
        )
        
        # Should succeed with default mock handler
        assert success
        assert result is not None
    
    def test_token_registry_independent(self, token_registry, valid_token_params):
        """TokenRegistry should work independently."""
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Should be able to retrieve without executor
        retrieved = token_registry.get_token(token_hash)
        assert retrieved is not None
        assert retrieved.user_id == "user_test_phase6"
    
    def test_audit_log_independent(self):
        """AuditEventLog should work independently."""
        audit_log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_ISSUED,
            timestamp=datetime.utcnow(),
            user_id="test_user",
            token_hash="test_hash",
            domain="test_domain",
            method="test_method",
            status="success",
        )
        
        success = audit_log.append(event)
        assert success
        assert len(audit_log.get_events()) == 1
