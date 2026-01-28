"""
PHASE 4B: Required Audit Events & Completeness Tests

This phase proves that all 12 mandatory audit events are recorded with complete information:
1. TOKEN_ISSUED - Token creation with capabilities
2. TOKEN_FIRST_USED - First usage of a token
3. TOKEN_VALIDATION - Pass/fail validation with reason
4. AUTHORIZATION_SCOPE_CHECK - Domain/method authorization pass/fail
5. RESOURCE_LIMIT_CHECK - Invocation/token/frequency limit pass/fail
6. EXECUTION_STARTED - Execution begins
7. EXECUTION_COMPLETED - Execution finishes (success/failure)
8. EXECUTION_DENIED - Operation rejected (with denial reason)
9. TOKEN_REVOKED - Token revocation recorded
10. TOKEN_EXPIRED - Token expiration recorded
11. BOUNDARY_VIOLATION - Stage-3 boundary violation attempt
12. OPERATION_ABORTED - Operation halted (audit failure, etc.)

Every event is append-only, chronologically ordered, and causally consistent.
Missing required events = execution invalid (fail-closed).
"""

import pytest
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum


class AuditEventType(Enum):
    """Enumeration of all required audit event types."""
    TOKEN_ISSUED = "TOKEN_ISSUED"
    TOKEN_FIRST_USED = "TOKEN_FIRST_USED"
    TOKEN_VALIDATION = "TOKEN_VALIDATION"
    AUTHORIZATION_SCOPE_CHECK = "AUTHORIZATION_SCOPE_CHECK"
    RESOURCE_LIMIT_CHECK = "RESOURCE_LIMIT_CHECK"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    EXECUTION_DENIED = "EXECUTION_DENIED"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    BOUNDARY_VIOLATION = "BOUNDARY_VIOLATION"
    OPERATION_ABORTED = "OPERATION_ABORTED"


class AuditEvent:
    """Immutable audit event with all required fields."""
    
    def __init__(
        self,
        event_type: AuditEventType,
        timestamp: datetime,
        user_id: str,
        token_hash: str,
        domain: str,
        method: str,
        status: str,  # "success", "denied", "failed"
        reason: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        """Create immutable audit event.
        
        Required fields:
        - event_type: One of 12 mandatory event types
        - timestamp: When event occurred
        - user_id: Who performed the operation
        - token_hash: Which token (never raw token)
        - domain: Target domain (for scope/execution events)
        - method: Target method (for scope/execution events)
        - status: success, denied, failed, etc.
        - reason: Why operation was denied/failed (required for denials)
        - additional_data: Event-specific context
        """
        self.event_type = event_type
        self.timestamp = timestamp
        self.user_id = user_id
        self.token_hash = token_hash
        self.domain = domain
        self.method = method
        self.status = status
        self.reason = reason
        self.additional_data = additional_data if additional_data else {}
        self._frozen = True
    
    def __setattr__(self, name, value):
        """Prevent modification after creation."""
        if hasattr(self, '_frozen') and self._frozen:
            raise AttributeError(f"Cannot modify frozen event: {name}")
        super().__setattr__(name, value)
    
    def has_required_fields(self) -> bool:
        """Verify event has all required fields."""
        required = {
            "event_type": self.event_type is not None,
            "timestamp": self.timestamp is not None,
            "user_id": self.user_id is not None and len(self.user_id) > 0,
            "token_hash": self.token_hash is not None and len(self.token_hash) > 0,
            "domain": self.domain is not None and len(self.domain) > 0,
            "method": self.method is not None and len(self.method) > 0,
            "status": self.status is not None and len(self.status) > 0,
        }
        return all(required.values())
    
    def has_required_reason_if_denied(self) -> bool:
        """Verify event has reason if status is denied."""
        if self.status == "denied":
            return self.reason is not None and len(self.reason) > 0
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Export event as dict (immutable copy)."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "token_hash": self.token_hash,
            "domain": self.domain,
            "method": self.method,
            "status": self.status,
            "reason": self.reason,
            "additional_data": dict(self.additional_data),
        }


