"""
PHASE 2B: Domain & Method Scope Enforcement Tests

Binding Spec Section 2.2: Scope Authorization

REQUIREMENT: Tokens authorize operations by explicit enumerated scope.

STRUCTURE:
  - domain_scope: ["apollo", "hermes"] — EXPLICIT list of allowed domains
  - method_scope: {
      "apollo": ["analyze_habits", "plan_routine"],
      "hermes": ["synthesize_schedule"]
    } — EXPLICIT per-domain methods

ENFORCEMENT RULES:
1. Domain MUST be in domain_scope or invocation is rejected
2. Method MUST be in method_scope[domain] or invocation is rejected
3. No wildcard/regex/prefix matching allowed
4. No inference from capability name
5. No fallback to another domain or method
6. Errors MUST identify what was denied (domain, method, or both)

ARCHITECTURE:
    Invocation Request
         ↓
    [VALIDATION PHASE] ← Phase 2A (already tested)
         ↓
    [AUTHORIZATION PHASE] ← Phase 2B tests here
         ├─ Domain in domain_scope?
         ├─ Domain exists in method_scope?
         ├─ Method in method_scope[domain]?
         └─ Fail → REJECT (no execution)
         ↓
    [EXECUTION PHASE] ← Phase 2C+
         └─ Call domain

FAIL-CLOSED: If domain or method not explicitly authorized, reject immediately.

ADVERSARIAL TESTS verify that similar/partial/inferred scopes are REJECTED:
  - "apollonian" when "apollo" allowed → REJECT
  - "apollo" when "apollonian" allowed → REJECT
  - Prefix matching "apol*" → REJECT
  - Case insensitivity "APOLLO" when "apollo" allowed → REJECT
  - Method inference from capability name → REJECT
  - Regex pattern matching → REJECT
  - Wildcard expansion → REJECT
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
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


class ScopeAuthorizationContext:
    """
    Represents authorization check after token validation.
    Tests scope authorization: domain and method must be in token's scope.
    """
    
    def __init__(self, token: CapabilityToken, invocation_domain: str, 
                 invocation_method: str):
        self.token = token
        self.invocation_domain = invocation_domain
        self.invocation_method = invocation_method
        
        # Authorization state
        self.authorization_passed = False
        self.authorization_failure_reason: Optional[str] = None
        self.domain_authorized = False
        self.method_authorized = False
    
    def authorize_scope(self) -> bool:
        """
        PHASE 2B: Check if invocation is authorized by token scope.
        Returns True if both domain and method are authorized.
        
        FAIL-CLOSED: If any check fails, return False immediately.
        """
        # Check 1: Domain must be in domain_scope
        if self.invocation_domain not in self.token.domain_scope:
            self.authorization_failure_reason = (
                f"Domain '{self.invocation_domain}' not authorized. "
                f"Token allows: {list(self.token.domain_scope)}"
            )
            return False
        
        self.domain_authorized = True
        
        # Check 2: Domain must exist in method_scope
        if self.invocation_domain not in self.token.method_scope:
            self.authorization_failure_reason = (
                f"Domain '{self.invocation_domain}' has no methods in token scope"
            )
            return False
        
        # Check 3: Method must be in method_scope[domain]
        allowed_methods = self.token.method_scope[self.invocation_domain]
        if self.invocation_method not in allowed_methods:
            self.authorization_failure_reason = (
                f"Method '{self.invocation_method}' not authorized for domain '{self.invocation_domain}'. "
                f"Token allows: {list(allowed_methods)}"
            )
            return False
        
        self.method_authorized = True
        self.authorization_passed = True
        return True


class TestDomainScopeMustBeExplicitEnumerated:
    """
    REQUIREMENT: Domain scope is an explicit enumerated list.
    A domain is authorized IFF it appears in domain_scope.
    No wildcards, regex, or prefix matching.
    """
    
    def test_domain_in_scope_authorizes_invocation(self, valid_token_params):
        """
        Token authorizes domain "apollo".
        Invocation requests domain "apollo".
        Authorization must pass.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="analyze_habits"
        )
        
        result = auth.authorize_scope()
        
        assert result
        assert auth.authorization_passed
        assert auth.domain_authorized
    
    def test_domain_not_in_scope_rejects_invocation(self, valid_token_params):
        """
        Token authorizes domain "apollo".
        Invocation requests domain "hermes".
        Authorization must fail with clear error.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="hermes",
            invocation_method="synthesize_schedule"
        )
        
        result = auth.authorize_scope()
        
        assert not result
        assert not auth.authorization_passed
        assert auth.authorization_failure_reason is not None
        assert "hermes" in auth.authorization_failure_reason.lower()
        assert "not authorized" in auth.authorization_failure_reason.lower()
    
    def test_multiple_domains_in_scope(self, valid_token_params):
        """
        Token authorizes multiple domains: ["apollo", "hermes", "hephaestus"].
        Each domain in scope must authorize invocation.
        Domain not in scope must reject.
        """
        params = valid_token_params.copy()
        params["domain_scope"] = ["apollo", "hermes", "hephaestus"]
        params["method_scope"] = {
            "apollo": ["analyze_habits"],
            "hermes": ["synthesize_schedule"],
            "hephaestus": ["design_system"]
        }
        
        token = CapabilityToken(**params)
        
        # Each authorized domain passes
        for domain in ["apollo", "hermes", "hephaestus"]:
            auth = ScopeAuthorizationContext(
                token=token,
                invocation_domain=domain,
                invocation_method=params["method_scope"][domain][0]
            )
            assert auth.authorize_scope()
        
        # Unauthorized domain fails
        auth_fail = ScopeAuthorizationContext(
            token=token,
            invocation_domain="dionysus",
            invocation_method="analyze_creativity"
        )
        assert not auth_fail.authorize_scope()


class TestMethodScopeMustBeExplicitPerDomain:
    """
    REQUIREMENT: Method scope is domain-specific enumerated list.
    A method is authorized IFF it appears in method_scope[domain].
    No cross-domain fallback. No inference from capability.
    """
    
    def test_method_in_scope_authorizes_invocation(self, valid_token_params):
        """
        Token authorizes method "analyze_habits" in domain "apollo".
        Invocation requests method "analyze_habits" in domain "apollo".
        Authorization must pass.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="analyze_habits"
        )
        
        result = auth.authorize_scope()
        
        assert result
        assert auth.method_authorized
    
    def test_method_not_in_scope_rejects_invocation(self, valid_token_params):
        """
        Token authorizes "analyze_habits" and "plan_routine" in "apollo".
        Invocation requests "schedule_workout" in "apollo".
        Authorization must fail with clear error identifying method.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="schedule_workout"
        )
        
        result = auth.authorize_scope()
        
        assert not result
        assert not auth.method_authorized
        assert auth.authorization_failure_reason is not None
        assert "schedule_workout" in auth.authorization_failure_reason
        assert "not authorized" in auth.authorization_failure_reason.lower()
    
    def test_multiple_methods_per_domain(self, valid_token_params):
        """
        Token authorizes multiple methods per domain.
        Each authorized method passes.
        Unauthorized method fails.
        """
        params = valid_token_params.copy()
        params["method_scope"] = {
            "apollo": ["analyze_habits", "plan_routine", "predict_patterns"]
        }
        
        token = CapabilityToken(**params)
        
        # Each authorized method passes
        for method in ["analyze_habits", "plan_routine", "predict_patterns"]:
            auth = ScopeAuthorizationContext(
                token=token,
                invocation_domain="apollo",
                invocation_method=method
            )
            assert auth.authorize_scope()
        
        # Unauthorized method fails
        auth_fail = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="forbidden_method"
        )
        assert not auth_fail.authorize_scope()
    
    def test_method_scope_is_per_domain(self, valid_token_params):
        """
        Token authorizes method "analyze_habits" in "apollo".
        Same method name in different domain is NOT automatically authorized.
        """
        params = valid_token_params.copy()
        params["domain_scope"] = ["apollo", "hermes"]
        params["method_scope"] = {
            "apollo": ["analyze_habits"],
            "hermes": ["synthesize_schedule"]  # Different methods
        }
        
        token = CapabilityToken(**params)
        
        # "analyze_habits" authorized in "apollo"
        auth_apollo = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="analyze_habits"
        )
        assert auth_apollo.authorize_scope()
        
        # "analyze_habits" NOT authorized in "hermes" (different method_scope)
        auth_hermes = ScopeAuthorizationContext(
            token=token,
            invocation_domain="hermes",
            invocation_method="analyze_habits"
        )
        assert not auth_hermes.authorize_scope()


class TestNoWildcardOrRegexMatching:
    """
    REQUIREMENT: Scope matching is explicit enumeration only.
    No wildcards (*), regex (.*), prefix matching (apol*), or patterns.
    """
    
    def test_wildcard_domain_not_authorized(self, valid_token_params):
        """
        Token authorizes domain "apollo" (explicit).
        Invocation requests domain with wildcard pattern.
        Must reject (wildcard not in scope).
        """
        token = CapabilityToken(**valid_token_params)
        
        # Attempt to use wildcard in invocation
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apol*",  # Wildcard, not explicit domain
            invocation_method="analyze_habits"
        )
        
        result = auth.authorize_scope()
        
        # Wildcard is not an explicitly allowed domain
        assert not result
    
    def test_regex_domain_not_authorized(self, valid_token_params):
        """
        Token authorizes domain "apollo" (explicit).
        Invocation requests domain with regex pattern.
        Must reject.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apol.*",  # Regex, not explicit domain
            invocation_method="analyze_habits"
        )
        
        result = auth.authorize_scope()
        
        assert not result
    
    def test_prefix_matching_not_allowed(self, valid_token_params):
        """
        Token authorizes domain "apollo" (exact, explicit).
        Invocation requests domain "apollonian" (prefix match).
        Must reject (not exact match).
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollonian",  # Prefix of "apollo"? No, different domain.
            invocation_method="analyze_habits"
        )
        
        result = auth.authorize_scope()
        
        assert not result


class TestAdversarialSimilarDomainNames:
    """
    ADVERSARIAL: Domain names can be similar but must match exactly.
    "apollo" ≠ "apollonian" ≠ "apolo" ≠ "APOLLO"
    """
    
    def test_similar_domain_names_are_distinct(self, valid_token_params):
        """
        Token authorizes "apollo".
        Different similar domain names must all be rejected.
        """
        token = CapabilityToken(**valid_token_params)
        
        similar_domains = [
            "apollonian",      # Prefix of token domain
            "apolo",          # Typo (missing 'l')
            "apolоо",         # Cyrillic 'о' instead of ASCII 'o'
            "apollo_",        # Suffix
            "_apollo",        # Prefix
            "Apollo",         # Different case
            "APOLLO",         # All caps
        ]
        
        for similar_domain in similar_domains:
            auth = ScopeAuthorizationContext(
                token=token,
                invocation_domain=similar_domain,
                invocation_method="analyze_habits"
            )
            
            result = auth.authorize_scope()
            
            # Each similar domain MUST be rejected
            assert not result, f"Domain '{similar_domain}' should not be authorized"


class TestAdversarialMethodNameCollisions:
    """
    ADVERSARIAL: Method names can be similar but must match exactly.
    "analyze_habits" ≠ "analyze_habits_" ≠ "analyze" ≠ "ANALYZE_HABITS"
    """
    
    def test_similar_method_names_are_distinct(self, valid_token_params):
        """
        Token authorizes method "analyze_habits" in "apollo".
        Similar method names must all be rejected.
        """
        token = CapabilityToken(**valid_token_params)
        
        similar_methods = [
            "analyze",                    # Prefix
            "analyze_",                   # Incomplete
            "analyze_habit",              # Singular instead of plural
            "analyze_habits_",            # Suffix
            "_analyze_habits",            # Prefix
            "Analyze_Habits",             # Different case
            "ANALYZE_HABITS",             # All caps
            "analyze_habitss",            # Typo (extra 's')
        ]
        
        for similar_method in similar_methods:
            auth = ScopeAuthorizationContext(
                token=token,
                invocation_domain="apollo",
                invocation_method=similar_method
            )
            
            result = auth.authorize_scope()
            
            # Each similar method MUST be rejected
            assert not result, f"Method '{similar_method}' should not be authorized"


class TestNoInferenceFromCapabilityName:
    """
    REQUIREMENT: Method scope is NOT inferred from token's capability field.
    Just because token.capability = "analyze_habits" does NOT mean
    the method "analyze_habits" is automatically authorized.
    """
    
    def test_capability_field_does_not_authorize_method(self, valid_token_params):
        """
        Token has capability="analyze_habits".
        But token's method_scope for "apollo" is ["plan_routine"] (different).
        Invocation requests method "analyze_habits".
        Must be rejected (not in method_scope, despite matching capability).
        """
        params = valid_token_params.copy()
        params["capability"] = "analyze_habits"
        params["method_scope"] = {"apollo": ["plan_routine"]}  # Different method!
        
        token = CapabilityToken(**params)
        
        # Try to invoke method matching capability name
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="analyze_habits"
        )
        
        result = auth.authorize_scope()
        
        # Must reject because method not in method_scope, regardless of capability
        assert not result
        assert "not authorized" in auth.authorization_failure_reason.lower()
    
    def test_capability_field_not_used_for_authorization(self, valid_token_params):
        """
        Token has capability="analyze_habits".
        Invocation requests different method "synthesize_schedule".
        Invocation requests different domain "hermes".
        Neither capability field nor implicit inference apply.
        
        If not in explicit scope, must reject.
        """
        params = valid_token_params.copy()
        params["capability"] = "analyze_habits"
        params["domain_scope"] = ["apollo"]
        params["method_scope"] = {"apollo": ["plan_routine"]}
        
        token = CapabilityToken(**params)
        
        # Invocation for completely different domain/method
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="hermes",
            invocation_method="synthesize_schedule"
        )
        
        result = auth.authorize_scope()
        
        # Must reject (not in explicit scope)
        assert not result


class TestNoFallbackToAnotherDomainOrMethod:
    """
    REQUIREMENT: If invoked domain/method not authorized, no fallback.
    System MUST NOT try alternative domains or methods.
    Failure is immediate and final.
    """
    
    def test_rejected_domain_no_fallback(self, valid_token_params):
        """
        Token authorizes ["apollo", "hermes"].
        Invocation requests "dionysus" (not authorized).
        System MUST NOT try to fallback to "apollo" or "hermes".
        Rejection is immediate.
        """
        params = valid_token_params.copy()
        params["domain_scope"] = ["apollo", "hermes"]
        params["method_scope"] = {
            "apollo": ["analyze_habits"],
            "hermes": ["synthesize_schedule"]
        }
        
        token = CapabilityToken(**params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="dionysus",
            invocation_method="analyze_creativity"
        )
        
        result = auth.authorize_scope()
        
        # Must reject, no fallback to other domains
        assert not result
        assert "dionysus" in auth.authorization_failure_reason.lower()
    
    def test_rejected_method_no_fallback(self, valid_token_params):
        """
        Token authorizes methods ["analyze_habits", "plan_routine"] in "apollo".
        Invocation requests "unauthorized_method" (not authorized).
        System MUST NOT try other methods.
        Rejection is immediate.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="unauthorized_method"
        )
        
        result = auth.authorize_scope()
        
        # Must reject, no fallback to other methods
        assert not result
        assert "unauthorized_method" in auth.authorization_failure_reason.lower()


