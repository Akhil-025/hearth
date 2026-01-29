"""
ArtemisGuardian - The core state machine for system security.

Artemis kill-path
Fail-closed
No recovery without restart
"""

import builtins
import importlib
import os
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from artemis.state import SecurityState
from artemis.boundary import LockdownPolicy, get_policy_for_state
from artemis.security_summary import SecuritySummary
from artemis.kill_switch import KillSwitch
from artemis.event_trace import EventTrace
from core.credentials import get_credential_store
from core.invariants import InvariantViolationError, FatalInvariantViolationError
from datetime import datetime

if TYPE_CHECKING:
    from artemis.integrity import IntegrityMonitor


class ArtemisGuardian:
    """
    Manages the global security state of Hearth.
    
    Rules:
    - State transitions are explicit and logged
    - Once in LOCKDOWN, no transitions are possible
    - All state changes require a reason (except returning to SECURE)
    """
    
    def __init__(self):
        """Initialize in SECURE state."""
        self._state: SecurityState = SecurityState.SECURE
        self._locked: bool = False
        self._lockdown_reason: str | None = None
        self._kill_switch = KillSwitch()
        self._integrity_monitor: Optional["IntegrityMonitor"] = None
        self._integrity_failures = 0
        self._boot_pid = os.getpid()
        self._boot_ppid = os.getppid()
        self._import_guard_installed = False
        self._process_guard_installed = False
        self._original_import = builtins.__import__
        self._original_import_module = importlib.import_module
        self._event_trace = EventTrace()
        self._last_escalation_reason: str | None = None
        self._last_transition_time: str = datetime.now().isoformat()
    
    def get_state(self) -> SecurityState:
        """Return the current security state."""
        return self._state
    
    def set_secure(self) -> None:
        """
        Return to SECURE state.
        
        Only allowed from DEGRADED state.
        Cannot recover from COMPROMISED or LOCKDOWN.
        
        Raises:
            RuntimeError: If transition is not allowed
        """
        if self._locked:
            raise RuntimeError(
                f"System is in LOCKDOWN: {self._lockdown_reason}. "
                "Restart required."
            )
        
        if self._state == SecurityState.SECURE:
            # Already secure, no-op
            return
        
        if self._state == SecurityState.DEGRADED:
            # TODO: Log transition
            self._state = SecurityState.SECURE
            self._last_escalation_reason = "Recovered to SECURE"
            self._last_transition_time = datetime.now().isoformat()
            self._record_event("security_state_transition", {
                "state": self._state.name,
                "reason": self._last_escalation_reason,
            })
            return
        
        # Cannot recover from COMPROMISED or LOCKDOWN
        raise RuntimeError(
            f"Cannot transition to SECURE from {self._state.name}. "
            "Manual intervention required."
        )
    
    def set_degraded(self, reason: str) -> None:
        """
        Transition to DEGRADED state.
        
        Args:
            reason: Explanation for degradation
        
        Raises:
            RuntimeError: If system is locked
            ValueError: If reason is empty
        """
        if self._locked:
            raise RuntimeError(
                f"System is in LOCKDOWN: {self._lockdown_reason}. "
                "Restart required."
            )
        
        if not reason or not reason.strip():
            raise ValueError("Reason for degradation must be provided")
        
        # TODO: Log transition and reason
        self._state = SecurityState.DEGRADED
        self._last_escalation_reason = reason
        self._last_transition_time = datetime.now().isoformat()
        self._record_event("security_state_transition", {
            "state": self._state.name,
            "reason": reason,
        })
    
    def set_compromised(self, reason: str) -> None:
        """
        Transition to COMPROMISED state.
        
        This is a serious security violation. System remains operational
        but requires manual intervention to recover.
        Triggers:
        - Credential freeze
        - Kill switch arm (but no termination)
        
        Args:
            reason: Explanation for compromise
        
        Raises:
            RuntimeError: If system is locked
            ValueError: If reason is empty
        """
        if self._locked:
            raise RuntimeError(
                f"System is in LOCKDOWN: {self._lockdown_reason}. "
                "Restart required."
            )
        
        if not reason or not reason.strip():
            raise ValueError("Reason for compromise must be provided")
        
        # TODO: Log transition and reason
        self._state = SecurityState.COMPROMISED
        self._last_escalation_reason = reason
        self._last_transition_time = datetime.now().isoformat()
        self._record_event("security_state_transition", {
            "state": self._state.name,
            "reason": reason,
        })
        
        # Artemis kill-path
        # Fail-closed
        # No recovery without restart
        
        # Freeze credentials immediately
        cred_store = get_credential_store()
        cred_store.freeze(self._state.name)
        
        # Arm kill switch (but don't execute - allows inspection)
        self._kill_switch.arm(reason)
    
    def lockdown(self, reason: str) -> None:
        """
        Enter LOCKDOWN state.
        
        This is irreversible without a system restart.
        All operations will be blocked.
        
        Triggers:
        - Credential freeze
        - Kill switch arm (but no termination)
        
        Args:
            reason: Explanation for lockdown
        
        Raises:
            ValueError: If reason is empty
        """
        if not reason or not reason.strip():
            raise ValueError("Reason for lockdown must be provided")
        
        # TODO: Log lockdown
        self._state = SecurityState.LOCKDOWN
        self._locked = True
        self._lockdown_reason = reason
        self._last_escalation_reason = reason
        self._last_transition_time = datetime.now().isoformat()
        self._record_event("security_state_transition", {
            "state": self._state.name,
            "reason": reason,
        })
        
        # Artemis kill-path
        # Fail-closed
        # No recovery without restart
        
        # Freeze credentials immediately
        cred_store = get_credential_store()
        cred_store.freeze(self._state.name)
        
        # Arm kill switch (but don't execute - allows inspection)
        self._kill_switch.arm(reason)
    
    def get_kill_switch(self) -> KillSwitch:
        """
        Get the kill switch instance.
        
        The kill switch is armed when entering COMPROMISED/LOCKDOWN.
        It is only triggered on explicit shutdown or integrity failure.
        
        Returns:
            The KillSwitch instance
        """
        return self._kill_switch

    def handle_boundary_error(self, error: Exception, boundary: str) -> None:
        """
        Handle a boundary error with explicit escalation.

        Artemis fault containment
        Blast radius limited
        Fail closed
        No recovery without restart
        """
        target_state = self._map_error_to_state(error)
        reason = f"{boundary} failure: {type(error).__name__}: {error}"
        self._record_event("fault_containment", {
            "boundary": boundary,
            "error_type": type(error).__name__,
        })
        self._escalate_to_state(target_state, reason)

    def _map_error_to_state(self, error: Exception) -> SecurityState:
        """
        Map error type to explicit security state.

        Escalation matrix (explicit):
        - FatalInvariantViolationError → LOCKDOWN
        - InvariantViolationError → COMPROMISED
        - PermissionError → COMPROMISED
        - RuntimeError → COMPROMISED
        - ValueError → DEGRADED
        - KeyError → DEGRADED
        - Unknown → COMPROMISED
        """
        if isinstance(error, FatalInvariantViolationError):
            return SecurityState.LOCKDOWN
        if isinstance(error, InvariantViolationError):
            return SecurityState.COMPROMISED
        if isinstance(error, PermissionError):
            return SecurityState.COMPROMISED
        if isinstance(error, RuntimeError):
            return SecurityState.COMPROMISED
        if isinstance(error, ValueError):
            return SecurityState.DEGRADED
        if isinstance(error, KeyError):
            return SecurityState.DEGRADED

        return SecurityState.COMPROMISED

    def _escalate_to_state(self, target_state: SecurityState, reason: str) -> None:
        """
        Escalate to target state without ambiguity.

        Artemis fault containment
        Blast radius limited
        Fail closed
        No recovery without restart
        """
        if self._locked:
            return

        current_rank = self._state_rank(self._state)
        target_rank = self._state_rank(target_state)

        if target_rank <= current_rank:
            return

        if target_state == SecurityState.DEGRADED:
            self.set_degraded(reason)
            return

        if target_state == SecurityState.COMPROMISED:
            self.set_compromised(reason)
            return

        if target_state == SecurityState.LOCKDOWN:
            self.lockdown(reason)

    def _state_rank(self, state: SecurityState) -> int:
        """Return monotonic rank for SecurityState comparisons."""
        ordering = [
            SecurityState.SECURE,
            SecurityState.DEGRADED,
            SecurityState.COMPROMISED,
            SecurityState.LOCKDOWN,
        ]
        return ordering.index(state)

    def install_attack_surface_reduction(self) -> None:
        """
        Install attack-surface reduction guards.

        Artemis attack-surface reduction
        Fail closed
        No recovery without restart
        """
        self._install_import_hardening()
        self._install_process_hardening()

    def assert_single_process_execution(self) -> None:
        """
        Assert the process has not forked or spawned.

        Artemis attack-surface reduction
        Fail closed
        No recovery without restart

        Raises:
            RuntimeError: If multiple processes are detected
        """
        current_pid = os.getpid()
        current_ppid = os.getppid()

        if current_pid != self._boot_pid or current_ppid != self._boot_ppid:
            self._escalate_attack_surface_violation(
                f"Process mismatch detected (pid={current_pid}, ppid={current_ppid})"
            )
            raise RuntimeError(
                "Multiple process execution detected. "
                "Artemis attack-surface reduction triggered."
            )

    def _escalate_attack_surface_violation(self, reason: str) -> None:
        """
        Escalate security state on attack-surface violations.

        Artemis attack-surface reduction
        Fail closed
        No recovery without restart
        """
        if self._locked:
            return

        if self._state == SecurityState.COMPROMISED:
            self.lockdown(reason)
            return

        if self._state in (SecurityState.SECURE, SecurityState.DEGRADED):
            self.set_compromised(reason)

    def _install_import_hardening(self) -> None:
        """
        Block dynamic import mechanisms.

        Artemis attack-surface reduction
        Fail closed
        No recovery without restart
        """
        if self._import_guard_installed:
            return

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if self._is_importlib_bootstrap_call():
                return self._original_import(name, globals, locals, fromlist, level)

            self._escalate_attack_surface_violation(
                f"Dynamic import blocked: {name}"
            )
            raise RuntimeError("Dynamic import blocked by Artemis")

        def blocked_import_module(name, package=None):
            self._escalate_attack_surface_violation(
                f"Dynamic import blocked: {name}"
            )
            raise RuntimeError("Dynamic import blocked by Artemis")

        builtins.__import__ = guarded_import
        importlib.import_module = blocked_import_module
        self._import_guard_installed = True

    def _install_process_hardening(self) -> None:
        """
        Block fork and subprocess creation.

        Artemis attack-surface reduction
        Fail closed
        No recovery without restart
        """
        if self._process_guard_installed:
            return

        def blocked_process_call(*args, **kwargs):
            self._escalate_attack_surface_violation("Subprocess creation blocked")
            raise RuntimeError("Subprocess creation blocked by Artemis")

        subprocess.Popen = blocked_process_call
        subprocess.run = blocked_process_call
        subprocess.call = blocked_process_call
        subprocess.check_call = blocked_process_call
        subprocess.check_output = blocked_process_call

        if hasattr(os, "fork"):
            def blocked_fork(*args, **kwargs):
                self._escalate_attack_surface_violation("Fork attempt blocked")
                raise RuntimeError("Fork blocked by Artemis")

            os.fork = blocked_fork

        for spawn_name in (
            "spawnl",
            "spawnle",
            "spawnlp",
            "spawnlpe",
            "spawnv",
            "spawnve",
            "spawnvp",
            "spawnvpe",
        ):
            if hasattr(os, spawn_name):
                setattr(os, spawn_name, blocked_process_call)

        self._process_guard_installed = True

    def _is_importlib_bootstrap_call(self) -> bool:
        """Allow only importlib bootstrap to use __import__ internally."""
        frame = sys._getframe(1)
        while frame:
            module_name = frame.f_globals.get("__name__", "")
            if module_name.startswith("importlib._bootstrap"):
                return True
            if module_name.startswith("importlib._bootstrap_external"):
                return True
            frame = frame.f_back
        return False

    def set_integrity_monitor(self, monitor: "IntegrityMonitor") -> None:
        """
        Set the integrity monitor instance.
        
        Called during bootstrap to wire up integrity checking.
        
        Args:
            monitor: IntegrityMonitor instance
        """
        self._integrity_monitor = monitor
    
    def escalate_on_integrity_failure(self) -> None:
        """
        Handle integrity failure with state escalation.
        
        Escalation rules:
        - SECURE + first failure → DEGRADED
        - DEGRADED + second failure → COMPROMISED
        - COMPROMISED + any failure → LOCKDOWN
        
        Artemis integrity violation
        Evidence preserved
        Escalation irreversible without restart
        """
        if not self._integrity_monitor:
            return
        
        failure_count = self._integrity_monitor.get_failure_count()
        
        # Artemis integrity violation
        # Evidence preserved
        # Escalation irreversible without restart
        
        if self._state == SecurityState.SECURE:
            if failure_count >= 1:
                # First failure - degrade
                self.set_degraded("Integrity check failed - first occurrence")
        
        elif self._state == SecurityState.DEGRADED:
            if failure_count >= 2:
                # Second failure - compromise
                self.set_compromised("Integrity check failed - second occurrence or audit corruption")
        
        elif self._state == SecurityState.COMPROMISED:
            if failure_count >= 2:
                # Any failure while compromised - full lockdown
                self.lockdown("Integrity failure while already compromised")
    
    def verify_integrity(self) -> Tuple[bool, list]:
        """
        Perform explicit integrity verification.
        
        Called:
        - At boot
        - Before execution
        - On explicit user request
        
        Returns:
            Tuple of (is_valid, mismatches)
        
        Raises:
            RuntimeError: If monitor not configured
        """
        if not self._integrity_monitor:
            raise RuntimeError(
                "Integrity monitor not configured. "
                "Cannot verify integrity."
            )
        
        is_valid, mismatches = self._integrity_monitor.verify_files(Path("."))

        self._record_event("integrity_check", {
            "valid": is_valid,
            "mismatch_count": len(mismatches),
        })
        
        # Auto-escalate on failure
        if not is_valid:
            self.escalate_on_integrity_failure()
        
        return is_valid, mismatches    

    def record_execution_block(self, boundary: str, reason: str) -> None:
        """
        Record an execution block event.

        Artemis inspection surface
        Read-only
        No side effects
        Safe in LOCKDOWN
        """
        self._record_event("execution_block", {
            "boundary": boundary,
            "reason": reason,
        })

    def inspect_security_state(self) -> Dict[str, str | None]:
        """
        Inspect current security state (read-only).

        Artemis inspection surface
        Read-only
        No side effects
        Safe in LOCKDOWN
        """
        return {
            "state": self._state.name,
            "last_escalation_reason": self._last_escalation_reason,
        }

    def inspect_security_summary(self) -> SecuritySummary:
        """
        Inspect current security summary (read-only).

        Artemis security UX
        Informational only
        No authority
        No side effects
        """
        policy = get_policy_for_state(self._state)
        explanation = self._build_security_explanation()
        return SecuritySummary(
            state=self._state.name,
            explanation=explanation,
            last_transition_time=self._last_transition_time,
            execution_allowed=policy.allow_execution,
        )

    def inspect_recent_events(self, limit: int = 10) -> tuple[dict, ...]:
        """
        Inspect recent event summaries (read-only).

        Artemis inspection surface
        Read-only
        No side effects
        Safe in LOCKDOWN
        """
        events = self._event_trace.snapshot(limit)
        summaries = []
        for event in events:
            summaries.append({
                "seq": event.seq,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "hash": event.hash,
            })
        return tuple(summaries)

    def inspect_event_chain_valid(self) -> bool:
        """
        Verify event chain integrity (read-only).

        Artemis inspection surface
        Read-only
        No side effects
        Safe in LOCKDOWN
        """
        return self._event_trace.verify_chain()

    def _build_security_explanation(self) -> str:
        if self._state == SecurityState.SECURE:
            return "No integrity mismatches detected. Execution is currently allowed."
        if self._state == SecurityState.DEGRADED:
            return "Integrity mismatch detected. Execution may be restricted."
        if self._state == SecurityState.COMPROMISED:
            return "Integrity mismatch detected. Execution is currently restricted."
        return "Integrity mismatch detected or policy escalation. Execution is currently restricted."

    def _record_event(self, event_type: str, details: dict) -> None:
        """
        Append an event to the trace (internal only).
        """
        self._event_trace.append(event_type, details)
    def is_locked(self) -> bool:
        """Check if system is in permanent lockdown."""
        return self._locked
    
    def get_lockdown_reason(self) -> str | None:
        """Get the reason for lockdown, if any."""
        return self._lockdown_reason
    
    def current_policy(self) -> LockdownPolicy:
        """
        Get the access policy for the current security state.
        
        Policy evaluation is separate from enforcement.
        This method returns the policy but does NOT enforce it.
        Enforcement must be implemented in subsystems that use this policy.
        
        Returns:
            The LockdownPolicy for the current state
        """
        return get_policy_for_state(self._state)