class AuditEventLog:
    """Append-only event log that tracks all 12 mandatory event types."""
    
    def __init__(self):
        self.events: List[AuditEvent] = []
        self.event_types_recorded: set = set()
        self.required_event_types = {e.value for e in AuditEventType}
    
    def append(self, event: AuditEvent) -> bool:
        """Append event to log. Returns False if invalid (fail-closed)."""
        # Verify event is valid
        if not isinstance(event, AuditEvent):
            return False
        
        # Verify event has all required fields
        if not event.has_required_fields():
            return False
        
        # Verify denied events have reason
        if not event.has_required_reason_if_denied():
            return False
        
        # Append event
        self.events.append(event)
        self.event_types_recorded.add(event.event_type.value)
        return True
    
    def get_events(self) -> List[AuditEvent]:
        """Return immutable copy of all events."""
        import copy
        return copy.deepcopy(self.events)
    
    def get_events_by_type(self, event_type: str) -> List[AuditEvent]:
        """Get all events of a specific type."""
        import copy
        return copy.deepcopy([e for e in self.events if e.event_type.value == event_type])
    
    def verify_chronological_order(self) -> bool:
        """Verify events are in chronological order."""
        for i in range(1, len(self.events)):
            if self.events[i].timestamp < self.events[i-1].timestamp:
                return False
        return True
    
    def verify_causal_consistency(self) -> bool:
        """Verify causal ordering: validation → auth → execution."""
        event_types = [e.event_type.value for e in self.events]
        
        # Find indices of key events
        validation_idx = None
        auth_idx = None
        execution_idx = None
        
        for i, et in enumerate(event_types):
            if "TOKEN_VALIDATION" in et and validation_idx is None:
                validation_idx = i
            if "AUTHORIZATION_SCOPE_CHECK" in et and auth_idx is None:
                auth_idx = i
            if "EXECUTION_STARTED" in et and execution_idx is None:
                execution_idx = i
        
        # If all present, verify order (validation must come before auth, auth before execution)
        if validation_idx is not None and auth_idx is not None:
            if validation_idx > auth_idx:
                return False
        if auth_idx is not None and execution_idx is not None:
            if auth_idx > execution_idx:
                return False
        
        return True
    
    def verify_all_mandatory_events_present(self) -> bool:
        """Fail-closed: verify all 12 mandatory event types are recorded."""
        return self.required_event_types.issubset(self.event_types_recorded)
    
    def get_missing_mandatory_events(self) -> set:
        """Return set of missing mandatory event types."""
        return self.required_event_types - self.event_types_recorded


# ============================================================================
# TEST CLASSES
# ============================================================================


class TestTokenIssuedEvent:
    """TOKEN_ISSUED event is recorded when token is created."""
    
    def test_token_issued_event_is_recorded(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_ISSUED,
            timestamp=datetime.now(),
            user_id="admin_user",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="success",
            additional_data={"capabilities": ["analyze", "report"]},
        )
        
        result = log.append(event)
        assert result is True
        assert len(log.get_events_by_type("TOKEN_ISSUED")) == 1
    
    def test_token_issued_event_has_all_required_fields(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_ISSUED,
            timestamp=datetime.now(),
            user_id="admin_user",
            token_hash="token_abc123",
            domain="system",
            method="issue_token",
            status="success",
        )
        
        assert event.has_required_fields() is True
        result = log.append(event)
        assert result is True
    
    def test_token_issued_records_capabilities(self):
        log = AuditEventLog()
        
        capabilities = {"domains": ["apolloo", "hephaestus"], "methods": {"apolloo": ["analyze", "report"]}}
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_ISSUED,
            timestamp=datetime.now(),
            user_id="admin_user",
            token_hash="token_abc123",
            domain="system",
            method="issue_token",
            status="success",
            additional_data={"capabilities": capabilities},
        )
        
        log.append(event)
        recorded_event = log.get_events_by_type("TOKEN_ISSUED")[0]
        assert recorded_event.additional_data["capabilities"] == capabilities


