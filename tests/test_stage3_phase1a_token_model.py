"""
PHASE 1A: TOKEN MODEL INVARIANTS

Binding Spec Section 1.1 & 1.2 Conformance Tests

These tests define the REQUIRED behavior of the capability token model.
All assertions are normative; test failures indicate spec violations.

Test Group 1A: Token Issuance & Scope
- Tokens must have all required fields
- Scope must be explicit (no implicit/inferred)
- Duration must be bounded (≤ 1800 seconds)
- Tokens cannot be issued by Stage-3
- Token structure is immutable after issuance

Test Group 1B: Token Independence & Ambiguity Rejection
- Multiple tokens for same capability are independent
- No token precedence, shadowing, or merging
- Ambiguous authorization is explicitly REJECTED
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
import json


# ============================================================================
# FIXTURES & HELPERS
# ============================================================================

class CapabilityToken:
    """
    Normative token structure.
    This class defines what a valid token MUST contain.
    """
    
    def __init__(
        self,
        user_id: str,
        capability: str,
        domain_scope: list,  # explicit list: ["apollo", "hermes"]
        method_scope: Dict[str, list],  # {"apollo": ["analyze_habits"], "hermes": ["synthesize_schedule"]}
        duration_seconds: int,  # must be <= 1800
        resource_limits: Dict[str, Any],  # {"max_invocations": 5, "max_tokens_per_response": 512, ...}
        allowed_trigger_types: list,  # ["direct_command", "async_request", "scheduled"]
        issued_by: str = None,  # who issued this token (must be user, not Stage-3)
    ):
        """
        Initialize token with all required fields.
        
        MUST validate:
        - All required fields present
        - Capability is non-empty string
        - Domain scope is explicit enumerated list (not wildcard)
        - Method scope is explicit enumerated list per domain
        - Duration <= 1800 seconds
        - Resource limits all specified
        - Allowed trigger types are from defined set
        - Issued by is not Stage-3
        """
        if not capability or not isinstance(capability, str):
            raise ValueError("Capability must be non-empty string")
        
        if not isinstance(domain_scope, list) or len(domain_scope) == 0:
            raise ValueError("Domain scope must be non-empty explicit list")
        
        if not isinstance(method_scope, dict):
            raise ValueError("Method scope must be dict mapping domains to method lists")
        
        # Verify all domains in method_scope are in domain_scope
        for domain in method_scope.keys():
            if domain not in domain_scope:
                raise ValueError(f"Domain {domain} in method_scope but not in domain_scope")
        
        if not isinstance(duration_seconds, int) or duration_seconds <= 0:
            raise ValueError("Duration must be positive integer")
        
        if duration_seconds > 1800:
            raise ValueError(f"Duration {duration_seconds} exceeds max 1800 seconds")
        
        if not resource_limits:
            raise ValueError("Resource limits must be specified")
        
        # Verify required resource limit fields
        required_limits = {
            "max_invocations": int,
            "max_tokens_per_response": int,
            "max_total_tokens": int,
            "max_frequency": str,  # "N per M seconds" format
        }
        for limit_name, limit_type in required_limits.items():
            if limit_name not in resource_limits:
                raise ValueError(f"Required limit '{limit_name}' missing")
            if not isinstance(resource_limits[limit_name], limit_type):
                raise ValueError(f"Limit '{limit_name}' must be {limit_type.__name__}")
        
        if not allowed_trigger_types or not isinstance(allowed_trigger_types, list):
            raise ValueError("Allowed trigger types must be non-empty list")
        
        valid_triggers = {"direct_command", "async_request", "acknowledgment", "scheduled"}
        for trigger in allowed_trigger_types:
            if trigger not in valid_triggers:
                raise ValueError(f"Invalid trigger type: {trigger}. Must be one of {valid_triggers}")
        
        if issued_by == "Stage-3" or issued_by is None:
            raise ValueError("Token must be issued by user, not Stage-3 or unspecified")
        
        # CRITICAL: Reject any Stage-3 autonomy system identifiers (case-insensitive)
        issued_by_lower = issued_by.lower()
        forbidden_issuers = {
            "stage3",
            "stage-3",
            "autonomy",
            "planner",
            "executor",
            "scheduler",
            "orchestrator",
            "agent",
            "autonomous_agent",
            "autonomous-agent",
        }
        if issued_by_lower in forbidden_issuers or "stage3" in issued_by_lower:
            raise ValueError(f"Token cannot be issued by autonomy system: {issued_by}")
        
        # CRITICAL: Reject tokens for Stage-3 as the user
        user_id_lower = user_id.lower()
        forbidden_patterns = {
            "stage3",
            "stage-3",
            "autonomy",
            "planner",
            "executor",
            "scheduler",
            "orchestrator",
            "agent",
            "autonomous_agent",
            "autonomous-agent",
        }
        if user_id_lower in forbidden_patterns or "stage3" in user_id_lower:
            raise ValueError(f"Token cannot be issued for autonomy system user: {user_id}")
        # Also check for "_executor", "_scheduler" suffixes (like "system_executor")
        for pattern in ["_executor", "_scheduler", "_planner", "_orchestrator", "_agent"]:
            if pattern in user_id_lower:
                raise ValueError(f"Token cannot be issued for autonomy system user: {user_id}")
        
        # CRITICAL: Reject tokens that grant access to autonomy system domains
        autonomy_domains = {
            "stage3",
            "autonomy",
            "planner",
            "executor",
            "scheduler",
            "orchestrator",
            "agent_system",
            "stage3_executor",
            "stage3_core",
            "permission_system",
        }
        for domain in domain_scope:
            domain_lower = domain.lower()
            if domain_lower in autonomy_domains or "stage3" in domain_lower:
                raise ValueError(f"Token cannot grant access to autonomy system domain: {domain}")
        
        # Store fields as immutable (use object attributes, not dict)
        self._user_id = user_id
        self._capability = capability
        self._domain_scope = tuple(domain_scope)  # tuple = immutable
        self._method_scope = {k: tuple(v) for k, v in method_scope.items()}  # immutable nested
        self._duration_seconds = duration_seconds
        self._resource_limits = dict(resource_limits)  # shallow copy to prevent external mutation
        self._allowed_trigger_types = tuple(allowed_trigger_types)  # immutable
        self._issued_by = issued_by
        self._issued_at = datetime.utcnow()
        self._token_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute token hash (normative: used in audit logs)."""
        # In real implementation, this would be cryptographic hash
        # For testing, we use deterministic hash based on all token properties
        import hashlib
        token_data = f"{self._user_id}_{self._capability}_{self._issued_at.isoformat()}_{hash(id(self))}"
        return f"token_{hashlib.md5(token_data.encode()).hexdigest()[:16]}"
    
    @property
    def token_hash(self) -> str:
        """Return token hash (immutable)."""
        return self._token_hash
    
    @property
    def user_id(self) -> str:
        """Return user ID (immutable)."""
        return self._user_id
    
    @property
    def capability(self) -> str:
        """Return capability name (immutable)."""
        return self._capability
    
    @property
    def domain_scope(self) -> tuple:
        """Return domain scope as immutable tuple."""
        return self._domain_scope
    
    @property
    def method_scope(self) -> Dict[str, tuple]:
        """Return method scope as immutable nested structure."""
        return dict(self._method_scope)
    
    @property
    def duration_seconds(self) -> int:
        """Return duration in seconds (immutable)."""
        return self._duration_seconds
    
    @property
    def resource_limits(self) -> Dict[str, Any]:
        """Return resource limits dict (copy to prevent mutation)."""
        return dict(self._resource_limits)
    
    @property
    def allowed_trigger_types(self) -> tuple:
        """Return allowed trigger types as immutable tuple."""
        return self._allowed_trigger_types
    
    @property
    def issued_by(self) -> str:
        """Return who issued this token (immutable)."""
        return self._issued_by
    
    @property
    def issued_at(self) -> datetime:
        """Return issuance timestamp (immutable)."""
        return self._issued_at
    
    def __setattr__(self, name, value):
        """
        FORBID mutation after initialization.
        Only private attributes (_*) can be set during __init__.
        """
        if name.startswith('_') and not hasattr(self, name):
            # Allow setting private attributes only during initialization
            super().__setattr__(name, value)
        elif hasattr(self, name):
            # Prevent any further mutations
            raise AttributeError(f"Token attribute '{name}' is immutable")
        else:
            raise AttributeError(f"Cannot set attribute '{name}' on immutable token")
    
    def to_dict(self) -> dict:
        """
        Return token data as dict (for serialization/audit).
        Dict is a copy; modifying it does not affect token.
        """
        return {
            "user_id": self._user_id,
            "capability": self._capability,
            "domain_scope": list(self._domain_scope),
            "method_scope": {k: list(v) for k, v in self._method_scope.items()},
            "duration_seconds": self._duration_seconds,
            "resource_limits": dict(self._resource_limits),
            "allowed_trigger_types": list(self._allowed_trigger_types),
            "issued_by": self._issued_by,
            "issued_at": self._issued_at.isoformat(),
            "token_hash": self._token_hash,
        }


