# ARES — Active Defense & Deterrence
# Phase 0: Detection, Deception, Reporting
# No execution authority
# No persistence
# No autonomy
# Reports to Artemis only

"""
Forensic reporting (immutable, signed).

Reports:
- Immutable
- Cryptographically signed (hash-based ID only, no key infrastructure)
- Self-contained
- Read-only
- Include signal summary, timeline, confidence, recommended escalation

Does:
- Generate forensic reports
- Sign reports (hash-based)
- Serialize to dict
- Immutable records

Does NOT:
- Persist
- Execute
- Escalate automatically
- Modify plans
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

from .signals import Signal, ConfidenceLevel, SignalPattern
from .timeline import TimelineEvent


class EscalationLevel:
    """Recommended escalation levels (advisory only)."""
    NONE = "none"
    INVESTIGATION = "investigation"
    MONITORING = "monitoring"
    URGENT = "urgent"


@dataclass(frozen=True)
class AresForensicReport:
    """
    Immutable forensic report from ARES.
    
    Does:
    - Contains findings
    - Cryptographically signed (hash-based)
    - Self-contained
    - Read-only
    
    Does NOT:
    - Persist
    - Execute
    - Escalate automatically
    - Modify plans
    """
    
    report_id: str
    timestamp: datetime
    signals_count: int
    events_count: int
    confidence_assessment: ConfidenceLevel
    signal_summary: tuple  # Immutable tuple of dicts
    timeline_summary: tuple  # Immutable tuple of dicts
    detected_patterns: tuple  # Immutable tuple of patterns
    recommended_escalation: str  # ADVISORY ONLY
    risk_factors: tuple  # Immutable tuple of strings
    report_hash: str  # Cryptographic hash (for verification)
    
    @staticmethod
    def create(
        signals: List[Signal],
        timeline_events: List[TimelineEvent],
        detected_patterns: List[SignalPattern] = None,
    ) -> "AresForensicReport":
        """
        Create forensic report.
        
        Does:
        - Generates report from signals and events
        - Cryptographically signs (hash-based)
        - Returns immutable record
        
        Does NOT:
        - Persist
        - Execute
        - Escalate
        """
        timestamp = datetime.utcnow()
        
        # Calculate overall confidence (highest signal confidence)
        if signals:
            confidence_map = {
                ConfidenceLevel.LOW: 1,
                ConfidenceLevel.MEDIUM: 2,
                ConfidenceLevel.HIGH: 3,
            }
            max_confidence_level = max(
                confidence_map[sig.confidence] for sig in signals
            )
            overall_confidence = {
                1: ConfidenceLevel.LOW,
                2: ConfidenceLevel.MEDIUM,
                3: ConfidenceLevel.HIGH,
            }[max_confidence_level]
        else:
            overall_confidence = ConfidenceLevel.LOW
        
        # Recommend escalation (advisory, not automated)
        if not signals:
            recommended_escalation = EscalationLevel.NONE
        elif overall_confidence == ConfidenceLevel.HIGH:
            recommended_escalation = EscalationLevel.URGENT
        elif overall_confidence == ConfidenceLevel.MEDIUM:
            recommended_escalation = EscalationLevel.MONITORING
        else:
            recommended_escalation = EscalationLevel.INVESTIGATION
        
        # Build risk factors
        risk_factors = []
        signal_types = set(sig.signal_type.value for sig in signals)
        if len(signal_types) > 3:
            risk_factors.append("Multiple attack vectors detected")
        if any(sig.confidence == ConfidenceLevel.HIGH for sig in signals):
            risk_factors.append("High-confidence signals present")
        if len(signals) > 10:
            risk_factors.append("Signal volume elevated")
        
        # Serialize signals and events
        signal_summary = tuple(sig.to_dict() for sig in signals)
        timeline_summary = tuple(
            {
                "event_id": evt.event_id,
                "event_type": evt.event_type,
                "timestamp": evt.timestamp.isoformat(),
                "source": evt.source,
            }
            for evt in timeline_events
        )
        
        # Serialize patterns
        pattern_list = detected_patterns if detected_patterns else []
        pattern_summary = tuple(pat.to_dict() for pat in pattern_list)
        
        # Generate report content for hashing
        report_content = f"{len(signals)}_{len(timeline_events)}_{recommended_escalation}_{len(risk_factors)}"
        report_hash = hashlib.sha256(report_content.encode()).hexdigest()
        
        # Generate report ID
        id_str = f"report_{timestamp.isoformat()}_{report_hash[:12]}"
        report_id = f"rep-{hashlib.sha256(id_str.encode()).hexdigest()[:12]}"
        
        return AresForensicReport(
            report_id=report_id,
            timestamp=timestamp,
            signals_count=len(signals),
            events_count=len(timeline_events),
            confidence_assessment=overall_confidence,
            signal_summary=signal_summary,
            timeline_summary=timeline_summary,
            detected_patterns=pattern_summary,
            recommended_escalation=recommended_escalation,
            risk_factors=tuple(risk_factors),
            report_hash=report_hash,
        )
    
    def to_dict(self) -> dict:
        """
        Serialize report to dict (read-only).
        
        Does:
        - Returns immutable dict representation
        
        Does NOT:
        - Persist
        - Execute
        """
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "signals_count": self.signals_count,
            "events_count": self.events_count,
            "confidence_assessment": self.confidence_assessment.value,
            "signal_summary": self.signal_summary,
            "timeline_summary": self.timeline_summary,
            "detected_patterns": self.detected_patterns,
            "recommended_escalation": self.recommended_escalation,
            "risk_factors": self.risk_factors,
            "report_hash": self.report_hash,
        }
    
    def verify_integrity(self) -> bool:
        """
        Verify report integrity (hash check).
        
        Does:
        - Verifies hash matches content
        
        Does NOT:
        - Persist
        - Execute
        """
        # Reconstruct content
        report_content = f"{self.signals_count}_{self.events_count}_{self.recommended_escalation}_{len(self.risk_factors)}"
        computed_hash = hashlib.sha256(report_content.encode()).hexdigest()
        
        return computed_hash == self.report_hash
