# ARES — Active Defense & Deterrence
# Phase 0: Detection, Deception, Reporting
# No execution authority
# No persistence
# No autonomy
# Reports to Artemis only

"""
ARES interface (single reporting interface to Artemis).

ARES exposes ONE method:

def report_to_artemis() -> AresForensicReport

ARES:
- Never calls kill switch
- Never changes security state
- Never raises system-wide exceptions
- Only reports findings

Does:
- Collects findings
- Generates forensic report
- Returns to Artemis

Does NOT:
- Execute
- Persist
- Escalate automatically
- Modify plans
"""

from typing import List, Optional

from .report import AresForensicReport
from .state import get_store, AresState
from .signals import Signal
from .timeline import get_timeline
from .profiler import get_factory as get_profiler_factory


def report_to_artemis() -> AresForensicReport:
    """
    ARES reports findings to Artemis.
    
    This is the ONLY public interface for ARES.
    
    Does:
    - Collects current signals from ephemeral store
    - Collects timeline events
    - Generates immutable forensic report
    - Returns report to Artemis
    
    Does NOT:
    - Execute anything
    - Persist data
    - Escalate automatically
    - Modify plans
    - Talk to users
    - Access network
    
    Returns:
    - AresForensicReport (immutable)
    
    Authority:
    - ONLY Artemis decides:
      - Escalation
      - Credential freeze
      - Lockdown
      - Kill switch
    """
    # Collect signals from ephemeral store
    store = get_store()
    signals_list = list(store.signals)
    
    # Collect timeline events
    timeline = get_timeline()
    timeline_events = list(timeline.events)
    
    # Get detected patterns (if any)
    profiler_factory = get_profiler_factory()
    risk_profiles = profiler_factory.get_risk_profiles()
    
    # Build detected patterns from profiler risk assessments
    detected_patterns = []
    for subsystem, (risk_score, signal) in risk_profiles.items():
        if signal:
            detected_patterns.append({
                "subsystem": subsystem,
                "risk_score": risk_score,
                "has_signal": True,
            })
    
    # Generate forensic report
    report = AresForensicReport.create(
        signals=signals_list,
        timeline_events=timeline_events,
        detected_patterns=detected_patterns,
    )
    
    return report


# Export public API
__all__ = ["report_to_artemis", "AresForensicReport"]
