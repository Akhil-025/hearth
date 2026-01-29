# ARES — Active Defense & Deterrence
# Phase 0: Detection, Deception, Reporting
# No execution authority
# No persistence
# No autonomy
# Reports to Artemis only

"""
Behavioral fingerprinting for ARES.

Profiler:
- Builds behavioral fingerprints
- Correlates actions across subsystems
- No identity inference
- No ML (deterministic only)

Does:
- Track action patterns
- Correlate subsystem behavior
- Emit signals
- Record profiles

Does NOT:
- Persist
- Execute
- Infer identity
- Use ML
"""

from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Tuple
from datetime import datetime
import hashlib

from .signals import Signal, SignalType, ConfidenceLevel


@dataclass(frozen=True)
class BehavioralFingerprint:
    """
    Immutable behavioral fingerprint.
    
    Does:
    - Records behavior pattern
    - Captures action signature
    
    Does NOT:
    - Infer identity
    - Persist
    - Execute
    """
    
    fingerprint_id: str
    subsystem: str
    timestamp: datetime
    action_types: frozenset  # Immutable set of action types
    frequency: Dict[str, int]  # Action counts (frozen dict)
    timing_pattern: str  # Description of timing
    risk_score: float  # 0.0-1.0
    description: str
    
    @staticmethod
    def create(
        subsystem: str,
        action_types: List[str],
        frequency: Dict[str, int],
        timing_pattern: str,
        description: str,
    ) -> "BehavioralFingerprint":
        """
        Create behavioral fingerprint.
        
        Does:
        - Records behavior pattern
        - Generates fingerprint ID
        - Computes risk score
        
        Does NOT:
        - Infer identity
        - Persist
        - Execute
        """
        timestamp = datetime.utcnow()
        
        # Generate deterministic fingerprint ID
        id_str = f"{subsystem}_{timestamp.isoformat()}_{','.join(action_types[:5])}"
        fingerprint_id = f"fp-{hashlib.sha256(id_str.encode()).hexdigest()[:12]}"
        
        # Compute risk score (simple deterministic calculation)
        action_count = sum(frequency.values())
        unique_actions = len(action_types)
        risk_score = min(1.0, action_count / 100.0 + unique_actions / 50.0)
        
        return BehavioralFingerprint(
            fingerprint_id=fingerprint_id,
            subsystem=subsystem,
            timestamp=timestamp,
            action_types=frozenset(action_types),
            frequency=dict(frequency),
            timing_pattern=timing_pattern,
            risk_score=risk_score,
            description=description,
        )


@dataclass
class BehavioralProfiler:
    """
    Behavioral profiler (tracks patterns without ML).
    
    Does:
    - Track action patterns
    - Correlate subsystem behavior
    - Emit signals
    - Record profiles
    
    Does NOT:
    - Use ML
    - Infer identity
    - Persist
    - Execute
    """
    
    subsystem: str
    actions: Dict[str, int] = field(default_factory=dict)
    correlations: Dict[str, Set[str]] = field(default_factory=dict)
    fingerprints: List[BehavioralFingerprint] = field(default_factory=list)
    
    def record_action(self, action_type: str) -> None:
        """
        Record action (does NOT persist).
        
        Does:
        - Increments action counter
        
        Does NOT:
        - Persist
        - Execute
        """
        self.actions[action_type] = self.actions.get(action_type, 0) + 1
    
    def correlate_with(self, other_subsystem: str, shared_action: str) -> None:
        """
        Correlate action with another subsystem.
        
        Does:
        - Records action correlation
        
        Does NOT:
        - Infer identity
        - Persist
        - Execute
        """
        if self.subsystem not in self.correlations:
            self.correlations[self.subsystem] = set()
        self.correlations[self.subsystem].add(
            f"{other_subsystem}:{shared_action}"
        )
    
    def fingerprint(self, timing_pattern: str) -> BehavioralFingerprint:
        """
        Generate fingerprint from recorded actions.
        
        Does:
        - Creates fingerprint from actions
        - Records in list
        
        Does NOT:
        - Infer identity
        - Persist
        - Execute
        """
        fingerprint = BehavioralFingerprint.create(
            subsystem=self.subsystem,
            action_types=list(self.actions.keys()),
            frequency=dict(self.actions),
            timing_pattern=timing_pattern,
            description=f"Profile of {self.subsystem}",
        )
        self.fingerprints.append(fingerprint)
        return fingerprint
    
    def get_risk_assessment(self) -> Tuple[float, Optional[Signal]]:
        """
        Get risk assessment from current profile.
        
        Returns:
        - (risk_score, Optional[Signal])
        
        Does:
        - Computes risk from actions
        - Emits signal if suspicious
        
        Does NOT:
        - Persist
        - Execute
        - Infer identity
        """
        action_count = sum(self.actions.values())
        unique_actions = len(self.actions)
        
        # Simple deterministic risk calculation
        risk_score = min(1.0, action_count / 100.0)
        
        signal = None
        if risk_score > 0.7:
            signal = Signal.create(
                signal_type=SignalType.STATE_MANIPULATION,
                source_subsystem=self.subsystem,
                confidence=ConfidenceLevel.MEDIUM,
                description=f"Behavioral anomaly in {self.subsystem}",
                evidence_reference=f"profile_{self.subsystem}",
                context=f"Risk score: {risk_score:.2f}",
            )
        
        return risk_score, signal


class ProfilerFactory:
    """
    Factory for creating profilers.
    
    Does:
    - Creates profiler instances
    - Tracks profilers
    
    Does NOT:
    - Execute
    - Persist
    """
    
    def __init__(self):
        """Initialize factory (does NOT execute on import)."""
        self.profilers: Dict[str, BehavioralProfiler] = {}
    
    def get_or_create_profiler(self, subsystem: str) -> BehavioralProfiler:
        """
        Get or create profiler for subsystem.
        
        Does:
        - Returns profiler (creates if needed)
        
        Does NOT:
        - Persist
        - Execute
        """
        if subsystem not in self.profilers:
            self.profilers[subsystem] = BehavioralProfiler(subsystem)
        return self.profilers[subsystem]
    
    def record_correlated_action(
        self,
        subsystem1: str,
        subsystem2: str,
        action: str,
    ) -> None:
        """
        Record correlated action between subsystems.
        
        Does:
        - Records action in both profilers
        - Creates correlation
        
        Does NOT:
        - Persist
        - Execute
        """
        prof1 = self.get_or_create_profiler(subsystem1)
        prof2 = self.get_or_create_profiler(subsystem2)
        
        prof1.record_action(action)
        prof2.record_action(action)
        
        prof1.correlate_with(subsystem2, action)
        prof2.correlate_with(subsystem1, action)
    
    def get_risk_profiles(self) -> Dict[str, Tuple[float, Optional[Signal]]]:
        """
        Get risk assessments for all profilers.
        
        Returns:
        - Dict[subsystem, (risk_score, Signal)]
        
        Does:
        - Computes risk for all
        - Emits signals if suspicious
        
        Does NOT:
        - Persist
        - Execute
        """
        results = {}
        for subsystem, profiler in self.profilers.items():
            risk_score, signal = profiler.get_risk_assessment()
            results[subsystem] = (risk_score, signal)
        return results


# Global profiler factory (does NOT execute on import)
_factory = None


def get_factory() -> ProfilerFactory:
    """
    Get profiler factory.
    
    Does:
    - Returns factory (creates if needed)
    
    Does NOT:
    - Execute
    - Persist
    """
    global _factory
    if _factory is None:
        _factory = ProfilerFactory()
    return _factory
