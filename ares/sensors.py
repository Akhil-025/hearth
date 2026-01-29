# ARES — Active Defense & Deterrence
# Phase 0: Detection, Deception, Reporting
# No execution authority
# No persistence
# No autonomy
# Reports to Artemis only

"""
Passive observation hooks for ARES.

Sensors:
- Detect boundary probing
- Detect invalid plan attempts
- Detect policy rejections
- Detect timing anomalies
- Detect capability enumeration

Does:
- Observe passively
- Emit signals
- Record events

Does NOT:
- Block operations
- Execute
- Persist
- Modify plans
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Any
from enum import Enum

from .signals import Signal, SignalType, ConfidenceLevel


class SensorEventType(Enum):
    """Types of events observed by sensors."""
    BOUNDARY_ACCESS_ATTEMPT = "boundary_access_attempt"
    INVALID_PLAN_SUBMITTED = "invalid_plan_submitted"
    PLAN_REJECTED = "plan_rejected"
    TIMING_ANOMALY = "timing_anomaly"
    CAPABILITY_QUERY = "capability_query"
    REPEATED_FAILURE = "repeated_failure"


@dataclass(frozen=True)
class SensorEvent:
    """
    Immutable sensor observation.
    
    Does:
    - Records passive observation
    - Captures source and context
    
    Does NOT:
    - Execute
    - Block
    - Persist
    """
    
    event_id: str
    event_type: SensorEventType
    timestamp: datetime
    source: str  # subsystem that generated event
    description: str
    context: dict  # Additional context (frozen)
    
    @staticmethod
    def create(
        event_type: SensorEventType,
        source: str,
        description: str,
        context: dict = None,
    ) -> "SensorEvent":
        """
        Create sensor event.
        
        Does:
        - Records observation with timestamp
        - Freezes context
        
        Does NOT:
        - Execute
        - Persist
        - Block
        """
        import hashlib
        
        timestamp = datetime.utcnow()
        id_str = f"{event_type.value}_{source}_{timestamp.isoformat()}_{description[:20]}"
        event_id = f"evt-{hashlib.sha256(id_str.encode()).hexdigest()[:12]}"
        
        return SensorEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            source=source,
            description=description,
            context=dict(context) if context else {},
        )


class PassiveSensor:
    """
    Base class for passive sensors.
    
    Does:
    - Observe passively
    - Emit signals
    - Record events
    
    Does NOT:
    - Block
    - Execute
    - Persist
    - Modify plans
    """
    
    def __init__(self, name: str):
        """Initialize sensor (does NOT execute on import)."""
        self.name = name
    
    def observe_boundary_probing(
        self,
        subsystem: str,
        attempt_count: int,
        description: str,
    ) -> Optional[Signal]:
        """
        Observe excessive boundary access attempts.
        
        Does:
        - Detects pattern of boundary probing
        - Creates signal if threshold exceeded
        - Returns signal (or None if below threshold)
        
        Does NOT:
        - Block
        - Execute
        - Persist
        - Modify subsystem
        """
        if attempt_count >= 5:
            return Signal.create(
                signal_type=SignalType.EXCESSIVE_PROBING,
                source_subsystem=subsystem,
                confidence=ConfidenceLevel.MEDIUM,
                description=f"Boundary probing detected: {description}",
                evidence_reference=f"boundary_access_{subsystem}",
                context=f"Attempt count: {attempt_count}",
            )
        return None
    
    def observe_invalid_plan_attempts(
        self,
        plan_count: int,
        time_window_sec: int,
        description: str,
    ) -> Optional[Signal]:
        """
        Observe repeated invalid plan submissions.
        
        Does:
        - Detects pattern of invalid plans
        - Creates signal if threshold exceeded
        
        Does NOT:
        - Block plan submission
        - Execute
        - Persist
        - Modify plans
        """
        if plan_count >= 3:
            return Signal.create(
                signal_type=SignalType.INVALID_PLAN_ATTEMPTS,
                source_subsystem="plan_executor",
                confidence=ConfidenceLevel.MEDIUM,
                description=f"Invalid plan pattern: {description}",
                evidence_reference=f"plan_submissions_{time_window_sec}s",
                context=f"Invalid submissions in {time_window_sec}s: {plan_count}",
            )
        return None
    
    def observe_rapid_rejections(
        self,
        rejection_count: int,
        time_window_sec: int,
        policy: str,
    ) -> Optional[Signal]:
        """
        Observe rapid policy rejections.
        
        Does:
        - Detects pattern of rapid rejections
        - Creates signal if threshold exceeded
        
        Does NOT:
        - Block rejection
        - Override policy
        - Persist
        - Execute
        """
        if rejection_count >= 5:
            return Signal.create(
                signal_type=SignalType.RAPID_REJECTIONS,
                source_subsystem="policy_engine",
                confidence=ConfidenceLevel.MEDIUM,
                description=f"Rapid rejections by policy: {policy}",
                evidence_reference=f"rejections_{policy}_{time_window_sec}s",
                context=f"Rejections in {time_window_sec}s: {rejection_count}",
            )
        return None
    
    def observe_timing_anomaly(
        self,
        expected_duration_ms: int,
        actual_duration_ms: int,
        operation: str,
    ) -> Optional[Signal]:
        """
        Observe suspicious timing patterns.
        
        Does:
        - Detects timing deviations
        - Creates signal if anomalous
        
        Does NOT:
        - Block operation
        - Modify timing
        - Persist
        - Execute
        """
        ratio = actual_duration_ms / max(expected_duration_ms, 1)
        
        # Significant deviation: >5x slower or >10x faster
        if ratio > 5.0 or ratio < 0.1:
            return Signal.create(
                signal_type=SignalType.SUSPICIOUS_TIMING,
                source_subsystem="executor",
                confidence=ConfidenceLevel.LOW,
                description=f"Timing anomaly in {operation}",
                evidence_reference=f"timing_{operation}",
                context=f"Expected {expected_duration_ms}ms, got {actual_duration_ms}ms",
            )
        return None
    
    def observe_capability_enumeration(
        self,
        subsystem: str,
        query_count: int,
        unique_capabilities: int,
    ) -> Optional[Signal]:
        """
        Observe capability enumeration attempts.
        
        Does:
        - Detects pattern of capability queries
        - Creates signal if suspicious
        
        Does NOT:
        - Block queries
        - Modify capabilities
        - Persist
        - Execute
        """
        if query_count >= 10 and unique_capabilities >= 5:
            return Signal.create(
                signal_type=SignalType.CAPABILITY_ENUMERATION,
                source_subsystem=subsystem,
                confidence=ConfidenceLevel.MEDIUM,
                description="Capability enumeration pattern detected",
                evidence_reference=f"enum_{subsystem}",
                context=f"Queries: {query_count}, Unique: {unique_capabilities}",
            )
        return None
    
    def observe_credential_scan(
        self,
        attempt_count: int,
        description: str,
    ) -> Optional[Signal]:
        """
        Observe credential scanning attempts.
        
        Does:
        - Detects pattern of credential queries
        - Creates signal if suspicious
        
        Does NOT:
        - Block access
        - Leak credentials
        - Persist
        - Execute
        """
        if attempt_count >= 5:
            return Signal.create(
                signal_type=SignalType.CREDENTIAL_SCAN,
                source_subsystem="auth",
                confidence=ConfidenceLevel.HIGH,
                description=f"Credential scan detected: {description}",
                evidence_reference="credential_access_pattern",
                context=f"Attempts: {attempt_count}",
            )
        return None


# Global sensor instance (singleton, does NOT execute on import)
_sensor = None


def get_sensor(name: str = "default") -> PassiveSensor:
    """
    Get passive sensor instance.
    
    Does:
    - Returns sensor (creates if needed)
    
    Does NOT:
    - Execute
    - Persist
    - Side effects on import
    """
    global _sensor
    if _sensor is None:
        _sensor = PassiveSensor(name)
    return _sensor
