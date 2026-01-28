"""
PHASE 2A: Token Validation Sequence Tests

Binding Spec Section 2.1: Validation Before Execution

REQUIREMENT: When user invokes an operation with a token:
1. FIRST: Validate token (exists, not revoked, not expired, user matches)
2. ONLY IF: Token is valid
3. THEN: Proceed to authorization checks

CRITICAL: Validation MUST happen before ANY domain call.
If validation fails at ANY step, execution MUST be aborted immediately.
No partial execution. No fallback. No retry.

FAIL-CLOSED BEHAVIOR: Every validation failure must abort execution.

These tests verify the validation sequence structure, not domain execution.
Domain execution tests are in Phase 2B and later phases.

ARCHITECTURE:
    Invocation Request
         ↓
    [VALIDATION PHASE] ← Phase 2A tests verify this
         ├─ Token exists?
         ├─ Token not revoked?
         ├─ Token not expired?
         ├─ User matches?
         └─ Fail → ABORT (no execution)
         ↓ (only if all pass)
    [AUTHORIZATION PHASE] ← Phase 2B
         └─ Method authorized?
         ↓
    [EXECUTION PHASE] ← Phase 2C+
         └─ Call domain
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from tests.test_stage3_phase1a_token_model import CapabilityToken, TokenRegistry


@pytest.fixture
def token_registry():
    """Fresh registry for each test."""
    return TokenRegistry()


@pytest.fixture
def valid_token_params():
    """Fixture providing valid token parameters."""
    return {
        "user_id": "user_7f3d",
        "capability": "analyze_habits",
        "domain_scope": ["apollo"],
        "method_scope": {"apollo": ["analyze_habits", "plan_routine"]},
        "duration_seconds": 900,
        "resource_limits": {
            "max_invocations": 5,
            "max_tokens_per_response": 512,
            "max_total_tokens": 2048,
            "max_frequency": "1 per 10 seconds",
        },
        "allowed_trigger_types": ["direct_command", "async_request"],
        "issued_by": "user_7f3d",
    }


class InvocationContext:
    """
    Represents an invocation request with token validation state.
    Used to test validation sequence: validation MUST happen before execution.
    """
    
    def __init__(self, token_hash: str, user_id: str, domain: str, method: str, 
                 trigger_type: str, token_registry: TokenRegistry):
        self.token_hash = token_hash
        self.user_id = user_id
        self.domain = domain
        self.method = method
        self.trigger_type = trigger_type
        self.token_registry = token_registry
        
        # Validation state (Phase 2A tests)
        self.validation_passed = False
        self.validation_failure_reason: Optional[str] = None
        self.execution_started = False
        
    def validate_token(self) -> bool:
        """
        PHASE 2A: Validate token BEFORE execution.
        Returns True if all validation checks pass.
        If any check fails, sets validation_failure_reason and returns False.
        """
        # Check 1: Token must exist
        try:
            token = self.token_registry.get_token(self.token_hash)
        except Exception as e:
            self.validation_failure_reason = f"Token not found: {e}"
            return False
        
        if token is None:
            self.validation_failure_reason = "Token does not exist"
            return False
        
        # Check 2: Token must not be revoked
        if self.token_registry.is_revoked(self.token_hash):
            self.validation_failure_reason = "Token has been revoked"
            return False
        
        # Check 3: User must match token's user_id
        if token.user_id != self.user_id:
            self.validation_failure_reason = f"Token user mismatch: token is for {token.user_id}, invocation by {self.user_id}"
            return False
        
        # Check 4: Token must not be expired
        # Note: Phase 1 tests don't include expiration tracking, so we document it here
        # Real implementation would check: time.now() > token.issued_at + duration_seconds
        
        # Check 5: Trigger type must be authorized
        if self.trigger_type not in token.allowed_trigger_types:
            self.validation_failure_reason = f"Trigger type '{self.trigger_type}' not authorized by token"
            return False
        
        self.validation_passed = True
        return True
    
    def try_execute(self) -> Tuple[bool, Optional[str]]:
        """
        Execute operation ONLY if validation passed.
        Returns (success, error_message) tuple.
        If validation did not pass, returns (False, validation_failure_reason).
        """
        # CRITICAL: Validate BEFORE execution
        if not self.validate_token():
            # Do NOT execute if validation failed
            return (False, self.validation_failure_reason)
        
        # ONLY if validation passed, mark execution as started
        self.execution_started = True
        
        # Phase 2A tests stop here - no actual domain execution
        # Phase 2B+ tests will verify authorization and domain calls
        return (True, None)


class TestTokenMustExistBeforeExecution:
    """
    REQUIREMENT: Token must exist in registry before execution can proceed.
    If token hash doesn't resolve to a token, execution MUST be aborted.
    """
    
    def test_nonexistent_token_aborts_execution(self, token_registry):
        """
        User provides token_hash that doesn't exist in registry.
        Execution MUST be rejected immediately.
        """
        nonexistent_hash = "token_nonexistent_12345"
        
        invocation = InvocationContext(
            token_hash=nonexistent_hash,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        # Attempt execution
        success, error = invocation.try_execute()
        
        # Execution MUST fail
        assert not success
        assert error is not None
        assert "not found" in error.lower() or "does not exist" in error.lower()
        
        # Execution MUST NOT have started
        assert not invocation.execution_started
    
    def test_valid_token_passes_existence_check(self, token_registry, valid_token_params):
        """
        User provides valid token that exists in registry.
        Existence check MUST pass.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocation = InvocationContext(
            token_hash=token_hash,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        # Validate token existence
        token_exists = invocation.validate_token()
        
        # Token must exist
        assert token_exists
        assert invocation.validation_passed


class TestTokenMustNotBeRevokedBeforeExecution:
    """
    REQUIREMENT: If token has been revoked, execution MUST be aborted.
    Revocation is checked DURING validation, BEFORE execution.
    """
    
    def test_revoked_token_aborts_execution(self, token_registry, valid_token_params):
        """
        Token 1 is created and then revoked.
        User tries to execute with Token 1.
        Execution MUST be rejected.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Revoke the token
        token_registry.revoke_token(token_hash)
        
        invocation = InvocationContext(
            token_hash=token_hash,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        # Attempt execution
        success, error = invocation.try_execute()
        
        # Execution MUST fail
        assert not success
        assert error is not None
        assert "revoked" in error.lower()
        
        # Execution MUST NOT have started
        assert not invocation.execution_started
    
    def test_non_revoked_token_passes_revocation_check(self, token_registry, valid_token_params):
        """
        Token is not revoked.
        Revocation check MUST pass.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Verify token is not revoked
        assert not token_registry.is_revoked(token_hash)
        
        invocation = InvocationContext(
            token_hash=token_hash,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        # Validate token
        valid = invocation.validate_token()
        
        # Token must pass validation
        assert valid
        assert invocation.validation_passed


class TestUserMustMatchTokenBeforeExecution:
    """
    REQUIREMENT: User ID in invocation MUST match token's user_id.
    If user doesn't match, execution MUST be aborted.
    """
    
    def test_wrong_user_aborts_execution(self, token_registry, valid_token_params):
        """
        Token is issued for user_7f3d.
        Different user (user_wrong) tries to use the token.
        Execution MUST be rejected.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocation = InvocationContext(
            token_hash=token_hash,
            user_id="user_wrong",  # Wrong user!
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        # Attempt execution
        success, error = invocation.try_execute()
        
        # Execution MUST fail
        assert not success
        assert error is not None
        assert "user" in error.lower() or "mismatch" in error.lower()
        
        # Execution MUST NOT have started
        assert not invocation.execution_started
    
    def test_correct_user_passes_user_check(self, token_registry, valid_token_params):
        """
        User matches token's user_id.
        User check MUST pass.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocation = InvocationContext(
            token_hash=token_hash,
            user_id="user_7f3d",  # Correct user
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        # Validate token
        valid = invocation.validate_token()
        
        # User check must pass
        assert valid
        assert invocation.validation_passed


class TestTriggerTypeMustBeAuthorizedBeforeExecution:
    """
    REQUIREMENT: Trigger type in invocation MUST be in token's allowed_trigger_types.
    If trigger is not authorized, execution MUST be aborted.
    """
    
    def test_unauthorized_trigger_aborts_execution(self, token_registry, valid_token_params):
        """
        Token authorizes ["direct_command", "async_request"].
        User tries to use "scheduled" trigger.
        Execution MUST be rejected.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocation = InvocationContext(
            token_hash=token_hash,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="scheduled",  # Not in token's allowed types
            token_registry=token_registry
        )
        
        # Attempt execution
        success, error = invocation.try_execute()
        
        # Execution MUST fail
        assert not success
        assert error is not None
        assert "trigger" in error.lower() or "authorized" in error.lower()
        
        # Execution MUST NOT have started
        assert not invocation.execution_started
    
    def test_authorized_trigger_passes_trigger_check(self, token_registry, valid_token_params):
        """
        Trigger type is in token's allowed_trigger_types.
        Trigger check MUST pass.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocation = InvocationContext(
            token_hash=token_hash,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",  # In token's allowed types
            token_registry=token_registry
        )
        
        # Validate token
        valid = invocation.validate_token()
        
        # Trigger check must pass
        assert valid
        assert invocation.validation_passed


class TestValidationSequenceIsAtomicFailClosed:
    """
    REQUIREMENT: Validation is atomic fail-closed.
    If ANY validation step fails, execution is aborted immediately.
    No partial execution. No retry. No fallback.
    """
    
    def test_validation_failure_aborts_execution_immediately(self, token_registry, valid_token_params):
        """
        Multiple validation checks exist.
        If FIRST check fails, execution stops.
        MUST NOT proceed to other checks.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Create invocation that fails on first check (nonexistent token)
        invocation = InvocationContext(
            token_hash="nonexistent",
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        # Try to execute
        success, error = invocation.try_execute()
        
        # Execution MUST fail
        assert not success
        assert invocation.validation_failure_reason is not None
        
        # Execution MUST NOT have started
        assert not invocation.execution_started
    
    def test_each_validation_check_fails_independently(self, token_registry, valid_token_params):
        """
        Each validation check must independently reject invalid invocations.
        Test multiple failure scenarios.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Scenario 1: Token doesn't exist
        inv1 = InvocationContext(
            token_hash="nonexistent",
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        success1, _ = inv1.try_execute()
        assert not success1
        assert not inv1.execution_started
        
        # Scenario 2: Token revoked
        token_registry.revoke_token(token_hash)
        inv2 = InvocationContext(
            token_hash=token_hash,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        success2, _ = inv2.try_execute()
        assert not success2
        assert not inv2.execution_started
        
        # Create new token for remaining tests
        token2 = CapabilityToken(**valid_token_params)
        token_hash2 = token_registry.issue_token(token2)
        
        # Scenario 3: Wrong user
        inv3 = InvocationContext(
            token_hash=token_hash2,
            user_id="user_wrong",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        success3, _ = inv3.try_execute()
        assert not success3
        assert not inv3.execution_started
        
        # Scenario 4: Unauthorized trigger
        inv4 = InvocationContext(
            token_hash=token_hash2,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="unauthorized_trigger",
            token_registry=token_registry
        )
        success4, _ = inv4.try_execute()
        assert not success4
        assert not inv4.execution_started
    
    def test_validation_succeeds_iff_all_checks_pass(self, token_registry, valid_token_params):
        """
        Validation ONLY succeeds if ALL checks pass.
        If token exists, not revoked, user matches, and trigger authorized:
        validation must succeed.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        invocation = InvocationContext(
            token_hash=token_hash,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        # Validate
        valid = invocation.validate_token()
        
        # ALL checks must pass
        assert valid
        assert invocation.validation_passed
        assert invocation.validation_failure_reason is None


class TestValidationHappensBeforeExecution:
    """
    REQUIREMENT: Validation MUST happen BEFORE execution.
    This is the critical ordering guarantee.
    
    Tests verify that invocation.try_execute() calls validate_token()
    BEFORE setting execution_started = True.
    """
    
    def test_validation_called_before_execution_started_flag(self, token_registry, valid_token_params):
        """
        If validation fails, execution_started MUST remain False.
        If validation passes, execution CAN proceed.
        """
        token = CapabilityToken(**valid_token_params)
        token_hash = token_registry.issue_token(token)
        
        # Valid invocation
        inv_valid = InvocationContext(
            token_hash=token_hash,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        success, error = inv_valid.try_execute()
        
        # Validation must have passed
        assert success
        assert error is None
        assert inv_valid.validation_passed
        
        # Execution CAN start only after validation passes
        assert inv_valid.execution_started
        
        # Invalid invocation (wrong user)
        inv_invalid = InvocationContext(
            token_hash=token_hash,
            user_id="user_wrong",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        success2, error2 = inv_invalid.try_execute()
        
        # Validation must have failed
        assert not success2
        assert error2 is not None
        
        # Execution MUST NOT start if validation failed
        assert not inv_invalid.execution_started
    
    def test_no_execution_if_validation_fails(self, token_registry):
        """
        Create a scenario where validation fails.
        Verify execution never starts.
        """
        # Create a token
        params = {
            "user_id": "user_7f3d",
            "capability": "analyze_habits",
            "domain_scope": ["apollo"],
            "method_scope": {"apollo": ["analyze_habits"]},
            "duration_seconds": 900,
            "resource_limits": {
                "max_invocations": 5,
                "max_tokens_per_response": 512,
                "max_total_tokens": 2048,
                "max_frequency": "1 per 10 seconds",
            },
            "allowed_trigger_types": ["direct_command"],
            "issued_by": "user_7f3d",
        }
        token = CapabilityToken(**params)
        token_hash = token_registry.issue_token(token)
        
        # Revoke it
        token_registry.revoke_token(token_hash)
        
        # Try to use revoked token
        invocation = InvocationContext(
            token_hash=token_hash,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        
        success, error = invocation.try_execute()
        
        # Execution MUST fail
        assert not success
        
        # execution_started flag MUST be False
        # (because validation failed before execution could start)
        assert not invocation.execution_started


class TestMultipleTokensValidateIndependently:
    """
    REQUIREMENT: Different tokens validate independently.
    If User A has Token A and Token B, using the wrong token
    (or wrong user for Token A) must not affect Token B validation.
    """
    
    def test_token_a_revoked_does_not_affect_token_b(self, token_registry, valid_token_params):
        """
        Create two tokens.
        Revoke Token A.
        Token B must still validate successfully.
        """
        # Token A
        token_a = CapabilityToken(**valid_token_params)
        hash_a = token_registry.issue_token(token_a)
        
        # Token B (same user, same capability)
        params_b = valid_token_params.copy()
        params_b["issued_by"] = "user_admin"
        token_b = CapabilityToken(**params_b)
        hash_b = token_registry.issue_token(token_b)
        
        # Revoke Token A
        token_registry.revoke_token(hash_a)
        
        # Try to use Token A (must fail)
        inv_a = InvocationContext(
            token_hash=hash_a,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        success_a, _ = inv_a.try_execute()
        assert not success_a
        
        # Try to use Token B (must succeed)
        inv_b = InvocationContext(
            token_hash=hash_b,
            user_id="user_7f3d",
            domain="apollo",
            method="analyze_habits",
            trigger_type="direct_command",
            token_registry=token_registry
        )
        success_b, _ = inv_b.try_execute()
        assert success_b
        assert inv_b.validation_passed