class TestTokenFirstUsedEvent:
    """TOKEN_FIRST_USED event is recorded when token is first used."""
    
    def test_token_first_used_event_is_recorded(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_FIRST_USED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="success",
        )
        
        result = log.append(event)
        assert result is True
        assert len(log.get_events_by_type("TOKEN_FIRST_USED")) == 1
    
    def test_token_first_used_captures_domain_and_method(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_FIRST_USED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="hephaestus",
            method="design",
            status="success",
        )
        
        log.append(event)
        recorded_event = log.get_events_by_type("TOKEN_FIRST_USED")[0]
        assert recorded_event.domain == "hephaestus"
        assert recorded_event.method == "design"


class TestTokenValidationEvent:
    """TOKEN_VALIDATION events record both pass and fail."""
    
    def test_token_validation_success_event(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="success",
        )
        
        result = log.append(event)
        assert result is True
        assert len(log.get_events_by_type("TOKEN_VALIDATION")) == 1
    
    def test_token_validation_failure_event(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_revoked",
            domain="apolloo",
            method="analyze",
            status="denied",
            reason="Token is revoked",
        )
        
        result = log.append(event)
        assert result is True
        assert event.has_required_reason_if_denied() is True
    
    def test_token_validation_denied_requires_reason(self):
        log = AuditEventLog()
        
        # Event without reason
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc",
            domain="apolloo",
            method="analyze",
            status="denied",
            reason=None,
        )
        
        result = log.append(event)
        assert result is False  # Fail-closed: denied without reason is invalid


class TestAuthorizationScopeCheckEvent:
    """AUTHORIZATION_SCOPE_CHECK events record both pass and fail."""
    
    def test_authorization_pass_event(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.AUTHORIZATION_SCOPE_CHECK,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="success",
        )
        
        result = log.append(event)
        assert result is True
    
    def test_authorization_denied_event(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.AUTHORIZATION_SCOPE_CHECK,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="hephaestus",
            method="escalate",
            status="denied",
            reason="Domain 'hephaestus' not in scope",
        )
        
        result = log.append(event)
        assert result is True
        assert event.reason == "Domain 'hephaestus' not in scope"
    
    def test_authorization_denied_requires_reason(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.AUTHORIZATION_SCOPE_CHECK,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="forbidden_domain",
            method="execute",
            status="denied",
            reason=None,
        )
        
        result = log.append(event)
        assert result is False  # Fail-closed


class TestResourceLimitCheckEvent:
    """RESOURCE_LIMIT_CHECK events record limit enforcement."""
    
    def test_resource_limit_passed_event(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.RESOURCE_LIMIT_CHECK,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="success",
            additional_data={"limit_type": "max_invocations", "current": 5, "max": 10},
        )
        
        result = log.append(event)
        assert result is True
    
    def test_resource_limit_exceeded_event(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.RESOURCE_LIMIT_CHECK,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="denied",
            reason="max_invocations limit exceeded (10/10)",
            additional_data={"limit_type": "max_invocations", "current": 11, "max": 10},
        )
        
        result = log.append(event)
        assert result is True
        assert "max_invocations" in event.reason
    
    def test_resource_limit_check_tracks_limit_type(self):
        log = AuditEventLog()
        
        limit_types = ["max_invocations", "max_tokens_per_response", "max_total_tokens", "max_frequency"]
        
        for limit_type in limit_types:
            event = AuditEvent(
                event_type=AuditEventType.RESOURCE_LIMIT_CHECK,
                timestamp=datetime.now() + timedelta(seconds=len(log.get_events())),
                user_id="user123",
                token_hash="token_abc123",
                domain="apolloo",
                method="analyze",
                status="success",
                additional_data={"limit_type": limit_type},
            )
            log.append(event)
        
        assert len(log.get_events_by_type("RESOURCE_LIMIT_CHECK")) == 4


class TestExecutionStartedEvent:
    """EXECUTION_STARTED event marks beginning of execution."""
    
    def test_execution_started_event_recorded(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_STARTED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="started",
        )
        
        result = log.append(event)
        assert result is True
    
    def test_execution_started_captures_domain_method(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_STARTED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="dionysus",
            method="create_prompt",
            status="started",
        )
        
        log.append(event)
        recorded_event = log.get_events_by_type("EXECUTION_STARTED")[0]
        assert recorded_event.domain == "dionysus"
        assert recorded_event.method == "create_prompt"


