"""
HEARTH LIVE MODE GATE

# Authority transfer point
# Execution enabled only if LIVE
# Fail-closed

Controls whether ApprovalExecutor can dispatch to Stage-4.

STATES:
- DRY_RUN (default): No execution, demonstration only
- LIVE: Execution allowed with proper approval

CONSTRAINTS:
- Default = DRY_RUN (fail-closed)
- Explicit enable/disable only
- No automation
- No persistence
- Immutable audit trail
- Auto-reverts on security degradation

This is the FINAL GATE before execution.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import Enum
from datetime import datetime
from uuid import uuid4


# ============================================================================
# LIVE MODE STATE
# ============================================================================

class LiveModeState(Enum):
    """
    Live mode states.

    # Authority transfer point
    # Execution enabled only if LIVE
    # Fail-closed
    """
    DRY_RUN = "DRY_RUN"  # No execution (default, fail-closed)
    LIVE = "LIVE"        # Execution allowed


# ============================================================================
# LIVE MODE TRANSITION RECORD
# ============================================================================

@dataclass(frozen=True)
class LiveModeTransition:
    """
    Immutable record of a live mode state transition.

    # Authority transfer point
    # Execution enabled only if LIVE
    # Fail-closed
    """
    transition_id: str               # Unique ID
    timestamp: str                   # ISO 8601
    from_state: LiveModeState        # Previous state
    to_state: LiveModeState          # New state
    reason: str                      # Why transition happened
    user_identity: Optional[str]     # Who initiated (if manual)
    automatic: bool                  # Was this automatic (security revert)?
    security_state_at_transition: str  # Artemis state at time of transition


# ============================================================================
# LIVE MODE GATE
# ============================================================================

class LiveModeGate:
    """
    Control whether execution is allowed.

    # Authority transfer point
    # Execution enabled only if LIVE
    # Fail-closed

    Default state: DRY_RUN (no execution)
    Live state: LIVE (execution allowed with approval)

    CONSTRAINTS:
    - Explicit enable/disable only
    - No automation
    - No timers
    - No auto-enable
    - No persistence across restart
    - Auto-reverts on security degradation
    """

    def __init__(self, kernel: Optional[any] = None):
        """
        Initialize live mode gate.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed

        Args:
            kernel: Artemis kernel (for security state inspection)
        """
        self._state = LiveModeState.DRY_RUN  # Default: fail-closed
        self._kernel = kernel
        self._transition_history: List[LiveModeTransition] = []
        
        # Record initial state
        self._record_transition(
            from_state=LiveModeState.DRY_RUN,
            to_state=LiveModeState.DRY_RUN,
            reason="Initialization (default: DRY_RUN)",
            user_identity=None,
            automatic=True,
        )

    def get_state(self) -> LiveModeState:
        """
        Get current live mode state.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed

        Returns:
            LiveModeState (DRY_RUN or LIVE)
        """
        return self._state

    def is_live(self) -> bool:
        """
        Check if execution is allowed.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed

        Returns:
            True if LIVE, False if DRY_RUN
        """
        return self._state == LiveModeState.LIVE

    def is_dry_run(self) -> bool:
        """
        Check if in dry-run mode.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed

        Returns:
            True if DRY_RUN, False if LIVE
        """
        return self._state == LiveModeState.DRY_RUN

    def enable_live(
        self,
        reason: str,
        user_identity: str,
    ) -> Tuple[bool, str]:
        """
        Enable LIVE mode (allow execution).

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed

        Args:
            reason: Why enabling LIVE mode
            user_identity: Who is enabling it

        Returns:
            (success: bool, message: str)
        """
        # Validate inputs
        if not reason or not reason.strip():
            return False, "Reason cannot be empty"
        
        if not user_identity or not user_identity.strip():
            return False, "User identity cannot be empty"
        
        # Check if already LIVE
        if self._state == LiveModeState.LIVE:
            return False, "Already in LIVE mode"

        # Check security state
        security_state = self._get_security_state()
        if security_state in ["COMPROMISED", "LOCKDOWN"]:
            return False, f"Cannot enable LIVE mode: system is {security_state}"

        # Transition to LIVE
        self._state = LiveModeState.LIVE
        self._record_transition(
            from_state=LiveModeState.DRY_RUN,
            to_state=LiveModeState.LIVE,
            reason=reason,
            user_identity=user_identity,
            automatic=False,
        )

        return True, "LIVE mode enabled - execution now allowed"

    def disable_live(
        self,
        reason: str,
        user_identity: Optional[str] = None,
        automatic: bool = False,
    ) -> Tuple[bool, str]:
        """
        Disable LIVE mode (prevent execution).

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed

        Args:
            reason: Why disabling LIVE mode
            user_identity: Who is disabling it (if manual)
            automatic: Whether this is automatic (security revert)

        Returns:
            (success: bool, message: str)
        """
        # Check if already DRY_RUN
        if self._state == LiveModeState.DRY_RUN:
            return False, "Already in DRY_RUN mode"

        # Transition to DRY_RUN
        self._state = LiveModeState.DRY_RUN
        self._record_transition(
            from_state=LiveModeState.LIVE,
            to_state=LiveModeState.DRY_RUN,
            reason=reason,
            user_identity=user_identity,
            automatic=automatic,
        )

        return True, "DRY_RUN mode enabled - execution now blocked"

    def check_security_and_revert_if_needed(self) -> bool:
        """
        Check security state and auto-revert to DRY_RUN if compromised.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed

        Returns:
            True if reverted, False if no revert needed
        """
        if self._state != LiveModeState.LIVE:
            return False  # Already in DRY_RUN

        security_state = self._get_security_state()
        
        if security_state in ["COMPROMISED", "LOCKDOWN"]:
            # Auto-revert to DRY_RUN
            self.disable_live(
                reason=f"Automatic revert due to security state: {security_state}",
                user_identity=None,
                automatic=True,
            )
            return True

        return False

    def get_transition_history(self) -> Tuple[LiveModeTransition, ...]:
        """
        Get immutable transition history.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed

        Returns:
            Tuple of LiveModeTransition (immutable)
        """
        return tuple(self._transition_history)

    def _get_security_state(self) -> str:
        """
        Get current security state from Artemis kernel.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed

        Returns:
            Security state string (SECURE, DEGRADED, COMPROMISED, LOCKDOWN, unknown)
        """
        if not self._kernel:
            return "unknown"

        try:
            summary = self._kernel.inspect_security_state()
            if summary:
                state = getattr(summary, "state", "unknown")
                if hasattr(state, "value"):
                    return state.value
                return str(state)
        except Exception:
            pass

        return "unknown"

    def _record_transition(
        self,
        from_state: LiveModeState,
        to_state: LiveModeState,
        reason: str,
        user_identity: Optional[str],
        automatic: bool,
    ) -> None:
        """
        Record state transition.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed
        """
        transition = LiveModeTransition(
            transition_id=str(uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z",
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            user_identity=user_identity,
            automatic=automatic,
            security_state_at_transition=self._get_security_state(),
        )
        self._transition_history.append(transition)

    def to_dict(self) -> dict:
        """
        Export gate state as dictionary.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed
        """
        return {
            "state": self._state.value,
            "is_live": self.is_live(),
            "is_dry_run": self.is_dry_run(),
            "security_state": self._get_security_state(),
            "transition_count": len(self._transition_history),
            "last_transition": (
                {
                    "timestamp": self._transition_history[-1].timestamp,
                    "from": self._transition_history[-1].from_state.value,
                    "to": self._transition_history[-1].to_state.value,
                    "reason": self._transition_history[-1].reason,
                    "automatic": self._transition_history[-1].automatic,
                }
                if self._transition_history
                else None
            ),
        }

    def get_status_message(self) -> str:
        """
        Get human-readable status message.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed
        """
        if self._state == LiveModeState.LIVE:
            return "🔴 LIVE MODE - Execution is ENABLED"
        else:
            return "🟢 DRY RUN MODE - Execution is BLOCKED (safe)"


# ============================================================================
# LIVE MODE GATE VALIDATOR
# ============================================================================

class LiveModeGateValidator:
    """
    Validate live mode gate before execution.

    # Authority transfer point
    # Execution enabled only if LIVE
    # Fail-closed
    """

    @staticmethod
    def can_execute(gate: LiveModeGate) -> Tuple[bool, str]:
        """
        Check if execution is allowed.

        # Authority transfer point
        # Execution enabled only if LIVE
        # Fail-closed

        Args:
            gate: LiveModeGate instance

        Returns:
            (allowed: bool, reason: str)
        """
        if not gate:
            return False, "Execution blocked: No LiveModeGate configured"
        
        if gate.is_dry_run():
            return False, "Execution blocked: LiveModeGate is in DRY_RUN mode"

        if gate.is_live():
            # Check security state before allowing
            gate.check_security_and_revert_if_needed()
            
            if gate.is_dry_run():
                # Was reverted due to security state
                return False, "Execution blocked: LiveModeGate auto-reverted to DRY_RUN due to security degradation"

            return True, "Execution allowed: LiveModeGate is in LIVE mode"

        # Should never reach here
        return False, "Execution blocked: LiveModeGate state unknown"