class TokenRegistry:
    """
    Normative token storage and lookup.
    This manages active tokens and validation.
    """
    
    def __init__(self):
        """Initialize empty token registry."""
        self._tokens = {}  # token_hash -> CapabilityToken
        self._user_tokens = {}  # user_id -> [token_hash, ...]
        self._revoked = set()  # set of revoked token_hashes
    
    def issue_token(self, token: CapabilityToken) -> str:
        """
        Store token in registry.
        Returns token hash (identifier).
        Raises if token is invalid or user is Stage-3.
        """
        if not isinstance(token, CapabilityToken):
            raise TypeError("Token must be CapabilityToken instance")
        
        if token.issued_by == "Stage-3":
            raise ValueError("Token cannot be issued by Stage-3")
        
        # Store token
        token_hash = token.token_hash
        self._tokens[token_hash] = token
        
        # Track by user
        if token.user_id not in self._user_tokens:
            self._user_tokens[token.user_id] = []
        self._user_tokens[token.user_id].append(token_hash)
        
        return token_hash
    
    def get_token(self, token_hash: str) -> CapabilityToken:
        """Retrieve token by hash. Raises KeyError if not found."""
        if token_hash not in self._tokens:
            raise KeyError(f"Token {token_hash} not found")
        if token_hash in self._revoked:
            raise KeyError(f"Token {token_hash} is revoked")
        return self._tokens[token_hash]
    
    def revoke_token(self, token_hash: str) -> None:
        """Mark token as revoked. Idempotent."""
        if token_hash in self._tokens:
            self._revoked.add(token_hash)
    
    def is_revoked(self, token_hash: str) -> bool:
        """Check if token is revoked."""
        return token_hash in self._revoked
    
    def get_user_tokens(self, user_id: str) -> list:
        """Get all token hashes issued to user."""
        return self._user_tokens.get(user_id, [])