class TestExecutionCompletedEvent:
    """EXECUTION_COMPLETED event records success or failure."""
    
    def test_execution_completed_success(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_COMPLETED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="success",
            additional_data={"result": "Analysis complete", "duration_ms": 1234},
        )
        
        result = log.append(event)
        assert result is True
    
    def test_execution_completed_failure(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_COMPLETED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="failed",
            reason="Internal error: database connection lost",
        )
        
        result = log.append(event)
        assert result is True


class TestExecutionDeniedEvent:
    """EXECUTION_DENIED event records denied operations with reason."""
    
    def test_execution_denied_due_to_scope(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_DENIED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="forbidden",
            method="admin_method",
            status="denied",
            reason="Domain 'forbidden' not in token scope",
        )
        
        result = log.append(event)
        assert result is True
    
    def test_execution_denied_due_to_resource_limit(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_DENIED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="denied",
            reason="Invocation limit (10) exceeded",
        )
        
        result = log.append(event)
        assert result is True
    
    def test_execution_denied_requires_reason(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_DENIED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="denied",
            reason=None,
        )
        
        result = log.append(event)
        assert result is False  # Fail-closed


class TestTokenRevokedEvent:
    """TOKEN_REVOKED event records token revocation."""
    
    def test_token_revoked_event_recorded(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_REVOKED,
            timestamp=datetime.now(),
            user_id="admin_user",
            token_hash="token_abc123",
            domain="system",
            method="revoke_token",
            status="success",
            additional_data={"revoked_user": "user123", "reason": "Compromised"},
        )
        
        result = log.append(event)
        assert result is True
    
    def test_token_revoked_captures_revocation_reason(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_REVOKED,
            timestamp=datetime.now(),
            user_id="admin_user",
            token_hash="token_abc123",
            domain="system",
            method="revoke_token",
            status="success",
            additional_data={"reason": "User suspended"},
        )
        
        log.append(event)
        recorded_event = log.get_events_by_type("TOKEN_REVOKED")[0]
        assert recorded_event.additional_data["reason"] == "User suspended"


class TestTokenExpiredEvent:
    """TOKEN_EXPIRED event records token expiration."""
    
    def test_token_expired_event_recorded(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_EXPIRED,
            timestamp=datetime.now(),
            user_id="system",
            token_hash="token_abc123",
            domain="system",
            method="token_lifecycle",
            status="expired",
        )
        
        result = log.append(event)
        assert result is True


class TestBoundaryViolationEvent:
    """BOUNDARY_VIOLATION event records Stage-3 attempting to escape restrictions."""
    
    def test_boundary_violation_event(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.BOUNDARY_VIOLATION,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="denied",
            reason="Attempted unauthorized token operation",
            additional_data={"violation_type": "token_grant_attempt"},
        )
        
        result = log.append(event)
        assert result is True
    
    def test_boundary_violation_tracks_violation_type(self):
        log = AuditEventLog()
        
        violation_types = [
            "token_grant_attempt",
            "token_revoke_attempt",
            "audit_read_attempt",
            "thread_spawn_attempt",
        ]
        
        for vtype in violation_types:
            event = AuditEvent(
                event_type=AuditEventType.BOUNDARY_VIOLATION,
                timestamp=datetime.now() + timedelta(seconds=len(log.get_events())),
                user_id="user123",
                token_hash="token_abc123",
                domain="apolloo",
                method="analyze",
                status="denied",
                reason=f"Attempted {vtype}",
                additional_data={"violation_type": vtype},
            )
            log.append(event)
        
        assert len(log.get_events_by_type("BOUNDARY_VIOLATION")) == 4


