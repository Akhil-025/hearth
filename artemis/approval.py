"""
Artemis Approval Governance - Security-aware approval validation.

Artemis-governed approval
Authority transfer
Fail-closed
No bypass
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, Tuple

from artemis.security_summary import SecuritySummary
from artemis.state import SecurityState


class ApprovalType(Enum):
    """Approval capability types."""
    READ_ONLY = "read_only"
    WRITE = "write"
    EXECUTION = "execution"
    SHUTDOWN = "shutdown"


# Artemis-governed approval
# Authority transfer
# Fail-closed
# No bypass
APPROVAL_CAPABILITY_MATRIX: Dict[SecurityState, FrozenSet[ApprovalType]] = {
    SecurityState.SECURE: frozenset({
        ApprovalType.READ_ONLY,
        ApprovalType.WRITE,
        ApprovalType.EXECUTION,
        ApprovalType.SHUTDOWN,
    }),
    SecurityState.DEGRADED: frozenset({
        ApprovalType.READ_ONLY,
    }),
    SecurityState.COMPROMISED: frozenset(),
    SecurityState.LOCKDOWN: frozenset({
        ApprovalType.SHUTDOWN,
    }),
}


@dataclass(frozen=True)
class ApprovalRequest:
    """
    Immutable approval request.

    Artemis-governed approval
    Authority transfer
    Fail-closed
    No bypass
    """
    requested_action: str
    risk_level: str
    required_capabilities: Tuple[ApprovalType, ...]
    security_summary: SecuritySummary


# Artemis-governed approval
# Authority transfer
# Fail-closed
# No bypass
def validate_approval_request(request: ApprovalRequest) -> tuple[bool, str]:
    """
    Validate approval request against security posture.

    Pure function: no state changes, no escalation, no side effects.
    Returns (allowed, reason).
    """
    state_name = request.security_summary.state

    try:
        state = SecurityState[state_name]
    except KeyError:
        return False, "Security posture is unknown. Approval is not allowed."

    allowed_caps = APPROVAL_CAPABILITY_MATRIX.get(state, frozenset())
    required = set(request.required_capabilities)

    if not required:
        return False, "No approval capabilities specified. Approval is not allowed."

    if not required.issubset(allowed_caps):
        if ApprovalType.EXECUTION in required:
            return False, "This action requires execution privileges. Execution is restricted under current security posture."
        if ApprovalType.WRITE in required:
            return False, "This action requires write privileges. Write approvals are restricted under current security posture."
        if ApprovalType.SHUTDOWN in required:
            return False, "Shutdown approval is restricted under current security posture."
        return False, "Approval type is restricted under current security posture."

    return True, "Approval is allowed under current security posture."