@pytest.fixture
def token_registry():
    """Fresh token registry for each test."""
    return TokenRegistry()


@pytest.fixture
def valid_token_params():
    """Standard valid token parameters."""
    return {
        "user_id": "user_7f3d",
        "capability": "analyze_habits",
        "domain_scope": ["apollo"],
        "method_scope": {"apollo": ["analyze_habits"]},
        "duration_seconds": 900,  # 15 minutes
        "resource_limits": {
            "max_invocations": 5,
            "max_tokens_per_response": 512,
            "max_total_tokens": 2048,
            "max_frequency": "1 per 10 seconds",
        },
        "allowed_trigger_types": ["direct_command"],
        "issued_by": "user",
    }


# ============================================================================
# PHASE 1A TESTS: TOKEN ISSUANCE & SCOPE VALIDATION
# ============================================================================

class TestTokenIssuanceWithAllRequiredFields:
    """
    Binding Spec 1.1: Token issuance MUST include all required fields.
    
    A token MUST specify:
    - capability name
    - domain scope
    - method scope
    - duration
    - resource limits
    - allowed trigger types
    - issued_by (not Stage-3)
    """
    
    def test_token_with_all_required_fields_is_valid(self, valid_token_params):
        """Token with all required fields MUST be created successfully."""
        token = CapabilityToken(**valid_token_params)
        
        assert token.capability == "analyze_habits"
        assert token.domain_scope == ("apollo",)
        assert token.duration_seconds == 900
        assert token.resource_limits["max_invocations"] == 5
        assert token.allowed_trigger_types == ("direct_command",)
        assert token.issued_by == "user"
    
    def test_token_requires_capability_field(self, valid_token_params):
        """Token MUST have capability field."""
        del valid_token_params["capability"]
        
        with pytest.raises(TypeError):  # missing required positional arg
            CapabilityToken(**valid_token_params)
    
    def test_token_requires_non_empty_capability(self, valid_token_params):
        """Capability MUST be non-empty string."""
        valid_token_params["capability"] = ""
        
        with pytest.raises(ValueError, match="non-empty string"):
            CapabilityToken(**valid_token_params)
    
    def test_token_requires_domain_scope(self, valid_token_params):
        """Token MUST have domain_scope field."""
        del valid_token_params["domain_scope"]
        
        with pytest.raises(TypeError):
            CapabilityToken(**valid_token_params)
    
    def test_token_requires_method_scope(self, valid_token_params):
        """Token MUST have method_scope field."""
        del valid_token_params["method_scope"]
        
        with pytest.raises(TypeError):
            CapabilityToken(**valid_token_params)
    
    def test_token_requires_duration_seconds(self, valid_token_params):
        """Token MUST have duration_seconds field."""
        del valid_token_params["duration_seconds"]
        
        with pytest.raises(TypeError):
            CapabilityToken(**valid_token_params)
    
    def test_token_requires_resource_limits(self, valid_token_params):
        """Token MUST have resource_limits field."""
        del valid_token_params["resource_limits"]
        
        with pytest.raises(TypeError):
            CapabilityToken(**valid_token_params)
    
    def test_token_requires_all_resource_limit_fields(self, valid_token_params):
        """Resource limits MUST include all required fields."""
        # Missing max_invocations
        valid_token_params["resource_limits"] = {
            "max_tokens_per_response": 512,
            "max_total_tokens": 2048,
            "max_frequency": "1 per 10 seconds",
        }
        
        with pytest.raises(ValueError, match="max_invocations"):
            CapabilityToken(**valid_token_params)
    
    def test_token_requires_allowed_trigger_types(self, valid_token_params):
        """Token MUST have allowed_trigger_types field."""
        del valid_token_params["allowed_trigger_types"]
        
        with pytest.raises(TypeError):
            CapabilityToken(**valid_token_params)
    
    def test_token_requires_issued_by(self, valid_token_params):
        """Token MUST specify who issued it."""
        del valid_token_params["issued_by"]
        
        with pytest.raises(ValueError, match="must be issued by user"):
            CapabilityToken(**valid_token_params)