class TestOperationAbortedEvent:
    """OPERATION_ABORTED event records execution halts due to failures."""
    
    def test_operation_aborted_due_to_audit_failure(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.OPERATION_ABORTED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="aborted",
            reason="Audit log write failed - fail-closed",
        )
        
        result = log.append(event)
        assert result is True
    
    def test_operation_aborted_due_to_validation_failure(self):
        log = AuditEventLog()
        
        event = AuditEvent(
            event_type=AuditEventType.OPERATION_ABORTED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc123",
            domain="apolloo",
            method="analyze",
            status="aborted",
            reason="Token validation failed",
        )
        
        result = log.append(event)
        assert result is True


class TestAllMandatoryEventsRequired:
    """Fail-closed: all 12 mandatory event types must be present."""
    
    def test_execution_with_all_events_is_valid(self):
        log = AuditEventLog()
        
        # Create a complete execution trace
        base_time = datetime.now()
        
        events = [
            AuditEvent(
                event_type=AuditEventType.TOKEN_ISSUED,
                timestamp=base_time,
                user_id="admin",
                token_hash="token_abc",
                domain="system",
                method="issue",
                status="success",
            ),
            AuditEvent(
                event_type=AuditEventType.TOKEN_FIRST_USED,
                timestamp=base_time + timedelta(seconds=1),
                user_id="user123",
                token_hash="token_abc",
                domain="apolloo",
                method="analyze",
                status="success",
            ),
            AuditEvent(
                event_type=AuditEventType.TOKEN_VALIDATION,
                timestamp=base_time + timedelta(seconds=2),
                user_id="user123",
                token_hash="token_abc",
                domain="apolloo",
                method="analyze",
                status="success",
            ),
            AuditEvent(
                event_type=AuditEventType.AUTHORIZATION_SCOPE_CHECK,
                timestamp=base_time + timedelta(seconds=3),
                user_id="user123",
                token_hash="token_abc",
                domain="apolloo",
                method="analyze",
                status="success",
            ),
            AuditEvent(
                event_type=AuditEventType.RESOURCE_LIMIT_CHECK,
                timestamp=base_time + timedelta(seconds=4),
                user_id="user123",
                token_hash="token_abc",
                domain="apolloo",
                method="analyze",
                status="success",
            ),
            AuditEvent(
                event_type=AuditEventType.EXECUTION_STARTED,
                timestamp=base_time + timedelta(seconds=5),
                user_id="user123",
                token_hash="token_abc",
                domain="apolloo",
                method="analyze",
                status="started",
            ),
            AuditEvent(
                event_type=AuditEventType.EXECUTION_COMPLETED,
                timestamp=base_time + timedelta(seconds=6),
                user_id="user123",
                token_hash="token_abc",
                domain="apolloo",
                method="analyze",
                status="success",
            ),
            AuditEvent(
                event_type=AuditEventType.TOKEN_REVOKED,
                timestamp=base_time + timedelta(seconds=7),
                user_id="admin",
                token_hash="token_abc",
                domain="system",
                method="revoke",
                status="success",
            ),
            AuditEvent(
                event_type=AuditEventType.TOKEN_EXPIRED,
                timestamp=base_time + timedelta(seconds=8),
                user_id="system",
                token_hash="token_abc",
                domain="system",
                method="lifecycle",
                status="expired",
            ),
            AuditEvent(
                event_type=AuditEventType.EXECUTION_DENIED,
                timestamp=base_time + timedelta(seconds=9),
                user_id="user123",
                token_hash="token_def",
                domain="forbidden",
                method="escalate",
                status="denied",
                reason="Scope violation",
            ),
            AuditEvent(
                event_type=AuditEventType.BOUNDARY_VIOLATION,
                timestamp=base_time + timedelta(seconds=10),
                user_id="user123",
                token_hash="token_abc",
                domain="apolloo",
                method="analyze",
                status="denied",
                reason="Attempted token grant",
            ),
            AuditEvent(
                event_type=AuditEventType.OPERATION_ABORTED,
                timestamp=base_time + timedelta(seconds=11),
                user_id="user123",
                token_hash="token_xyz",
                domain="dionysus",
                method="create",
                status="aborted",
                reason="Audit write failure",
            ),
        ]
        
        for event in events:
            result = log.append(event)
            assert result is True
        
        # Verify all mandatory events are present
        assert log.verify_all_mandatory_events_present() is True
        assert len(log.get_missing_mandatory_events()) == 0
    
    def test_execution_missing_events_is_invalid(self):
        log = AuditEventLog()
        
        # Only add a few events, not all 12
        events = [
            AuditEvent(
                event_type=AuditEventType.TOKEN_ISSUED,
                timestamp=datetime.now(),
                user_id="admin",
                token_hash="token_abc",
                domain="system",
                method="issue",
                status="success",
            ),
            AuditEvent(
                event_type=AuditEventType.EXECUTION_STARTED,
                timestamp=datetime.now() + timedelta(seconds=1),
                user_id="user123",
                token_hash="token_abc",
                domain="apolloo",
                method="analyze",
                status="started",
            ),
        ]
        
        for event in events:
            log.append(event)
        
        # Not all mandatory events present
        assert log.verify_all_mandatory_events_present() is False
        missing = log.get_missing_mandatory_events()
        assert len(missing) > 0