class TestPartialMatchNotAllowed:
    """
    ADVERSARIAL: Partial string matches must be rejected.
    "analyze_habits" does not match "analyze", "_habits", or "alyze_hab".
    """
    
    def test_prefix_match_rejected(self, valid_token_params):
        """
        Token authorizes "analyze_habits".
        Invocation requests "analyze" (prefix).
        Must reject.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="analyze"
        )
        
        result = auth.authorize_scope()
        assert not result
    
    def test_suffix_match_rejected(self, valid_token_params):
        """
        Token authorizes "analyze_habits".
        Invocation requests "habits" (suffix).
        Must reject.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="habits"
        )
        
        result = auth.authorize_scope()
        assert not result
    
    def test_substring_match_rejected(self, valid_token_params):
        """
        Token authorizes "analyze_habits".
        Invocation requests "nalyze_hab" (substring).
        Must reject.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="nalyze_hab"
        )
        
        result = auth.authorize_scope()
        assert not result


class TestErrorMessagesIdentifyDenial:
    """
    REQUIREMENT: Error messages must clearly identify what was denied.
    "Domain 'X' not authorized" or "Method 'Y' not authorized for domain 'Z'".
    """
    
    def test_error_identifies_denied_domain(self, valid_token_params):
        """
        Invocation for unauthorized domain.
        Error message MUST identify the domain.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="unauthorized_domain",
            invocation_method="method"
        )
        
        auth.authorize_scope()
        
        # Error must identify the domain
        assert auth.authorization_failure_reason is not None
        assert "unauthorized_domain" in auth.authorization_failure_reason.lower()
    
    def test_error_identifies_denied_method(self, valid_token_params):
        """
        Invocation for unauthorized method.
        Error message MUST identify the method and domain.
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="unauthorized_method"
        )
        
        auth.authorize_scope()
        
        # Error must identify the method and domain
        assert auth.authorization_failure_reason is not None
        assert "unauthorized_method" in auth.authorization_failure_reason.lower()
        assert "apollo" in auth.authorization_failure_reason.lower()
    
    def test_error_lists_allowed_methods(self, valid_token_params):
        """
        Error message SHOULD list what methods ARE authorized (for debugging).
        """
        token = CapabilityToken(**valid_token_params)
        
        auth = ScopeAuthorizationContext(
            token=token,
            invocation_domain="apollo",
            invocation_method="bad_method"
        )
        
        auth.authorize_scope()
        
        # Error should help user know what's allowed
        error_msg = auth.authorization_failure_reason.lower()
        # Should mention the authorized methods somehow
        assert "analyze_habits" in error_msg or "plan_routine" in error_msg or "allows" in error_msg


class TestScopeAuthorizationIsIndependent:
    """
    REQUIREMENT: Scope authorization is independent per token.
    Token A's scope does not affect Token B's authorization.
    """
    
    def test_different_tokens_different_scopes(self, token_registry, valid_token_params):
        """
        Token A: authorizes ["apollo"]
        Token B: authorizes ["hermes"]
        
        Invocation with Token A for "hermes" must be rejected.
        Invocation with Token B for "hermes" must pass.
        """
        # Token A: apollo only
        token_a = CapabilityToken(**valid_token_params)
        hash_a = token_registry.issue_token(token_a)
        
        # Token B: hermes only
        params_b = valid_token_params.copy()
        params_b["domain_scope"] = ["hermes"]
        params_b["method_scope"] = {"hermes": ["synthesize_schedule"]}
        params_b["issued_by"] = "admin_user"
        token_b = CapabilityToken(**params_b)
        hash_b = token_registry.issue_token(token_b)
        
        # Token A cannot access hermes
        auth_a = ScopeAuthorizationContext(
            token=token_a,
            invocation_domain="hermes",
            invocation_method="synthesize_schedule"
        )
        assert not auth_a.authorize_scope()
        
        # Token B can access hermes
        auth_b = ScopeAuthorizationContext(
            token=token_b,
            invocation_domain="hermes",
            invocation_method="synthesize_schedule"
        )
        assert auth_b.authorize_scope()