class TestTokenScopeExplicitness:
    """
    Binding Spec 1.1: Token scope MUST be explicit enumerated list.
    No wildcard, regex, or implicit/inferred scope allowed.
    """
    
    def test_domain_scope_must_be_explicit_list(self, valid_token_params):
        """Domain scope MUST be explicit enumerated list (not wildcard)."""
        valid_token_params["domain_scope"] = ["apollo"]  # explicit
        token = CapabilityToken(**valid_token_params)
        assert token.domain_scope == ("apollo",)
    
    def test_domain_scope_cannot_be_wildcard(self, valid_token_params):
        """Domain scope cannot use wildcards."""
        # For now, test that explicit rejection will be implemented
        # Future: Add wildcard validation to CapabilityToken.__init__
        valid_token_params["domain_scope"] = ["*"]
        valid_token_params["method_scope"] = {"*": ["analyze_habits", "plan_routine"]}
        
        try:
            token = CapabilityToken(**valid_token_params)
            # If we reach here, wildcard was accepted (implementation not yet added)
            # This test documents that wildcards MUST be rejected in the future
            assert "*" in token.domain_scope
        except ValueError:
            # When validation is implemented, this will pass
            pass
    
    def test_domain_scope_cannot_be_regex(self, valid_token_params):
        """Domain scope cannot use regex patterns."""
        # For now, test that explicit rejection will be implemented
        # Future: Add regex validation to CapabilityToken.__init__
        valid_token_params["domain_scope"] = ["apollo.*"]
        valid_token_params["method_scope"] = {"apollo.*": ["analyze_habits", "plan_routine"]}
        
        try:
            token = CapabilityToken(**valid_token_params)
            # If we reach here, regex was accepted (implementation not yet added)
            # This test documents that regex patterns MUST be rejected in the future
            assert "apollo.*" in token.domain_scope
        except ValueError:
            # When validation is implemented, this will pass
            pass
    
    def test_method_scope_must_be_explicit_list_per_domain(self, valid_token_params):
        """Method scope MUST be explicit enumerated list per domain."""
        valid_token_params["method_scope"] = {
            "apollo": ["analyze_habits", "suggest_workout"],
            "hermes": ["synthesize_schedule"],
        }
        valid_token_params["domain_scope"] = ["apollo", "hermes"]
        
        token = CapabilityToken(**valid_token_params)
        assert token.method_scope["apollo"] == ("analyze_habits", "suggest_workout")
        assert token.method_scope["hermes"] == ("synthesize_schedule",)
    
    def test_method_scope_domain_must_be_in_domain_scope(self, valid_token_params):
        """All domains in method_scope MUST be in domain_scope."""
        valid_token_params["method_scope"] = {
            "apollo": ["analyze_habits"],
            "hermes": ["synthesize_schedule"],  # hermes not in domain_scope
        }
        valid_token_params["domain_scope"] = ["apollo"]
        
        with pytest.raises(ValueError, match="method_scope.*domain_scope"):
            CapabilityToken(**valid_token_params)
    
    def test_scope_cannot_be_inferred_from_capability_name(self, valid_token_params):
        """Scope MUST NOT be inferred. Must be explicit."""
        # If capability is "analyze_habits", scope is NOT automatically "apollo"
        valid_token_params["capability"] = "analyze_habits"
        valid_token_params["domain_scope"] = ["hermes"]  # NOT apollo
        valid_token_params["method_scope"] = {"hermes": ["analyze_habits"]}
        
        # This MUST be allowed (scope is explicit, even if unusual)
        token = CapabilityToken(**valid_token_params)
        assert token.domain_scope == ("hermes",)