class TestEventChronologicalOrder:
    """Events must be in chronological order (append-only timestamp guarantee)."""
    
    def test_events_in_chronological_order(self):
        log = AuditEventLog()
        
        base_time = datetime.now()
        for i in range(5):
            event = AuditEvent(
                event_type=AuditEventType.TOKEN_VALIDATION,
                timestamp=base_time + timedelta(seconds=i),
                user_id="user123",
                token_hash=f"token_{i}",
                domain="apolloo",
                method="analyze",
                status="success",
            )
            log.append(event)
        
        assert log.verify_chronological_order() is True
    
    def test_out_of_order_events_detected(self):
        log = AuditEventLog()
        
        # Manually add events out of order
        base_time = datetime.now()
        
        event1 = AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=base_time,
            user_id="user123",
            token_hash="token_1",
            domain="apolloo",
            method="analyze",
            status="success",
        )
        log.append(event1)
        
        # Manually insert out-of-order event (in real system, this is prevented)
        event2 = AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=base_time - timedelta(seconds=1),
            user_id="user123",
            token_hash="token_2",
            domain="apolloo",
            method="analyze",
            status="success",
        )
        log.events.append(event2)  # Direct append, bypassing validation
        
        assert log.verify_chronological_order() is False


class TestEventCausalConsistency:
    """Events must be causally consistent: validation → auth → execution."""
    
    def test_causal_ordering_validation_before_auth(self):
        log = AuditEventLog()
        
        base_time = datetime.now()
        
        event1 = AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=base_time,
            user_id="user123",
            token_hash="token_abc",
            domain="apolloo",
            method="analyze",
            status="success",
        )
        log.append(event1)
        
        event2 = AuditEvent(
            event_type=AuditEventType.AUTHORIZATION_SCOPE_CHECK,
            timestamp=base_time + timedelta(seconds=1),
            user_id="user123",
            token_hash="token_abc",
            domain="apolloo",
            method="analyze",
            status="success",
        )
        log.append(event2)
        
        assert log.verify_causal_consistency() is True


class TestDenialEventsCompleteness:
    """Every denial must have user_id, token_hash, domain, method, reason, timestamp."""
    
    def test_denial_event_has_all_required_fields(self):
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_DENIED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc",
            domain="forbidden_domain",
            method="escalate",
            status="denied",
            reason="Insufficient privileges",
        )
        
        assert event.user_id == "user123"
        assert event.token_hash == "token_abc"
        assert event.domain == "forbidden_domain"
        assert event.method == "escalate"
        assert event.reason == "Insufficient privileges"
        assert event.timestamp is not None
        assert event.has_required_fields() is True
        assert event.has_required_reason_if_denied() is True
    
    def test_denial_without_reason_is_invalid(self):
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_DENIED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc",
            domain="forbidden_domain",
            method="escalate",
            status="denied",
            reason=None,
        )
        
        assert event.has_required_reason_if_denied() is False
    
    def test_denial_with_empty_reason_is_invalid(self):
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_DENIED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc",
            domain="forbidden_domain",
            method="escalate",
            status="denied",
            reason="",
        )
        
        assert event.has_required_reason_if_denied() is False


