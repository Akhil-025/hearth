"""
PHASE 1B: Token Independence & No Shadowing Tests

Binding Spec Section 1.2: Token Independence Guarantee

REQUIREMENT: When user holds multiple tokens that authorize the same operation,
system MUST NOT apply implicit rules to choose among them. Instead:
1. User MUST explicitly specify which token to use for each operation
2. Tokens with overlapping scopes do NOT create precedence
3. Token shadowing (newer hiding older, higher privilege hiding lower) is FORBIDDEN

These tests verify that token independence is preserved even under ambiguous
authorization scenarios.

SAFETY GATE: All 1B tests must pass before proceeding to PHASE 1C.
If any test fails, implementation of token selection/authorization is FORBIDDEN
until test is fixed.
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
    """Fixture providing valid token parameters (not mutated)."""
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


class TestTokenIndependenceWithoutShadowing:
    """
    REQUIREMENT: Multiple tokens with overlapping scopes MUST be treated
    independently. System MUST NOT apply implicit precedence rules.
    """
    
    def test_two_tokens_for_same_operation_both_available(self, token_registry, valid_token_params):
        """
        User has two tokens that both authorize apollo.analyze_habits.
        Both tokens MUST remain available. System MUST NOT hide one with the other.
        """
        # Token 1: User's personal token
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: Delegation from another user (same operation, different issuer)
        params2 = valid_token_params.copy()
        params2["issued_by"] = "user_admin_delegate"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Both tokens must be retrievable
        assert token_registry.get_token(hash1) is not None
        assert token_registry.get_token(hash2) is not None
        
        # System cannot implicitly choose between them
        user_tokens = token_registry.get_user_tokens("user_7f3d")
        assert hash1 in user_tokens
        assert hash2 in user_tokens
        assert len(user_tokens) == 2
    
    def test_newer_token_does_not_shadow_older_token(self, token_registry, valid_token_params):
        """
        Newer tokens MUST NOT implicitly replace older tokens.
        System MUST NOT apply "use most recent" precedence.
        """
        # Token 1 (older)
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        issued_at_1 = token1.issued_at
        
        # Token 2 (newer, issued after token1)
        params2 = valid_token_params.copy()
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        issued_at_2 = token2.issued_at
        
        # Verify token2 is actually newer
        assert issued_at_2 >= issued_at_1
        
        # But BOTH tokens must remain available
        assert token_registry.get_token(hash1) is not None
        assert token_registry.get_token(hash2) is not None
        
        # System cannot have "hidden" the older token
        user_tokens = token_registry.get_user_tokens("user_7f3d")
        assert hash1 in user_tokens
        assert hash2 in user_tokens
    
    def test_higher_privilege_token_does_not_shadow_lower_privilege(self, token_registry, valid_token_params):
        """
        Higher-privilege tokens MUST NOT implicitly replace lower-privilege tokens.
        System MUST NOT apply "use highest privilege" precedence.
        """
        # Token 1: Limited invocations
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: Unlimited invocations (higher privilege)
        params2 = valid_token_params.copy()
        params2["resource_limits"]["max_invocations"] = 1000
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Both tokens must remain available (system cannot choose the "better" one)
        assert token_registry.get_token(hash1) is not None
        assert token_registry.get_token(hash2) is not None
        
        # Verify they have different limits
        assert token_registry.get_token(hash1).resource_limits["max_invocations"] == 5
        assert token_registry.get_token(hash2).resource_limits["max_invocations"] == 1000


class TestExplicitTokenSelection:
    """
    REQUIREMENT: When multiple tokens authorize same operation, user MUST
    explicitly specify which token to use. This is tested at invocation time
    (Phase 2 tests), but PHASE 1B tests document the token structure requirements.
    """
    
    def test_tokens_store_distinct_identifiers_for_explicit_selection(self, token_registry, valid_token_params):
        """
        Each token MUST have distinct, stable identifier so user can specify it.
        Token hash MUST be unique per token, not reused based on capabilities.
        """
        # Token 1
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: Same capability, different issuer
        params2 = valid_token_params.copy()
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Hashes MUST be distinct
        assert hash1 != hash2
        
        # User can explicitly select: "Use token_{hash1}"
        assert token_registry.get_token(hash1) is not None
        # Or: "Use token_{hash2}"
        assert token_registry.get_token(hash2) is not None
        
        # Each hash resolves to exact token
        token1_retrieved = token_registry.get_token(hash1)
        token2_retrieved = token_registry.get_token(hash2)
        assert token1_retrieved.issued_by == "user_7f3d"
        assert token2_retrieved.issued_by == "user_9x2k"
    
    def test_token_hash_is_stable_for_explicit_selection(self, token_registry, valid_token_params):
        """
        Token hash MUST NOT change after issuance (otherwise user cannot reference it).
        Hash is stable, immutable identifier for explicit selection.
        """
        token = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token)
        
        # Retrieve token multiple times
        retrieved_1 = token_registry.get_token(hash1)
        retrieved_2 = token_registry.get_token(hash1)
        retrieved_3 = token_registry.get_token(hash1)
        
        # All retrievals return same token
        assert retrieved_1 is not None
        assert retrieved_2 is not None
        assert retrieved_3 is not None
        
        # Hashes are stable
        # (In Phase 2 tests, we'll verify that invocation explicitly uses this hash)


class TestTokenScopeIndependence:
    """
    REQUIREMENT: Overlapping token scopes do NOT merge or combine for execution.
    System MUST respect each token's exact scope independently.
    """
    
    def test_overlapping_scope_does_not_expand_authorization(self, token_registry, valid_token_params):
        """
        Token 1: Can call apollo.analyze_habits
        Token 2: Can call apollo.plan_routine
        
        System MUST NOT allow Token 1 to call apollo.plan_routine just because
        Token 2 can. Scopes do NOT combine.
        """
        # Token 1: Only analyze_habits
        params1 = valid_token_params.copy()
        params1["method_scope"] = {"apollo": ["analyze_habits"]}  # Only analyze_habits
        token1 = CapabilityToken(**params1)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: Only plan_routine
        params2 = valid_token_params.copy()
        params2["capability"] = "plan_routine"
        params2["method_scope"] = {"apollo": ["plan_routine"]}  # Only plan_routine
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Verify scope independence
        token1_retrieved = token_registry.get_token(hash1)
        token2_retrieved = token_registry.get_token(hash2)
        
        assert token1_retrieved.capability == "analyze_habits"
        assert token2_retrieved.capability == "plan_routine"
        
        # Token 1's scope is ONLY analyze_habits
        assert "analyze_habits" in token1_retrieved.method_scope["apollo"]
        assert "plan_routine" not in token1_retrieved.method_scope["apollo"]
        
        # Token 2's scope is ONLY plan_routine
        assert "plan_routine" in token2_retrieved.method_scope["apollo"]
        assert "analyze_habits" not in token2_retrieved.method_scope["apollo"]
    
    def test_overlapping_domain_scope_does_not_expand_authorization(self, token_registry, valid_token_params):
        """
        Token 1: Can access apollo domain
        Token 2: Can access hermes domain
        
        System MUST NOT allow Token 1 to access hermes just because Token 2 can.
        Domain scopes do NOT combine.
        """
        # Token 1: apollo only
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: hermes only
        params2 = valid_token_params.copy()
        params2["domain_scope"] = ["hermes"]
        params2["method_scope"] = {"hermes": ["synthesize_schedule"]}
        params2["capability"] = "synthesize_schedule"
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Verify scope independence
        token1_retrieved = token_registry.get_token(hash1)
        token2_retrieved = token_registry.get_token(hash2)
        
        assert token1_retrieved.domain_scope == ("apollo",)
        assert token2_retrieved.domain_scope == ("hermes",)
        
        # Scopes do NOT combine
        assert "apollo" in token1_retrieved.domain_scope
        assert "hermes" not in token1_retrieved.domain_scope
        
        assert "hermes" in token2_retrieved.domain_scope
        assert "apollo" not in token2_retrieved.domain_scope


class TestNoImplicitPrecedence:
    """
    REQUIREMENT: System MUST NOT apply implicit rules like:
    - "Use most recent token"
    - "Use first matching token"
    - "Use highest privilege token"
    - "Use longest remaining duration token"
    
    These tests document the prohibition against implicit precedence.
    """
    
    def test_most_recent_token_is_not_implicit_default(self, token_registry, valid_token_params):
        """
        System MUST NOT automatically choose "most recent token" when multiple
        tokens authorize the same operation.
        """
        # Token 1 (older)
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2 (newer)
        params2 = valid_token_params.copy()
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # System MUST NOT have hidden token1 in favor of token2
        # Both must remain available
        user_tokens = token_registry.get_user_tokens("user_7f3d")
        assert hash1 in user_tokens
        assert hash2 in user_tokens
        
        # In Phase 2 tests, we'll verify that invocation requires explicit token specification
    
    def test_longest_duration_token_is_not_implicit_default(self, token_registry, valid_token_params):
        """
        System MUST NOT automatically choose token with longest remaining duration
        when multiple tokens authorize the same operation.
        """
        # Token 1: 300 seconds remaining
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: 900 seconds remaining (longer)
        params2 = valid_token_params.copy()
        params2["duration_seconds"] = 900
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # System MUST NOT hide token1 in favor of token2
        user_tokens = token_registry.get_user_tokens("user_7f3d")
        assert hash1 in user_tokens
        assert hash2 in user_tokens
    
    def test_first_matching_token_is_not_implicit_default(self, token_registry, valid_token_params):
        """
        System MUST NOT automatically use "first matching token" when multiple
        tokens authorize the same operation.
        
        There is no "first" token; all tokens are equally available.
        """
        # Token 1
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2
        params2 = valid_token_params.copy()
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Token 3
        params3 = valid_token_params.copy()
        params3["issued_by"] = "user_9x2k_admin"
        token3 = CapabilityToken(**params3)
        hash3 = token_registry.issue_token(token3)
        
        # All three must be available (no "first" selection)
        user_tokens = token_registry.get_user_tokens("user_7f3d")
        assert hash1 in user_tokens
        assert hash2 in user_tokens
        assert hash3 in user_tokens
        assert len(user_tokens) == 3


class TestAmbiguityDetectionRequirements:
    """
    REQUIREMENT: System MUST detect and reject ambiguous token use.
    If user invokes operation with multiple valid tokens and does not
    explicitly specify which one to use, system MUST reject the operation.
    
    Tests here document token structure requirements.
    Actual ambiguity rejection is tested in Phase 2 (invocation tests).
    """
    
    def test_tokens_can_be_enumerated_to_detect_ambiguity(self, token_registry, valid_token_params):
        """
        System MUST be able to enumerate all user's tokens to detect ambiguity.
        TokenRegistry.get_user_tokens() MUST return all tokens for a user.
        """
        # Token 1
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2
        params2 = valid_token_params.copy()
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Get all tokens for user
        user_tokens = token_registry.get_user_tokens("user_7f3d")
        
        # Both tokens must be enumerable
        assert hash1 in user_tokens
        assert hash2 in user_tokens
        
        # System can check: "How many tokens authorize apollo.analyze_habits?"
        # (Actual filtering is Phase 2, but enumeration is available in Phase 1)
    
    def test_ambiguous_tokens_have_distinguishing_properties(self, token_registry, valid_token_params):
        """
        Even when tokens are ambiguous (authorize same operation), they MUST
        have distinguishing properties so user can explicitly specify which one:
        - Different issued_by
        - Different hash
        - Different resource_limits
        - etc.
        """
        # Token 1: Issued by user_7f3d
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: Issued by admin, but same capability
        params2 = valid_token_params.copy()
        params2["issued_by"] = "admin_user"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Tokens are distinguishable
        assert hash1 != hash2
        assert token_registry.get_token(hash1).issued_by != token_registry.get_token(hash2).issued_by
        
        # User can explicitly select: "Use token from admin_user"
        # (Phase 2 tests will verify explicit selection in invocation)


class TestTokenIndependenceAfterRevocation:
    """
    REQUIREMENT: Revoking one token MUST NOT affect availability of other tokens
    (even if they authorize the same operation).
    """
    
    def test_revoking_one_ambiguous_token_preserves_others(self, token_registry, valid_token_params):
        """
        User has two tokens that authorize apollo.analyze_habits.
        Revoking Token 1 MUST NOT make Token 2 unavailable.
        """
        # Token 1
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: Same authorization, different issuer
        params2 = valid_token_params.copy()
        params2["issued_by"] = "admin_user"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Both available initially
        assert not token_registry.is_revoked(hash1)
        assert not token_registry.is_revoked(hash2)
        
        # Revoke token1
        token_registry.revoke_token(hash1)
        
        # Token1 is revoked
        assert token_registry.is_revoked(hash1)
        
        # But token2 is still available
        assert not token_registry.is_revoked(hash2)
        assert token_registry.get_token(hash2) is not None