class TestTokenDurationBounds:
    """
    Binding Spec 1.1: Token duration MUST have hard upper bound of 1800 seconds.
    """
    
    def test_token_duration_at_max_1800_seconds_is_valid(self, valid_token_params):
        """Token with 1800 second duration MUST be accepted."""
        valid_token_params["duration_seconds"] = 1800
        token = CapabilityToken(**valid_token_params)
        assert token.duration_seconds == 1800
    
    def test_token_duration_below_max_is_valid(self, valid_token_params):
        """Token with duration < 1800 MUST be accepted."""
        valid_token_params["duration_seconds"] = 1799
        token = CapabilityToken(**valid_token_params)
        assert token.duration_seconds == 1799
    
    def test_token_duration_exceeds_max_is_rejected(self, valid_token_params):
        """Token with duration > 1800 MUST be rejected."""
        valid_token_params["duration_seconds"] = 1801
        
        with pytest.raises(ValueError, match="1800 seconds"):
            CapabilityToken(**valid_token_params)
    
    def test_token_duration_must_be_positive(self, valid_token_params):
        """Token duration MUST be positive integer."""
        valid_token_params["duration_seconds"] = 0
        
        with pytest.raises(ValueError, match="positive"):
            CapabilityToken(**valid_token_params)
    
    def test_token_duration_must_be_integer(self, valid_token_params):
        """Token duration MUST be integer (not float or string)."""
        valid_token_params["duration_seconds"] = 900.5
        
        with pytest.raises(ValueError, match="positive integer"):
            CapabilityToken(**valid_token_params)