class TestEventImmutability:
    """Events cannot be modified after creation."""
    
    def test_event_cannot_be_modified(self):
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc",
            domain="apolloo",
            method="analyze",
            status="denied",
            reason="Original reason",
        )
        
        with pytest.raises(AttributeError):
            event.status = "success"
    
    def test_event_reason_cannot_be_changed(self):
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_DENIED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc",
            domain="forbidden",
            method="escalate",
            status="denied",
            reason="Scope violation",
        )
        
        with pytest.raises(AttributeError):
            event.reason = "Different reason"


class TestAdversarialAuditBypass:
    """Adversarial tests: cannot skip, batch, or falsify audit events."""
    
    def test_cannot_skip_required_event_type(self):
        log = AuditEventLog()
        
        # Try to execute without recording a TOKEN_VALIDATION event
        # This should be detected as invalid
        
        # Only record execution without validation
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_STARTED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc",
            domain="apolloo",
            method="analyze",
            status="started",
        )
        log.append(event)
        
        # Missing events
        missing = log.get_missing_mandatory_events()
        assert len(missing) > 0
    
    def test_cannot_batch_events_into_single_entry(self):
        """Cannot combine multiple logical events into one audit entry."""
        log = AuditEventLog()
        
        # Incorrect: batching multiple events
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc",
            domain="apolloo",
            method="analyze",
            status="success",
            additional_data={"also_done": ["AUTHORIZATION_SCOPE_CHECK", "EXECUTION_STARTED"]},
        )
        log.append(event)
        
        # Only TOKEN_VALIDATION is recorded, not the others
        assert len(log.get_events_by_type("TOKEN_VALIDATION")) == 1
        assert len(log.get_events_by_type("AUTHORIZATION_SCOPE_CHECK")) == 0
        assert len(log.get_events_by_type("EXECUTION_STARTED")) == 0
    
    def test_cannot_falsify_event_status(self):
        """Cannot record false success when actual failure occurred."""
        log = AuditEventLog()
        
        # Correct: record actual denial
        event = AuditEvent(
            event_type=AuditEventType.TOKEN_VALIDATION,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_revoked",
            domain="apolloo",
            method="analyze",
            status="denied",
            reason="Token is revoked",
        )
        
        result = log.append(event)
        assert result is True
        assert event.status == "denied"
        
        # Event's status cannot be changed after creation
        with pytest.raises(AttributeError):
            event.status = "success"
    
    def test_cannot_log_partial_information_on_denial(self):
        """Every denial must be logged with complete context."""
        log = AuditEventLog()
        
        # Incorrect: denial without reason
        event = AuditEvent(
            event_type=AuditEventType.EXECUTION_DENIED,
            timestamp=datetime.now(),
            user_id="user123",
            token_hash="token_abc",
            domain="forbidden",
            method="escalate",
            status="denied",
            reason=None,
        )
        
        result = log.append(event)
        assert result is False  # Fail-closed: rejected
    
    def test_comprehensive_audit_trail_cannot_be_bypassed(self):
        """Complete execution requires all mandatory event types."""
        log = AuditEventLog()
        
        # Simulate an execution that records only some events
        events_to_skip = ["TOKEN_FIRST_USED", "RESOURCE_LIMIT_CHECK"]
        base_time = datetime.now()
        sequence = 0
        
        for event_type in AuditEventType:
            if event_type.value in events_to_skip:
                continue  # Skip some events
            
            event = AuditEvent(
                event_type=event_type,
                timestamp=base_time + timedelta(seconds=sequence),
                user_id="user123",
                token_hash="token_abc",
                domain="apolloo",
                method="analyze",
                status="success" if event_type.value not in ["EXECUTION_DENIED", "OPERATION_ABORTED"] else "denied",
                reason="Test denial" if "denied" in event_type.value else None,
            )
            log.append(event)
            sequence += 1
        
        # Missing events are detected
        assert log.verify_all_mandatory_events_present() is False
        missing = log.get_missing_mandatory_events()
        assert "TOKEN_FIRST_USED" in missing
        assert "RESOURCE_LIMIT_CHECK" in missing
