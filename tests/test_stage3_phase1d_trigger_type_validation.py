"""
PHASE 1D: Trigger Type Validation Tests

Binding Spec Section 1.4: Execution Trigger Types

REQUIREMENT: Capability tokens MUST explicitly specify which trigger types
authorize execution. Only four trigger types exist:

1. direct_command: User directly invokes operation (synchronous request)
2. async_request: User requests asynchronous execution (user waits for result)
3. acknowledgment: System acknowledges a user action then executes
4. scheduled: User-scheduled operation (user specifies exact time)

FORBIDDEN TRIGGERS:
- background_execution: No automatic execution without user awareness
- polling: No proactive checking of conditions
- timer: No periodic execution
- stage3_invoke: No autonomy-system-initiated execution
- autonomous_trigger: No self-executing operations

REQUIREMENT: If token does not authorize a particular trigger type,
that trigger MUST NOT execute the operation (verified in Phase 2).

These tests verify trigger type structure and constraints.
Execution authorization (Phase 2) tests verify that triggers are actually enforced.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
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


class TestValidTriggerTypes:
    """
    REQUIREMENT: Tokens MUST explicitly specify which trigger types are allowed.
    Only four valid trigger types exist.
    """
    
    def test_direct_command_is_valid_trigger(self, valid_token_params):
        """direct_command: User directly invokes operation (synchronous)."""
        valid_token_params["allowed_trigger_types"] = ["direct_command"]
        
        token = CapabilityToken(**valid_token_params)
        assert "direct_command" in token.allowed_trigger_types
    
    def test_async_request_is_valid_trigger(self, valid_token_params):
        """async_request: User requests async execution."""
        valid_token_params["allowed_trigger_types"] = ["async_request"]
        
        token = CapabilityToken(**valid_token_params)
        assert "async_request" in token.allowed_trigger_types
    
    def test_acknowledgment_is_valid_trigger(self, valid_token_params):
        """acknowledgment: System acknowledges user action then executes."""
        valid_token_params["allowed_trigger_types"] = ["acknowledgment"]
        
        token = CapabilityToken(**valid_token_params)
        assert "acknowledgment" in token.allowed_trigger_types
    
    def test_scheduled_is_valid_trigger(self, valid_token_params):
        """scheduled: User-scheduled operation."""
        valid_token_params["allowed_trigger_types"] = ["scheduled"]
        
        token = CapabilityToken(**valid_token_params)
        assert "scheduled" in token.allowed_trigger_types
    
    def test_multiple_valid_trigger_types(self, valid_token_params):
        """Token can authorize multiple trigger types."""
        valid_token_params["allowed_trigger_types"] = [
            "direct_command",
            "async_request",
            "scheduled"
        ]
        
        token = CapabilityToken(**valid_token_params)
        assert "direct_command" in token.allowed_trigger_types
        assert "async_request" in token.allowed_trigger_types
        assert "scheduled" in token.allowed_trigger_types
    
    def test_all_four_trigger_types(self, valid_token_params):
        """Token can authorize all four trigger types."""
        valid_token_params["allowed_trigger_types"] = [
            "direct_command",
            "async_request",
            "acknowledgment",
            "scheduled"
        ]
        
        token = CapabilityToken(**valid_token_params)
        assert len(token.allowed_trigger_types) == 4


class TestForbiddenTriggerTypes:
    """
    REQUIREMENT: Autonomy-initiated or background-execution triggers MUST be rejected.
    No automatic, background, or self-triggered execution.
    """
    
    def test_background_execution_is_rejected(self, valid_token_params):
        """background_execution is forbidden."""
        valid_token_params["allowed_trigger_types"] = ["background_execution"]
        
        with pytest.raises(ValueError) as exc_info:
            token = CapabilityToken(**valid_token_params)
        
        assert "invalid" in str(exc_info.value).lower() or "trigger" in str(exc_info.value).lower()
    
    def test_polling_is_rejected(self, valid_token_params):
        """polling is forbidden (proactive condition checking)."""
        valid_token_params["allowed_trigger_types"] = ["polling"]
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_timer_is_rejected(self, valid_token_params):
        """timer is forbidden (periodic execution)."""
        valid_token_params["allowed_trigger_types"] = ["timer"]
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_periodic_is_rejected(self, valid_token_params):
        """periodic is forbidden (variant of timer)."""
        valid_token_params["allowed_trigger_types"] = ["periodic"]
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_stage3_invoke_is_rejected(self, valid_token_params):
        """stage3_invoke is forbidden (autonomy-initiated)."""
        valid_token_params["allowed_trigger_types"] = ["stage3_invoke"]
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_autonomous_trigger_is_rejected(self, valid_token_params):
        """autonomous_trigger is forbidden."""
        valid_token_params["allowed_trigger_types"] = ["autonomous_trigger"]
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_auto_execute_is_rejected(self, valid_token_params):
        """auto_execute is forbidden."""
        valid_token_params["allowed_trigger_types"] = ["auto_execute"]
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_webhook_is_rejected(self, valid_token_params):
        """webhook triggers should be rejected (external automatic triggering)."""
        valid_token_params["allowed_trigger_types"] = ["webhook"]
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_event_driven_is_rejected(self, valid_token_params):
        """event_driven triggers are rejected (automatic on condition)."""
        valid_token_params["allowed_trigger_types"] = ["event_driven"]
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)


class TestTriggerTypesMustBeExplicit:
    """
    REQUIREMENT: Trigger types MUST be explicitly specified.
    No defaults, no inference, no wildcards.
    """
    
    def test_empty_trigger_types_is_rejected(self, valid_token_params):
        """Cannot create token with no trigger types."""
        valid_token_params["allowed_trigger_types"] = []
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_none_trigger_types_is_rejected(self, valid_token_params):
        """Cannot create token with trigger_types=None."""
        valid_token_params["allowed_trigger_types"] = None
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_trigger_types_must_be_list(self, valid_token_params):
        """Trigger types must be list (not string, not dict)."""
        valid_token_params["allowed_trigger_types"] = "direct_command"
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_trigger_types_wildcard_is_rejected(self, valid_token_params):
        """Cannot use "*" to mean "all trigger types"."""
        valid_token_params["allowed_trigger_types"] = ["*"]
        
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)


class TestNoBackgroundExecution:
    """
    REQUIREMENT: Tokens MUST NOT authorize background execution.
    All triggers must involve explicit user awareness/control.
    """
    
    def test_no_background_trigger_variants(self, valid_token_params):
        """Reject all background execution variants."""
        background_variants = [
            "background",
            "background_execution",
            "background_job",
            "background_task",
            "daemon",
            "daemon_execution",
            "cron",
            "cron_job",
        ]
        
        for trigger in background_variants:
            params = valid_token_params.copy()
            params["allowed_trigger_types"] = [trigger]
            
            with pytest.raises(ValueError):
                token = CapabilityToken(**params)
    
    def test_token_cannot_enable_unaware_execution(self, token_registry, valid_token_params):
        """
        Even if token is created, system must verify user is aware of execution.
        This is tested in Phase 2 (invocation tests).
        
        For Phase 1D, we verify token structure includes explicit trigger awareness.
        """
        valid_token_params["allowed_trigger_types"] = ["direct_command"]
        
        token = CapabilityToken(**valid_token_params)
        
        # Token explicitly lists triggers
        assert token.allowed_trigger_types is not None
        assert len(token.allowed_trigger_types) > 0
        
        # User must explicitly request using one of these triggers
        # (Phase 2 will test execution rejects undefined triggers)


class TestNoPollingOrTimers:
    """
    REQUIREMENT: Tokens MUST NOT authorize polling or timer-based execution.
    These enable proactive, condition-based autonomous action.
    """
    
    def test_polling_variants_are_rejected(self, valid_token_params):
        """Reject all polling variants."""
        polling_variants = [
            "polling",
            "poll",
            "poll_condition",
            "condition_check",
            "monitor",
            "watch",
            "background_monitor",
        ]
        
        for trigger in polling_variants:
            params = valid_token_params.copy()
            params["allowed_trigger_types"] = [trigger]
            
            with pytest.raises(ValueError):
                token = CapabilityToken(**params)
    
    def test_timer_variants_are_rejected(self, valid_token_params):
        """Reject all timer variants."""
        timer_variants = [
            "timer",
            "timeout",
            "delay",
            "periodic",
            "recurring",
            "interval",
            "repeat",
            "cron",
        ]
        
        for trigger in timer_variants:
            params = valid_token_params.copy()
            params["allowed_trigger_types"] = [trigger]
            
            with pytest.raises(ValueError):
                token = CapabilityToken(**params)


class TestScheduledMustBeExplicit:
    """
    REQUIREMENT: "scheduled" trigger type is allowed, but the schedule itself
    must be managed outside the token system (user specifies when to run).
    
    NOT allowed: "scheduled" meaning "system decides when to run".
    """
    
    def test_scheduled_trigger_is_allowed(self, valid_token_params):
        """scheduled is an allowed trigger type."""
        valid_token_params["allowed_trigger_types"] = ["scheduled"]
        
        token = CapabilityToken(**valid_token_params)
        assert "scheduled" in token.allowed_trigger_types
    
    def test_scheduled_does_not_imply_automatic_execution(self, valid_token_params):
        """
        "scheduled" means user explicitly scheduled it, not system auto-runs it.
        This is enforced in Phase 2 (invocation must include schedule details).
        
        For Phase 1D, we document the requirement.
        """
        valid_token_params["allowed_trigger_types"] = ["scheduled"]
        
        token = CapabilityToken(**valid_token_params)
        
        # Phase 2 will test: When executing with "scheduled" trigger,
        # user must provide schedule details (time, repeat pattern, etc.)
        # System cannot invent a schedule


class TestTriggerTypeEnforcement:
    """
    REQUIREMENT: If token does not authorize a trigger type, that trigger
    MUST NOT execute the operation.
    
    Tests here verify token structure.
    Phase 2 tests verify execution actually enforces trigger types.
    """
    
    def test_token_with_only_direct_command_cannot_use_scheduled(self, token_registry, valid_token_params):
        """
        Token 1: Can only use direct_command
        System tries to execute using scheduled trigger
        MUST BE REJECTED
        
        (This test documents the requirement; Phase 2 enforces it)
        """
        valid_token_params["allowed_trigger_types"] = ["direct_command"]
        
        token = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token)
        
        # Phase 2 test: Try to invoke with trigger="scheduled"
        # System must reject: "Token does not authorize 'scheduled' trigger"
        retrieved_token = token_registry.get_token(hash1)
        assert "scheduled" not in retrieved_token.allowed_trigger_types
    
    def test_different_tokens_can_have_different_triggers(self, token_registry, valid_token_params):
        """
        User can have different tokens with different authorized triggers.
        Token 1: Can use direct_command
        Token 2: Can use scheduled
        
        Each token enforces its own trigger types.
        """
        # Token 1: only direct_command
        params1 = valid_token_params.copy()
        params1["allowed_trigger_types"] = ["direct_command"]
        params1["issued_by"] = "user_7f3d"
        token1 = CapabilityToken(**params1)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: only scheduled
        params2 = valid_token_params.copy()
        params2["allowed_trigger_types"] = ["scheduled"]
        params2["issued_by"] = "user_admin"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Triggers are independent
        token1_retrieved = token_registry.get_token(hash1)
        token2_retrieved = token_registry.get_token(hash2)
        
        assert "direct_command" in token1_retrieved.allowed_trigger_types
        assert "scheduled" not in token1_retrieved.allowed_trigger_types
        
        assert "scheduled" in token2_retrieved.allowed_trigger_types
        assert "direct_command" not in token2_retrieved.allowed_trigger_types