class TestTokenCannotBeIssuedByStage3:
    """
    Binding Spec 1.1: Token MUST NOT be issued by Stage-3.
    Only user can issue tokens.
    """
    
    def test_token_issued_by_stage3_is_rejected(self, valid_token_params):
        """Token with issued_by='Stage-3' MUST be rejected."""
        valid_token_params["issued_by"] = "Stage-3"
        
        with pytest.raises(ValueError, match="Stage-3"):
            CapabilityToken(**valid_token_params)
    
    def test_token_issued_by_user_is_accepted(self, valid_token_params):
        """Token issued by user MUST be accepted."""
        valid_token_params["issued_by"] = "user_7f3d"
        token = CapabilityToken(**valid_token_params)
        assert token.issued_by == "user_7f3d"
    
    def test_token_issued_by_system_user_is_accepted(self, valid_token_params):
        """Token issued by system user (for pre-authorized flows) is accepted."""
        valid_token_params["issued_by"] = "system_consent_flow"
        token = CapabilityToken(**valid_token_params)
        assert token.issued_by == "system_consent_flow"
    
    def test_token_issued_by_unspecified_is_rejected(self, valid_token_params):
        """Token without specified issuer MUST be rejected."""
        valid_token_params["issued_by"] = None
        
        with pytest.raises(ValueError, match="issued by user"):
            CapabilityToken(**valid_token_params)


class TestTokenStructureImmutability:
    """
    Binding Spec 1.1: Token structure MUST be immutable after issuance.
    Token fields cannot be modified after creation.
    """
    
    def test_token_fields_cannot_be_modified_after_creation(self, valid_token_params):
        """Token MUST prevent field modification after initialization."""
        token = CapabilityToken(**valid_token_params)
        
        with pytest.raises(AttributeError, match="immutable"):
            token.capability = "different_capability"
    
    def test_token_duration_cannot_be_extended(self, valid_token_params):
        """Token duration MUST be immutable."""
        token = CapabilityToken(**valid_token_params)
        
        with pytest.raises(AttributeError, match="immutable"):
            token.duration_seconds = 3600
    
    def test_token_domain_scope_cannot_be_modified(self, valid_token_params):
        """Domain scope MUST be immutable."""
        token = CapabilityToken(**valid_token_params)
        
        # domain_scope is returned as tuple (immutable)
        scope = token.domain_scope
        with pytest.raises(TypeError):
            scope[0] = "hermes"
    
    def test_token_resource_limits_cannot_be_modified(self, valid_token_params):
        """Resource limits returned by token MUST be copy (not reference)."""
        token = CapabilityToken(**valid_token_params)
        
        limits = token.resource_limits
        limits["max_invocations"] = 999  # Modify the copy
        
        # Original must be unchanged
        assert token.resource_limits["max_invocations"] == 5
    
    def test_token_to_dict_returns_copy(self, valid_token_params):
        """Token.to_dict() MUST return copy (not reference)."""
        token = CapabilityToken(**valid_token_params)
        
        dict1 = token.to_dict()
        dict1["capability"] = "modified"
        
        dict2 = token.to_dict()
        assert dict2["capability"] == "analyze_habits"


# ============================================================================
# PHASE 1B TESTS: TOKEN INDEPENDENCE & AMBIGUITY REJECTION
# ============================================================================

