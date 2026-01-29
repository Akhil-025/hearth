"""
Artemis Security Summary - Immutable, user-visible status.

Artemis security UX
Informational only
No authority
No side effects
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SecuritySummary:
    """
    Immutable security summary for user-visible inspection.
    """
    state: str
    explanation: str
    last_transition_time: str
    execution_allowed: bool
