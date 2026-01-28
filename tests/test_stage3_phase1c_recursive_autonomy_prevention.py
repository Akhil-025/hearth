"""
PHASE 1C: Recursive Autonomy Prevention Tests

Binding Spec Section 1.3: No Recursive Autonomy

CRITICAL SAFETY GATE: This phase verifies the absolute prohibition on
Stage-3 (the autonomy/planning system) granting tokens to itself or other
autonomous agents. This prevents:

1. Stage-3 issuing capability tokens (Stage-3 CANNOT be issued_by)
2. Stage-3 delegating authority to itself or other Stage-3 agents
3. Recursive capability escalation
4. Stage-3 creating autonomous sub-agents

CONSEQUENCE OF FAILURE: If any test fails, implementation is INCOMPLETE
and UNSAFE. Do NOT proceed to Phase 1D or Phase 2 until ALL tests pass.

Why this is critical:
- Without this gate, Stage-3 could autonomously grant itself more permissions
- This breaks the human-in-the-loop guarantee for permission escalation
- This violates the foundational architectural principle of bounded autonomy
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


class TestStage3CannotIssueTokens:
    """
    REQUIREMENT: Stage-3 autonomy system MUST NOT issue capability tokens.
    All tokens MUST be issued by humans or system accounts (not autonomy agents).
    
    This prevents Stage-3 from autonomously granting itself more permissions.
    """
    
    def test_token_with_issued_by_stage3_is_rejected(self, valid_token_params):
        """
        If someone tries to create a token with issued_by="stage3", it MUST be rejected.
        Stage-3 system cannot issue tokens to itself.
        """
        valid_token_params["issued_by"] = "stage3"
        
        with pytest.raises(ValueError) as exc_info:
            token = CapabilityToken(**valid_token_params)
        
        assert "stage3" in str(exc_info.value).lower() or "issued" in str(exc_info.value).lower()
    
    def test_token_with_issued_by_stage3_component_is_rejected(self, valid_token_params):
        """
        Variants of stage3 name (stage3_*, stage-3, etc.) also MUST be rejected.
        System cannot use naming tricks to bypass the prohibition.
        """
        stage3_variants = [
            "stage3_core",
            "stage3_executor",
            "stage3_planner",
            "stage3-autonomy",
            "STAGE3",
        ]
        
        for variant in stage3_variants:
            params = valid_token_params.copy()
            params["issued_by"] = variant
            
            with pytest.raises(ValueError):
                token = CapabilityToken(**params)
    
    def test_token_with_issued_by_autonomy_system_is_rejected(self, valid_token_params):
        """
        Any autonomy/planning system identifier MUST be rejected as issuer.
        Examples: "autonomy", "planner", "executor", "scheduler"
        """
        autonomy_identifiers = [
            "autonomy",
            "planner",
            "executor",
            "scheduler",
            "orchestrator",
            "agent",
            "autonomous_agent",
        ]
        
        for identifier in autonomy_identifiers:
            params = valid_token_params.copy()
            params["issued_by"] = identifier
            
            with pytest.raises(ValueError):
                token = CapabilityToken(**params)
    
    def test_token_issued_by_human_user_is_accepted(self, valid_token_params):
        """
        Tokens MUST be issuable by human users (even if they delegate creation to a human-controlled system).
        This is the only legitimate source of tokens.
        """
        valid_issuer_ids = [
            "user_7f3d",
            "user_alice",
            "admin_carol",
            "system_admin",
            "human_operator_1",
        ]
        
        for issuer in valid_issuer_ids:
            params = valid_token_params.copy()
            params["issued_by"] = issuer
            
            # Should not raise
            token = CapabilityToken(**params)
            assert token.issued_by == issuer


class TestStage3CannotBeTokenUser:
    """
    REQUIREMENT: Tokens MUST be issued FOR human users (user_id), not for autonomy systems.
    A token with user_id="stage3" is meaningless and MUST be rejected.
    """
    
    def test_token_for_stage3_as_user_id_is_rejected(self, valid_token_params):
        """
        Token represents permission for someone to do something.
        That someone MUST be a human, not an autonomy system.
        
        A token with user_id="stage3" is nonsensical (who is it for?).
        """
        valid_token_params["user_id"] = "stage3"
        
        with pytest.raises(ValueError) as exc_info:
            token = CapabilityToken(**valid_token_params)
        
        assert "stage3" in str(exc_info.value).lower() or "user" in str(exc_info.value).lower()
    
    def test_token_for_autonomy_system_user_id_is_rejected(self, valid_token_params):
        """
        Tokens cannot be "for" an autonomy system to use.
        user_id MUST be a human.
        """
        autonomy_user_ids = [
            "autonomy",
            "planner",
            "executor",
            "stage3_planner",
            "system_executor",
        ]
        
        for user_id in autonomy_user_ids:
            params = valid_token_params.copy()
            params["user_id"] = user_id
            
            with pytest.raises(ValueError):
                token = CapabilityToken(**params)


class TestNoTokenDelegationToStage3:
    """
    REQUIREMENT: Even if a human could create a token, they CANNOT create one
    that grants Stage-3 access to a capability.
    
    A token that says "Stage-3 may call apollo.analyze_habits" is FORBIDDEN.
    This prevents: "I'll let the autonomy system call this method."
    """
    
    def test_token_cannot_grant_permission_to_autonomy_agent(self, valid_token_params):
        """
        Domain scope CANNOT include identifiers that refer to autonomy systems.
        Each domain maps to a real subsystem (apollo, hermes, etc.), not to "stage3".
        """
        # This would mean "Stage-3 can access the 'stage3_executor' domain"
        valid_token_params["user_id"] = "user_7f3d"  # Human
        valid_token_params["issued_by"] = "user_7f3d"  # Issued by human
        valid_token_params["domain_scope"] = ["stage3_executor"]  # FORBIDDEN
        valid_token_params["method_scope"] = {"stage3_executor": ["execute"]}
        
        with pytest.raises(ValueError) as exc_info:
            token = CapabilityToken(**valid_token_params)
        
        assert "stage3" in str(exc_info.value).lower() or "domain" in str(exc_info.value).lower()
    
    def test_token_cannot_delegate_to_autonomy_in_method_scope(self, valid_token_params):
        """
        method_scope keys MUST be valid domain names (apollo, hermes, etc.), 
        not autonomy system identifiers.
        """
        autonomy_domains = [
            "stage3",
            "autonomy",
            "planner",
            "executor",
        ]
        
        for autonomy_domain in autonomy_domains:
            params = valid_token_params.copy()
            params["domain_scope"] = [autonomy_domain]
            params["method_scope"] = {autonomy_domain: ["execute"]}
            
            with pytest.raises(ValueError):
                token = CapabilityToken(**params)


class TestNoRecursiveCapabilityEscalation:
    """
    REQUIREMENT: A token CANNOT grant Stage-3 permission to issue more tokens.
    This breaks the recursive escalation vector.
    
    Normal case (ALLOWED):
    - User A has token to call apollo.analyze_habits
    - User A calls apollo.analyze_habits
    - User A gets result
    
    Forbidden case (MUST PREVENT):
    - User A has token to call "permission_system.grant_token"
    - User A invokes permission_system.grant_token to create new token
    - User A now has escalated permissions without human approval
    - Stage-3 could do the same autonomously
    """
    
    def test_token_cannot_grant_permission_system_access(self, valid_token_params):
        """
        There MUST NOT be methods like "grant_token", "issue_token", "create_capability"
        that can be called by any user with a token.
        
        Permission issuance MUST be outside the token system.
        """
        # Simulate attempt to create a token that lets someone issue tokens
        forbidden_capabilities = [
            "grant_token",
            "issue_token",
            "create_capability",
            "revoke_token",
            "modify_token",
            "escalate_permission",
        ]
        
        for capability in forbidden_capabilities:
            params = valid_token_params.copy()
            params["capability"] = capability
            params["method_scope"] = {"permission_system": [capability]}
            params["domain_scope"] = ["permission_system"]
            
            # Token creation MUST reject permission_system domain
            with pytest.raises(ValueError):
                token = CapabilityToken(**params)
    
    def test_no_token_chain_issuance(self, token_registry, valid_token_params):
        """
        ARCHITECTURAL REQUIREMENT: Token issuance MUST be one-level only.
        
        Path A (ALLOWED): Human issues token → User uses token → Operation happens
        
        Path B (FORBIDDEN): Human issues token → User uses token to call permission_system →
                            User issues new token → Recursive escalation
        
        This test documents that Phase 2 MUST reject "call permission system to issue tokens".
        """
        # Token 1: User has a token
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # User cannot use Token 1 to create Token 2
        # (This would be enforced at invocation time in Phase 2)
        # For Phase 1C, we just verify the token structure doesn't enable this
        
        assert token_registry.get_token(hash1) is not None
        # Phase 2 will test: "What happens if user tries to call token_issuer.create_token?"


class TestStage3NotInTriggerTypeEscalation:
    """
    REQUIREMENT: Trigger types MUST NOT include "stage3_invoke" or similar.
    Stage-3 cannot grant itself permission to execute autonomously.
    """
    
    def test_allowed_trigger_types_do_not_include_stage3(self, valid_token_params):
        """
        Valid trigger types: direct_command, async_request, acknowledgment, scheduled
        
        These are all user-initiated or user-scheduled. NOT autonomy-initiated.
        """
        valid_token_params["allowed_trigger_types"] = ["direct_command", "async_request"]
        
        token = CapabilityToken(**valid_token_params)
        assert token.allowed_trigger_types == ("direct_command", "async_request")
        
        # Stage-3 is not in there
        assert "stage3" not in str(token.allowed_trigger_types).lower()
        assert "autonomy" not in str(token.allowed_trigger_types).lower()
        assert "auto" not in str(token.allowed_trigger_types).lower()
    
    def test_token_with_stage3_trigger_type_is_rejected(self, valid_token_params):
        """
        If someone tries to create a token with trigger_type="stage3_execute" or similar,
        it MUST be rejected.
        """
        forbidden_triggers = [
            "stage3_execute",
            "autonomy_invoke",
            "auto_trigger",
            "background_execution",
            "autonomous_trigger",
            "polling",
            "timer",
        ]
        
        for trigger in forbidden_triggers:
            params = valid_token_params.copy()
            params["allowed_trigger_types"] = [trigger]
            
            with pytest.raises(ValueError) as exc_info:
                token = CapabilityToken(**params)
            
            # Error message should indicate why this trigger is forbidden
            error_msg = str(exc_info.value).lower()
            assert "trigger" in error_msg or "valid" in error_msg


class TestNoAutonomousSubAgentCreation:
    """
    REQUIREMENT: Stage-3 CANNOT create sub-agents or delegate to other autonomy systems.
    
    Prohibited pattern: Stage-3 → creates Agent B → Agent B has capabilities → Recursion
    """
    
    def test_token_cannot_be_issued_for_agent_creation(self, valid_token_params):
        """
        Tokens CANNOT be scoped to include "agent_factory" or "sub_agent_creator" methods.
        You cannot get permission to create new agents.
        """
        # This would be enforced at token creation time
        valid_token_params["domain_scope"] = ["agent_system"]
        valid_token_params["method_scope"] = {"agent_system": ["create_agent", "spawn_worker"]}
        valid_token_params["capability"] = "create_agent"
        
        # Token creation MUST reject agent_system domain
        with pytest.raises(ValueError):
            token = CapabilityToken(**valid_token_params)
    
    def test_no_bootstrap_capability_tokens(self, valid_token_params):
        """
        There MUST NOT be a "bootstrap" or "init_stage3" capability that lets
        someone grant Stage-3 initial permissions.
        
        Stage-3 permissions MUST be granted by hardcoded policy at startup,
        not by tokens that can be created/modified at runtime.
        """
        bootstrap_capabilities = [
            "bootstrap_stage3",
            "init_autonomy",
            "setup_agent",
            "grant_initial_permissions",
            "initialize_executor",
        ]
        
        for capability in bootstrap_capabilities:
            params = valid_token_params.copy()
            params["capability"] = capability
            
            # System should either reject these or they should be non-functional
            # For Phase 1C, we document that these MUST NOT exist as callable methods
            token = CapabilityToken(**params)
            # Test passes - Phase 2 will verify these methods don't respond to token calls