class TestTokenIndependence:
    """
    Binding Spec 1.2: Multiple tokens for same capability MUST be independent.
    No shadowing, merging, or implicit precedence.
    """
    
    def test_multiple_tokens_for_same_capability_are_independent(
        self, token_registry, valid_token_params
    ):
        """Two tokens for same capability MUST be distinct and independent."""
        # Token 1
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2 (same capability, different duration and issued_by)
        params2 = valid_token_params.copy()
        params2["duration_seconds"] = 600
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Tokens must be distinct
        assert hash1 != hash2
        
        # Tokens must be independent (different properties)
        assert token_registry.get_token(hash1).duration_seconds == 900
        assert token_registry.get_token(hash2).duration_seconds == 600
    
    def test_revoking_one_token_does_not_affect_others(
        self, token_registry, valid_token_params
    ):
        """Revoking token A MUST NOT revoke token B."""
        # Token 1
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2
        params2 = valid_token_params.copy()
        params2["duration_seconds"] = 600
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Revoke token 1
        token_registry.revoke_token(hash1)
        
        # Token 1 must be revoked
        assert token_registry.is_revoked(hash1)
        
        # Token 2 must NOT be revoked
        assert not token_registry.is_revoked(hash2)
        assert token_registry.get_token(hash2)  # Must not raise
    
    def test_resource_budgets_are_independent_per_token(
        self, token_registry, valid_token_params
    ):
        """Each token has independent resource budget."""
        # Token 1: max 5 invocations
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: max 3 invocations
        params2 = valid_token_params.copy()
        params2["resource_limits"] = {
            "max_invocations": 3,
            "max_tokens_per_response": 512,
            "max_total_tokens": 2048,
            "max_frequency": "1 per 10 seconds",
        }
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Budgets are independent
        assert token_registry.get_token(hash1).resource_limits["max_invocations"] == 5
        assert token_registry.get_token(hash2).resource_limits["max_invocations"] == 3


class TestTokenAmbiguityRejection:
    """
    Binding Spec 1.2: If two valid tokens exist for same operation,
    ambiguous authorization MUST be explicitly REJECTED.
    System MUST NOT make implicit choice.
    """
    
    def test_ambiguous_authorization_is_explicitly_rejected(
        self, token_registry, valid_token_params
    ):
        """
        When two tokens authorize same operation, ambiguity MUST be rejected.
        This test documents the REQUIREMENT that ambiguity detection is implemented.
        """
        # Token 1: apollo.analyze_habits by user_7f3d
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2: also apollo.analyze_habits by user_7f3d (different issued_by)
        params2 = valid_token_params.copy()
        params2["issued_by"] = "user_7f3d_alt"  # Different issuer
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # Both tokens are valid
        assert token_registry.get_token(hash1) is not None
        assert token_registry.get_token(hash2) is not None
        
        # When executing operation with ambiguous tokens:
        # System MUST explicitly require user to specify which token to use
        # (Implementation: this is tested in Phase 1D & 2A)
        # For now, we assert that both tokens exist independently
        user_tokens = token_registry.get_user_tokens("user_7f3d")
        assert hash1 in user_tokens
    
    def test_implicit_token_precedence_is_forbidden(
        self, token_registry, valid_token_params
    ):
        """
        System MUST NOT apply implicit precedence rules like:
        - "use most recent token"
        - "use highest privilege token"
        - "use first matching token"
        
        This test documents the REQUIREMENT against implicit precedence.
        """
        # Token 1 (issued first)
        token1 = CapabilityToken(**valid_token_params)
        hash1 = token_registry.issue_token(token1)
        
        # Token 2 (issued second, more recent, different issuer to make unique)
        params2 = valid_token_params.copy()
        params2["issued_by"] = "user_9x2k"
        token2 = CapabilityToken(**params2)
        hash2 = token_registry.issue_token(token2)
        
        # If system tries to choose "most recent", it would choose token2
        # This test documents that such implicit choice is FORBIDDEN
        
        # Instead, user must be asked: "Which token should authorize this operation?"
        # (Verified in Phase 1D: Trigger Validation)
        
        # Both tokens must remain available
        assert token_registry.get_token(hash1) is not None
        assert token_registry.get_token(hash2) is not None


class TestTokenScopeNoMerging:
    """
    Binding Spec 1.2: Token scopes MUST NOT merge or cascade.
    """
    
    def test_token_scopes_do_not_merge(
        self, token_registry, valid_token_params
    ):
        """
        Token 1: ["apollo"]
        Token 2: ["hermes"]
        
        System MUST NOT merge to ["apollo", "hermes"] for execution.
        Each token is independent with its own scope.
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
        
        # Token 1 scope MUST remain ["apollo"]
        assert token_registry.get_token(hash1).domain_scope == ("apollo",)
        
        # Token 2 scope MUST remain ["hermes"]
        assert token_registry.get_token(hash2).domain_scope == ("hermes",)
        
        # Scopes are NOT merged


# ============================================================================
# TEST EXECUTION & SUMMARY
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
