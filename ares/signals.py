# ARES — Active Defense & Deterrence
# Phase 0: Detection, Deception, Reporting
# No execution authority
# No persistence
# No autonomy
# Reports to Artemis only

"""
Signal definitions and creation.

Signals are:
- Structured observations
- Typed and scored
- Immutable once created
- Evidence of suspicion

Does NOT:
- Execute
- Block
- Modify plans
- Persist
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from datetime import datetime
import hashlib


class SignalType(Enum):
    """Types of suspicion signals detected by ARES."""
    EXCESSIVE_PROBING = "excessive_boundary_probing"
    INVALID_PLAN_ATTEMPTS = "repeated_invalid_plan_attempts"
    RAPID_REJECTIONS = "rapid_policy_rejections"
    SUSPICIOUS_TIMING = "suspicious_timing_pattern"
    CAPABILITY_ENUMERATION = "capability_enumeration_attempt"
    CREDENTIAL_SCAN = "credential_scan_attempt"
    HONEYPOT_TRIGGER = "honeypot_trigger"
    STATE_MANIPULATION = "state_manipulation_attempt"


class ConfidenceLevel(Enum):
    """Confidence in signal validity."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Signal:
    """
    Immutable suspicion signal.
    
    Does:
    - Records observation
    - Captures evidence reference
    - Scores confidence
    - Timestamps event
    
    Does NOT:
    - Execute
    - Persist
    - Modify plans
    - Block operations
    """
    
    signal_id: str  # Unique identifier (hash-based)
    signal_type: SignalType
    timestamp: datetime
    source_subsystem: str  # e.g., "plan_executor", "capabilities", "state_manager"
    confidence: ConfidenceLevel
    description: str
    evidence_reference: str  # Path/reference to source data
    context: str = ""  # Additional context
    
    @staticmethod
    def create(
        signal_type: SignalType,
        source_subsystem: str,
        confidence: ConfidenceLevel,
        description: str,
        evidence_reference: str,
        context: str = "",
    ) -> "Signal":
        """
        Create an immutable signal.
        
        Does:
        - Constructs signal with timestamp
        - Generates unique ID
        - Returns immutable record
        
        Does NOT:
        - Execute
        - Persist
        - Block
        """
        timestamp = datetime.utcnow()
        
        # Generate deterministic ID (not a hash of secrets, just for tracking)
        id_str = f"{signal_type.value}_{source_subsystem}_{timestamp.isoformat()}_{description[:20]}"
        signal_id = f"sig-{hashlib.sha256(id_str.encode()).hexdigest()[:12]}"
        
        return Signal(
            signal_id=signal_id,
            signal_type=signal_type,
            timestamp=timestamp,
            source_subsystem=source_subsystem,
            confidence=confidence,
            description=description,
            evidence_reference=evidence_reference,
            context=context,
        )
    
    def to_dict(self) -> dict:
        """
        Serialize signal to dict (for reporting only).
        
        Does:
        - Returns immutable dict representation
        
        Does NOT:
        - Persist
        - Execute
        """
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source_subsystem": self.source_subsystem,
            "confidence": self.confidence.value,
            "description": self.description,
            "evidence_reference": self.evidence_reference,
            "context": self.context,
        }


@dataclass(frozen=True)
class SignalPattern:
    """
    Pattern of related signals (immutable).
    
    Does:
    - Groups related signals
    - Aggregates confidence
    
    Does NOT:
    - Execute
    - Persist
    - Modify plans
    """
    
    pattern_type: str  # e.g., "scan", "enumeration", "probing"
    signals: tuple  # Immutable tuple of Signal objects
    aggregated_confidence: ConfidenceLevel
    description: str
    
    @staticmethod
    def from_signals(
        pattern_type: str,
        signals: List[Signal],
        description: str,
    ) -> "SignalPattern":
        """
        Create pattern from signal list.
        
        Does:
        - Groups signals
        - Aggregates confidence (highest wins)
        
        Does NOT:
        - Execute
        - Persist
        """
        if not signals:
            agg_confidence = ConfidenceLevel.LOW
        else:
            # Aggregate confidence: highest level wins
            confidence_order = {
                ConfidenceLevel.LOW: 1,
                ConfidenceLevel.MEDIUM: 2,
                ConfidenceLevel.HIGH: 3,
            }
            max_level = max(
                confidence_order[sig.confidence]
                for sig in signals
            )
            agg_confidence = {
                1: ConfidenceLevel.LOW,
                2: ConfidenceLevel.MEDIUM,
                3: ConfidenceLevel.HIGH,
            }[max_level]
        
        return SignalPattern(
            pattern_type=pattern_type,
            signals=tuple(signals),
            aggregated_confidence=agg_confidence,
            description=description,
        )
    
    def to_dict(self) -> dict:
        """Serialize pattern to dict. Does NOT persist or execute."""
        return {
            "pattern_type": self.pattern_type,
            "signal_count": len(self.signals),
            "aggregated_confidence": self.aggregated_confidence.value,
            "description": self.description,
            "signals": [sig.to_dict() for sig in self.signals],
        }
