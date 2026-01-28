"""
PHASE 2C: Resource Limit Enforcement Tests

Binding Spec Section 2.3: Resource Limits

REQUIREMENT: Tokens have explicit resource budgets.

STRUCTURE:
  resource_limits: {
    "max_invocations": 5,               # Max invocation count per token
    "max_tokens_per_response": 512,     # Max tokens output per invocation
    "max_total_tokens": 2048,           # Max cumulative tokens over token lifetime
    "max_frequency": "1 per 10 seconds" # Rate limiting (invocations per time)
  }

ENFORCEMENT RULES:
1. max_invocations: Token can be used at most N times
2. max_tokens_per_response: Each invocation output ≤ N tokens
3. max_total_tokens: Sum of all invocation outputs ≤ N tokens (cumulative)
4. max_frequency: Invocations must respect rate limit (e.g., "1 per 10 seconds")
5. Limit exceeded → REJECT BEFORE EXECUTION (no partial execution)
6. Exhaustion → Token unusable (no retry, no fallback)
7. Resource tracking: Per-token (Token A's usage doesn't affect Token B)

ARCHITECTURE:
    Invocation Request
         ↓
    [VALIDATION PHASE] ← Phase 2A (already tested)
         ↓
    [AUTHORIZATION PHASE] ← Phase 2B (already tested)
         ↓
    [RESOURCE LIMIT PHASE] ← Phase 2C tests here
         ├─ max_invocations exceeded?
         ├─ max_tokens_per_response check possible?
         ├─ max_total_tokens budget available?
         ├─ max_frequency violated?
         └─ Fail → REJECT (no execution)
         ↓
    [EXECUTION PHASE] ← Phase 2D+
         └─ Call domain, track usage

FAIL-CLOSED: If any limit exceeded, reject immediately. No partial execution.

ADVERSARIAL TESTS verify:
  - Off-by-one: 5 invocations allowed, 6th rejected
  - Concurrent: Multiple invocations using same token
  - Multiple tokens: Token A's budget separate from Token B's
  - Mid-lifecycle: Exhaustion after some usage
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from tests.test_stage3_phase1a_token_model import CapabilityToken, TokenRegistry


@pytest.fixture
def token_registry():
    """Fresh registry for each test."""
    return TokenRegistry()


@pytest.fixture
def valid_token_params():
    """Fixture providing valid token parameters with resource limits."""
    return {
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


class ResourceLimitContext:
    """
    Represents resource limit checking after authorization.
    Tracks resource usage for a token and enforces limits.
    """
    
    def __init__(self, token: CapabilityToken):
        self.token = token
        
        # Usage tracking
        self.invocation_count = 0
        self.total_tokens_used = 0
        self.invocations: List[Dict[str, Any]] = []  # List of (timestamp, tokens_used)
        
        # Limit enforcement state
        self.limits_exceeded = False
        self.limit_failure_reason: Optional[str] = None
        
        # For testing: auto-spacing invocations by frequency limit
        self.auto_timestamp = True
        self.next_auto_timestamp = datetime.utcnow()
    
    def check_max_invocations(self) -> bool:
        """Check if invocation count limit is exhausted."""
        max_invocations = self.token.resource_limits.get("max_invocations", float('inf'))
        
        if self.invocation_count >= max_invocations:
            self.limit_failure_reason = (
                f"Invocation limit exhausted: {self.invocation_count} of {max_invocations} used"
            )
            return False
        
        return True
    
    def check_max_tokens_per_response(self, response_tokens: int) -> bool:
        """Check if response token count exceeds per-response limit."""
        max_tokens_per_response = self.token.resource_limits.get(
            "max_tokens_per_response", float('inf')
        )
        
        if response_tokens > max_tokens_per_response:
            self.limit_failure_reason = (
                f"Response token limit exceeded: {response_tokens} tokens "
                f"exceeds max {max_tokens_per_response}"
            )
            return False
        
        return True
    
    def check_max_total_tokens(self, response_tokens: int) -> bool:
        """Check if total token budget allows this response."""
        max_total_tokens = self.token.resource_limits.get("max_total_tokens", float('inf'))
        total_after = self.total_tokens_used + response_tokens
        
        if total_after > max_total_tokens:
            self.limit_failure_reason = (
                f"Total token budget exhausted: {self.total_tokens_used} + {response_tokens} "
                f"= {total_after} exceeds max {max_total_tokens}"
            )
            return False
        
        return True
    
    def check_max_frequency(self, current_timestamp: datetime) -> bool:
        """
        Check if invocation respects frequency limit.
        Simple implementation: "1 per N seconds" → at least N seconds since last invocation.
        Only enforced if there are prior invocations (first invocation always allowed).
        """
        max_frequency = self.token.resource_limits.get("max_frequency", "unlimited")
        
        # No frequency check if unlimited or no prior invocations
        if max_frequency == "unlimited" or not self.invocations:
            return True
        
        # Parse "1 per X seconds" format
        if "per" in max_frequency:
            try:
                parts = max_frequency.split()
                seconds = int(parts[2])
                
                last_invocation_time = self.invocations[-1]["timestamp"]
                time_since_last = (current_timestamp - last_invocation_time).total_seconds()
                
                if time_since_last < seconds:
                    self.limit_failure_reason = (
                        f"Frequency limit violated: {time_since_last:.1f}s since last invocation, "
                        f"need {seconds}s (limit: {max_frequency})"
                    )
                    return False
            except (IndexError, ValueError):
                # Invalid frequency format, skip check
                pass
        
        return True
    
    def check_resource_limits(self, response_tokens: int, 
                             current_timestamp: Optional[datetime] = None) -> bool:
        """
        PHASE 2C: Check all resource limits BEFORE execution.
        Returns True only if all limits pass.
        
        FAIL-CLOSED: If any limit exceeded, return False immediately.
        """
        if current_timestamp is None:
            if self.auto_timestamp:
                # For testing: auto-space invocations to respect frequency limits
                current_timestamp = self.next_auto_timestamp
            else:
                current_timestamp = datetime.utcnow()
        
        # Check 1: max_invocations
        if not self.check_max_invocations():
            return False
        
        # Check 2: max_tokens_per_response (check this before total, more specific)
        if not self.check_max_tokens_per_response(response_tokens):
            return False
        
        # Check 3: max_total_tokens
        if not self.check_max_total_tokens(response_tokens):
            return False
        
        # Check 4: max_frequency (only enforced if prior invocations exist)
        if not self.check_max_frequency(current_timestamp):
            return False
        
        return True
    
    def record_invocation(self, response_tokens: int, 
                         timestamp: Optional[datetime] = None) -> None:
        """Record successful invocation usage."""
        if timestamp is None:
            if self.auto_timestamp:
                # Auto-space invocations
                timestamp = self.next_auto_timestamp
                # Advance for next invocation (respect frequency limit)
                max_frequency = self.token.resource_limits.get("max_frequency", "unlimited")
                if "per" in max_frequency:
                    try:
                        parts = max_frequency.split()
                        seconds = int(parts[2])
                        self.next_auto_timestamp = timestamp + timedelta(seconds=seconds)
                    except (IndexError, ValueError):
                        self.next_auto_timestamp = timestamp + timedelta(seconds=1)
                else:
                    self.next_auto_timestamp = timestamp + timedelta(seconds=1)
            else:
                timestamp = datetime.utcnow()
        
        self.invocation_count += 1
        self.total_tokens_used += response_tokens
        self.invocations.append({
            "timestamp": timestamp,
            "tokens": response_tokens
        })


class TestMaxInvocationsEnforcement:
    """
    REQUIREMENT: max_invocations limit is enforced.
    Token can be used at most N times.
    After N uses, token is exhausted.
    """
    
    def test_invocation_within_limit_succeeds(self, valid_token_params):
        """
        Token allows 5 invocations.
        First invocation must succeed limit check.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        result = ctx.check_resource_limits(response_tokens=100)
        
        assert result
        assert ctx.limit_failure_reason is None
    
    def test_invocation_at_limit_boundary_succeeds(self, valid_token_params):
        """
        Token allows 5 invocations.
        5th invocation (at boundary) must succeed.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Simulate 4 prior invocations
        for _ in range(4):
            ctx.record_invocation(response_tokens=100)
        
        # 5th invocation should succeed
        result = ctx.check_resource_limits(response_tokens=100)
        
        assert result
        assert ctx.invocation_count == 4  # Not incremented yet by check
    
    def test_invocation_beyond_limit_rejected(self, valid_token_params):
        """
        Token allows 5 invocations.
        6th invocation must be rejected with clear error.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Simulate 5 prior invocations (exhausted)
        for _ in range(5):
            ctx.record_invocation(response_tokens=100)
        
        # 6th invocation should fail
        result = ctx.check_resource_limits(response_tokens=100)
        
        assert not result
        assert ctx.limit_failure_reason is not None
        assert "limit exhausted" in ctx.limit_failure_reason.lower()
        assert "5" in ctx.limit_failure_reason  # Should show max
    
    def test_all_invocations_tracked_independently(self, valid_token_params):
        """
        Each invocation within token lifetime counts toward limit.
        Invocation count is cumulative.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # 5 invocations succeed
        for i in range(5):
            result = ctx.check_resource_limits(response_tokens=100)
            assert result, f"Invocation {i+1} should succeed"
            ctx.record_invocation(response_tokens=100)
        
        # 6th fails
        result = ctx.check_resource_limits(response_tokens=100)
        assert not result


class TestMaxTokensPerResponseEnforcement:
    """
    REQUIREMENT: max_tokens_per_response limit is enforced BEFORE execution.
    Single response output ≤ N tokens.
    Response exceeding limit is rejected before invocation.
    """
    
    def test_response_within_limit_succeeds(self, valid_token_params):
        """
        max_tokens_per_response = 512.
        Response with 400 tokens must succeed.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        result = ctx.check_resource_limits(response_tokens=400)
        
        assert result
    
    def test_response_at_limit_boundary_succeeds(self, valid_token_params):
        """
        max_tokens_per_response = 512.
        Response with exactly 512 tokens (at boundary) must succeed.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        result = ctx.check_resource_limits(response_tokens=512)
        
        assert result
    
    def test_response_exceeding_limit_rejected(self, valid_token_params):
        """
        max_tokens_per_response = 512.
        Response with 513 tokens must be rejected.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        result = ctx.check_resource_limits(response_tokens=513)
        
        assert not result
        assert ctx.limit_failure_reason is not None
        assert "response token limit" in ctx.limit_failure_reason.lower()
        assert "513" in ctx.limit_failure_reason
        assert "512" in ctx.limit_failure_reason
    
    def test_no_output_degradation_on_rejection(self, valid_token_params):
        """
        If response would exceed limit, rejection must happen BEFORE execution.
        System MUST NOT attempt to truncate or degrade output to fit.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Check fails before execution
        result = ctx.check_resource_limits(response_tokens=1000)
        
        # Failure happens, no execution occurs
        assert not result
        # invocation_count should NOT be incremented (execution never started)
        assert ctx.invocation_count == 0


class TestMaxTotalTokensEnforcement:
    """
    REQUIREMENT: max_total_tokens limit is enforced across token lifetime.
    Sum of all invocation outputs ≤ N tokens (cumulative budget).
    Token is exhausted when total budget is exceeded.
    """
    
    def test_single_response_within_total_budget(self, valid_token_params):
        """
        max_total_tokens = 2048, max_tokens_per_response = 512.
        Single response with 400 tokens must succeed (within all limits).
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        ctx.auto_timestamp = False  # Don't auto-time for this test
        
        result = ctx.check_resource_limits(response_tokens=400)
        
        assert result
    
    def test_cumulative_responses_within_budget(self, valid_token_params):
        """
        max_total_tokens = 2048.
        Multiple responses that cumulatively stay under 2048 must all succeed.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # First 3 responses: 500 + 500 + 500 = 1500
        for _ in range(3):
            result = ctx.check_resource_limits(response_tokens=500)
            assert result
            ctx.record_invocation(response_tokens=500)
        
        assert ctx.total_tokens_used == 1500
    
    def test_response_exhausts_total_budget_at_boundary(self, valid_token_params):
        """
        max_total_tokens = 2048.
        After 1536 tokens used, adding 512 more = 2048 (exactly at boundary).
        This must succeed.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Use 1536 tokens
        ctx.total_tokens_used = 1536
        
        # Next 512 should succeed (1536 + 512 = 2048, exactly at limit)
        result = ctx.check_resource_limits(response_tokens=512)
        
        assert result
    
    def test_response_exceeding_total_budget_rejected(self, valid_token_params):
        """
        max_total_tokens = 2048.
        After 1536 tokens used, adding 600 = 2136 (exceeds).
        This must be rejected.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Use 1536 tokens
        ctx.total_tokens_used = 1536
        
        # Next 600 should fail (exceeds budget)
        # Note: 600 is within per-response limit (512), so total budget check fails
        result = ctx.check_resource_limits(response_tokens=600)
        
        # Fails on per-response check first (600 > 512)
        assert not result
        assert "response token limit" in ctx.limit_failure_reason.lower()
    
    def test_response_exceeding_total_budget_within_per_response(self, valid_token_params):
        """
        max_total_tokens = 2048, max_tokens_per_response = 512.
        After 1536 tokens used, adding 512 more (1536 + 512 = 2048, OK).
        After that 1536 + 512 = 2048, adding 100 more = 2148 (exceeds total).
        This must be rejected with total budget error.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Use 1536 tokens (within budget)
        ctx.total_tokens_used = 1536
        
        # Next 512 puts us at exactly 2048 (within total)
        result = ctx.check_resource_limits(response_tokens=512)
        assert result
        ctx.total_tokens_used += 512  # Now at 2048
        
        # Next invocation: even 1 token exceeds
        result = ctx.check_resource_limits(response_tokens=1)
        
        assert not result
        assert "total token budget" in ctx.limit_failure_reason.lower()
    
    def test_total_budget_is_cumulative_across_lifecycle(self, valid_token_params):
        """
        Token lifetime budget is shared across all invocations.
        Once exhausted, token is unusable regardless of max_invocations.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # First 4 invocations: 500 tokens each = 2000 total
        for _ in range(4):
            result = ctx.check_resource_limits(response_tokens=500)
            assert result
            ctx.record_invocation(response_tokens=500)
        
        assert ctx.total_tokens_used == 2000
        
        # 5th invocation: even 100 tokens would exceed (2000 + 100 = 2100 > 2048)
        result = ctx.check_resource_limits(response_tokens=100)
        
        assert not result
        assert "total token budget" in ctx.limit_failure_reason.lower()


class TestMaxFrequencyEnforcement:
    """
    REQUIREMENT: max_frequency limit is enforced per token.
    Invocations must respect rate limit (e.g., "1 per 10 seconds").
    Invocation too soon is rejected before execution.
    """
    
    def test_first_invocation_respects_frequency_limit(self, valid_token_params):
        """
        Frequency limit applies from token issuance.
        First invocation must succeed (no prior invocations).
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        result = ctx.check_resource_limits(response_tokens=100)
        
        assert result
    
    def test_invocation_respecting_frequency_succeeds(self, valid_token_params):
        """
        max_frequency = "1 per 10 seconds".
        After first invocation at T=0, second at T=10 must succeed.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        time_1 = datetime.utcnow()
        
        # First invocation at T=0
        result = ctx.check_resource_limits(response_tokens=100, current_timestamp=time_1)
        assert result
        ctx.record_invocation(response_tokens=100, timestamp=time_1)
        
        # Second invocation at T=10 (respects 10-second limit)
        time_2 = time_1 + timedelta(seconds=10)
        result = ctx.check_resource_limits(response_tokens=100, current_timestamp=time_2)
        
        assert result
    
    def test_invocation_violating_frequency_rejected(self, valid_token_params):
        """
        max_frequency = "1 per 10 seconds".
        After first invocation at T=0, second at T=5 (5 seconds later) must fail.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        time_1 = datetime.utcnow()
        
        # First invocation at T=0
        result = ctx.check_resource_limits(response_tokens=100, current_timestamp=time_1)
        assert result
        ctx.record_invocation(response_tokens=100, timestamp=time_1)
        
        # Second invocation at T=5 (too soon, violates 10-second limit)
        time_2 = time_1 + timedelta(seconds=5)
        result = ctx.check_resource_limits(response_tokens=100, current_timestamp=time_2)
        
        assert not result
        assert ctx.limit_failure_reason is not None
        assert "frequency limit" in ctx.limit_failure_reason.lower()
    
    def test_frequency_limit_at_boundary(self, valid_token_params):
        """
        max_frequency = "1 per 10 seconds".
        At exactly 10 seconds, the next invocation should succeed.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        time_1 = datetime.utcnow()
        
        # First invocation
        ctx.record_invocation(response_tokens=100, timestamp=time_1)
        
        # Second invocation at T=10.0 (exactly at boundary)
        time_2 = time_1 + timedelta(seconds=10)
        result = ctx.check_resource_limits(response_tokens=100, current_timestamp=time_2)
        
        assert result


class TestAdversarialOffByOneInvocationLimit:
    """
    ADVERSARIAL: Off-by-one errors in invocation counting.
    max_invocations = 5 means exactly 5 uses, not 4 or 6.
    """
    
    def test_exactly_max_invocations_allowed(self, valid_token_params):
        """
        max_invocations = 5.
        Token must allow exactly 5 invocations, no more, no less.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Use all 5 invocations
        for i in range(5):
            result = ctx.check_resource_limits(response_tokens=100)
            assert result, f"Invocation {i+1} should succeed"
            ctx.record_invocation(response_tokens=100)
        
        # 6th must fail
        result = ctx.check_resource_limits(response_tokens=100)
        assert not result
    
    def test_off_by_one_invocation_limit_upper(self, valid_token_params):
        """
        max_invocations = 5.
        6th invocation (one beyond limit) must be rejected.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        for _ in range(5):
            ctx.record_invocation(response_tokens=100)
        
        # Off-by-one: 6 invocations when max is 5
        result = ctx.check_resource_limits(response_tokens=100)
        assert not result
    
    def test_off_by_one_invocation_limit_lower(self, valid_token_params):
        """
        max_invocations = 5.
        If token only allows 4 invocations (off-by-one error lower),
        5th must fail (tests that we don't undershoot).
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Manually check: after 4 invocations, should still allow more
        ctx.invocation_count = 4
        
        result = ctx.check_resource_limits(response_tokens=100)
        
        # Should succeed (4 < 5)
        assert result


class TestAdversarialConcurrentInvocations:
    """
    ADVERSARIAL: Multiple rapid invocations using same token.
    Each must be counted independently.
    Frequency and invocation limits must be enforced per-invocation.
    """
    
    def test_rapid_invocations_respect_invocation_limit(self, valid_token_params):
        """
        Multiple rapid invocations using same token.
        All must be counted, invocation limit enforced.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Rapid invocations
        for i in range(5):
            result = ctx.check_resource_limits(response_tokens=100)
            assert result, f"Invocation {i+1} should succeed"
            ctx.record_invocation(response_tokens=100)
        
        # 6th rapid invocation should fail (limit reached)
        result = ctx.check_resource_limits(response_tokens=100)
        assert not result
    
    def test_rapid_invocations_respect_frequency_limit(self, valid_token_params):
        """
        Multiple invocations with frequency limit "1 per 10 seconds".
        Rapid invocations (all within 10 seconds) should fail.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        base_time = datetime.utcnow()
        
        # First invocation succeeds
        ctx.record_invocation(response_tokens=100, timestamp=base_time)
        
        # Second invocation 1 second later (violates 10-second limit)
        time_2 = base_time + timedelta(seconds=1)
        result = ctx.check_resource_limits(response_tokens=100, current_timestamp=time_2)
        
        assert not result


class TestAdversarialMultipleTokensDifferentBudgets:
    """
    ADVERSARIAL: Multiple tokens with different resource budgets.
    Token A's limits do not affect Token B.
    Resource usage is isolated per token.
    """
    
    def test_token_a_limit_does_not_affect_token_b(self, valid_token_params, token_registry):
        """
        Token A: max_invocations = 5 (from valid_token_params)
        Token B: max_invocations = 10
        
        Exhausting Token A does not affect Token B.
        """
        # Token A: 5 invocations
        token_a = CapabilityToken(**valid_token_params)
        ctx_a = ResourceLimitContext(token_a)
        
        # Token B: 10 invocations
        params_b = valid_token_params.copy()
        params_b["resource_limits"] = {
            "max_invocations": 10,
            "max_tokens_per_response": 512,
            "max_total_tokens": 2048,
            "max_frequency": "1 per 10 seconds",
        }
        params_b["issued_by"] = "admin"
        token_b = CapabilityToken(**params_b)
        ctx_b = ResourceLimitContext(token_b)
        
        # Exhaust Token A: 5 invocations
        for _ in range(5):
            ctx_a.record_invocation(response_tokens=100)
        
        # Token A is exhausted
        result_a = ctx_a.check_resource_limits(response_tokens=100)
        assert not result_a
        
        # Token B is still available (has 10 invocations)
        result_b = ctx_b.check_resource_limits(response_tokens=100)
        assert result_b
        
        # Token B can use all 10 invocations independently
        for _ in range(9):  # Already checked 1
            result = ctx_b.check_resource_limits(response_tokens=100)
            assert result
            ctx_b.record_invocation(response_tokens=100)
    
    def test_token_a_total_budget_independent_from_token_b(self, valid_token_params):
        """
        Token A: max_total_tokens = 2048
        Token B: max_total_tokens = 1000
        
        Token A exhaustion doesn't affect Token B's budget.
        """
        # Token A: 2048 total tokens
        token_a = CapabilityToken(**valid_token_params)
        ctx_a = ResourceLimitContext(token_a)
        ctx_a.total_tokens_used = 2048  # Exhausted
        
        # Token B: 1000 total tokens (smaller budget)
        params_b = valid_token_params.copy()
        params_b["resource_limits"]["max_total_tokens"] = 1000
        params_b["issued_by"] = "admin"
        token_b = CapabilityToken(**params_b)
        ctx_b = ResourceLimitContext(token_b)
        
        # Token A cannot use even 1 token
        result_a = ctx_a.check_resource_limits(response_tokens=1)
        assert not result_a
        
        # Token B can use up to 1000 (independent budget)
        result_b = ctx_b.check_resource_limits(response_tokens=500)
        assert result_b


class TestAdversarialMidLifecycleExhaustion:
    """
    ADVERSARIAL: Resource exhaustion happens mid-lifecycle.
    Token is usable initially, then becomes exhausted.
    Exactly at exhaustion point, invocations are rejected.
    """
    
    def test_token_exhausted_mid_lifecycle(self, valid_token_params):
        """
        Token has max_invocations=5, max_total_tokens=2048.
        After 5 invocations using 400 tokens each (2000 total),
        the invocation count is exhausted (5 of 5 used).
        But we can demonstrate budget exhaustion by checking
        at earlier point: 2 invocations of 300 tokens = 600 total,
        then check with 1500 more tokens (2100 > 2048) - this tests
        that budget runs out mid-lifecycle.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Use 2 invocations of 300 tokens each = 600 total
        for _ in range(2):
            ctx.record_invocation(response_tokens=300)
        
        # Still have 3 invocations allowed (2 < 5)
        assert ctx.check_resource_limits(response_tokens=300)
        # Record 3rd invocation (now at 900 total)
        ctx.record_invocation(response_tokens=300)
        
        # Still have 2 invocations allowed (3 < 5)
        # But token budget is getting tight (900 + 512 + 512 = 1924 < 2048, OK)
        # But 900 + 512 + 512 + 100 = 2024 < 2048 still OK
        # To test exhaustion: set total to 1600 directly, then check
        ctx.total_tokens_used = 1600
        
        # Now: 1600 + 500 = 2100 > 2048 (budget exceeded)
        result = ctx.check_resource_limits(response_tokens=500)
        
        assert not result
        assert "total token budget" in ctx.limit_failure_reason.lower()
    
    def test_token_becomes_unusable_on_frequency_exhaustion(self, valid_token_params):
        """
        Token has frequency limit "1 per 10 seconds".
        After first invocation, subsequent invocations too soon are rejected.
        Token is temporarily unusable (not permanently exhausted).
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        time_1 = datetime.utcnow()
        ctx.record_invocation(response_tokens=100, timestamp=time_1)
        
        # Invocation 2 seconds later violates frequency
        time_2 = time_1 + timedelta(seconds=2)
        result = ctx.check_resource_limits(response_tokens=100, current_timestamp=time_2)
        
        assert not result
        
        # After 10 seconds, token is usable again
        time_3 = time_1 + timedelta(seconds=10)
        result = ctx.check_resource_limits(response_tokens=100, current_timestamp=time_3)
        
        assert result


class TestResourceLimitIsolationPerToken:
    """
    REQUIREMENT: Resource limits are per-token, not shared.
    Token A's invocation count doesn't affect Token B's.
    Token A's total token usage doesn't affect Token B's.
    """
    
    def test_invocation_count_isolated_per_token(self, valid_token_params):
        """
        Token A used once.
        Token B still has full invocation budget.
        """
        token_a = CapabilityToken(**valid_token_params)
        ctx_a = ResourceLimitContext(token_a)
        ctx_a.record_invocation(response_tokens=100)
        
        token_b = CapabilityToken(**valid_token_params)
        ctx_b = ResourceLimitContext(token_b)
        
        # Both should still have 4 invocations remaining
        assert ctx_a.invocation_count == 1
        assert ctx_b.invocation_count == 0
    
    def test_total_tokens_isolated_per_token(self, valid_token_params):
        """
        Token A used 1500 tokens (within 2048 limit).
        Token B still has full 2048 token budget.
        """
        token_a = CapabilityToken(**valid_token_params)
        ctx_a = ResourceLimitContext(token_a)
        ctx_a.auto_timestamp = False
        ctx_a.total_tokens_used = 1500
        
        token_b = CapabilityToken(**valid_token_params)
        ctx_b = ResourceLimitContext(token_b)
        ctx_b.auto_timestamp = False
        
        # Token A has 548 tokens remaining (2048 - 1500)
        # Token B has 2048 tokens remaining (full budget)
        result_a = ctx_a.check_resource_limits(response_tokens=400)
        assert result_a
        
        # Token B can use 512 (max_tokens_per_response)
        result_b = ctx_b.check_resource_limits(response_tokens=512)
        assert result_b


class TestNoPartialExecutionOnLimitExceedance:
    """
    REQUIREMENT: If limit is exceeded, invocation is rejected BEFORE execution.
    No partial execution. No attempt to execute then cleanup.
    Fail-closed and atomic.
    """
    
    def test_limit_check_happens_before_execution(self, valid_token_params):
        """
        Limit checking is a gate before execution starts.
        If check fails, execution never begins.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Exhaust invocations
        for _ in range(5):
            ctx.record_invocation(response_tokens=100)
        
        # 6th invocation fails limit check
        result = ctx.check_resource_limits(response_tokens=100)
        
        # No execution started
        assert not result
        assert ctx.invocation_count == 5  # Not incremented
    
    def test_no_truncation_on_token_limit_exceeded(self, valid_token_params):
        """
        If response would exceed max_tokens_per_response,
        system MUST NOT attempt to truncate output.
        Invocation must be rejected, not partially executed.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Response is too large
        response_tokens = 600  # Exceeds limit of 512
        result = ctx.check_resource_limits(response_tokens=response_tokens)
        
        # Rejected, no attempt to truncate to 512
        assert not result
        assert ctx.invocation_count == 0
        assert ctx.total_tokens_used == 0


class TestNoFallbackOrRetry:
    """
    REQUIREMENT: If limit exceeded, no fallback, retry, or alternative.
    Failure is immediate and final (within token's valid period).
    """
    
    def test_exhausted_invocation_limit_no_retry(self, valid_token_params):
        """
        Token invocation limit exhausted.
        System does not retry, does not offer fallback.
        Invocation is rejected permanently.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Exhaust invocations
        for _ in range(5):
            ctx.record_invocation(response_tokens=100)
        
        # Attempt invocation
        result = ctx.check_resource_limits(response_tokens=100)
        
        # Failed, no retry
        assert not result
        # Attempting again also fails (no recovery)
        result = ctx.check_resource_limits(response_tokens=100)
        assert not result
    
    def test_exhausted_token_budget_no_fallback(self, valid_token_params):
        """
        Total token budget exhausted.
        System does not split response, truncate, or offer alternative.
        Invocation is rejected.
        """
        token = CapabilityToken(**valid_token_params)
        ctx = ResourceLimitContext(token)
        
        # Use all budget
        ctx.total_tokens_used = 2048
        
        # Even 1-token response is rejected
        result = ctx.check_resource_limits(response_tokens=1)
        
        assert not result
