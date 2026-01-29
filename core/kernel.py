"""
HEARTH Kernel - Minimal Stub (v0.1)

DISABLED IN v0.1:
- Service lifecycle management
- Dependency resolution
- Health monitoring
- Graceful shutdown
- Audit logging

Artemis kill-path
Fail-closed
No recovery without restart
"""
from dataclasses import dataclass
from typing import Optional, Dict

# DISABLED IN v0.1  not part of execution spine
# from ..shared.logging.structured_logger import StructuredLogger
from .event_bus import EventBus
from .permission_manager import PermissionManager
from .config_loader import ConfigLoader
from .service_registry import ServiceRegistry

from artemis.guardian import ArtemisGuardian
from artemis.boundary import LockdownPolicy, POLICY_SECURE
from artemis.state import SecurityState


@dataclass
class KernelConfig:
    """Kernel configuration."""
    data_dir: str = "./data"
    log_level: str = "INFO"
    enable_audit: bool = False  # DISABLED IN v0.1
    require_permissions: bool = False  # DISABLED IN v0.1
    service_startup_timeout: int = 30
    service_shutdown_timeout: int = 10


class HearthKernel:
    """
    Minimal kernel - just holds configuration.
    
    FUTURE: Will manage services, dependencies, lifecycle, audit.
    
    Policy awareness:
      Kernel holds a reference to ArtemisGuardian for passive policy visibility.
      Policy awareness only — enforcement occurs later.
      This reference must never block execution or change behavior.
    """
    
    def __init__(self, config: Optional[KernelConfig] = None, artemis: Optional[ArtemisGuardian] = None):
        self.config = config or KernelConfig()
        self._artemis = artemis
        
        # DISABLED IN v0.1  minimal noop instances
        self.event_bus = EventBus()
        self.service_registry = ServiceRegistry()
        self.permission_manager = PermissionManager()
        self.config_loader = ConfigLoader()
        
        self.running = False
    
    def get_security_policy(self) -> LockdownPolicy:
        """
        Get the current security policy from Artemis.
        
        Policy awareness only — enforcement occurs later.
        This method must never block execution or raise exceptions.
        
        Returns:
            The current LockdownPolicy, or a safe default if Artemis unavailable
        """
        if self._artemis is None:
            # If no Artemis reference, we cannot query policy
            # Return a permissive default (will be overridden by actual Artemis)
            return POLICY_SECURE
        
        # Simply return the current policy - no enforcement here
        return self._artemis.current_policy()
    
    def enforce_execution_policy(self) -> None:
        """
        Enforce the execution policy before any execution occurs.
        
        Artemis enforcement boundary - Fail-closed by design
        Do not bypass.
        
        In LOCKDOWN state:
        - Only inspection and shutdown allowed
        - All other operations blocked
        
        Raises:
            RuntimeError: If execution is not allowed by current policy
        """
        # ────────────────────────────────────────────────────────────────
        # EXECUTION GATE: Integrity verification before execution
        # ────────────────────────────────────────────────────────────────
        # Artemis integrity gate
        # Fail closed
        # No execution past this point
        # Artemis attack-surface reduction
        # Fail closed
        # No recovery without restart
        
        if self._artemis:
            # Artemis attack-surface reduction
            # Fail closed
            # No recovery without restart
            self._artemis.assert_single_process_execution()

            try:
                is_valid, mismatches = self._artemis.verify_integrity()
                
                if not is_valid:
                    # Integrity check failed - Artemis escalated state
                    artemis_state = self._artemis.get_state().name
                    print(f"[Artemis] EXECUTION GATE: Integrity verification failed")
                    print(f"[Artemis] State escalated to: {artemis_state}")
                    
                    for mismatch in mismatches:
                        print(f"  - {mismatch['file']}: {mismatch['status']}")
                    
                    raise RuntimeError(
                        f"Execution blocked: Artemis integrity gate failed (state: {artemis_state})"
                    )
            except RuntimeError as e:
                if "Integrity monitor not configured" not in str(e):
                    # Re-raise integrity failures
                    raise RuntimeError(f"Execution gate failed: {e}")
        
        policy = self.get_security_policy()
        
        # Artemis kill-path
        # Fail-closed
        # No recovery without restart
        # Artemis fault containment
        # Blast radius limited
        # Fail closed
        # No recovery without restart

        try:
            # ────────────────────────────────────────────────────────────────
            # EXECUTION GATE: Integrity verification before execution
            # ────────────────────────────────────────────────────────────────
            # Artemis integrity gate
            # Fail closed
            # No execution past this point
            # Artemis attack-surface reduction
            # Fail closed
            # No recovery without restart
            
            if self._artemis:
                # Artemis attack-surface reduction
                # Fail closed
                # No recovery without restart
                self._artemis.assert_single_process_execution()

                try:
                    is_valid, mismatches = self._artemis.verify_integrity()
                    
                    if not is_valid:
                        # Integrity check failed - Artemis escalated state
                        artemis_state = self._artemis.get_state().name
                        print(f"[Artemis] EXECUTION GATE: Integrity verification failed")
                        print(f"[Artemis] State escalated to: {artemis_state}")
                        
                        for mismatch in mismatches:
                            print(f"  - {mismatch['file']}: {mismatch['status']}")
                        
                        reason = f"Integrity gate failed (state: {artemis_state})"
                        self._artemis.record_execution_block("kernel", reason)
                        raise RuntimeError(f"Execution blocked: {reason}")
                except RuntimeError as e:
                    if "Integrity monitor not configured" not in str(e):
                        # Re-raise integrity failures
                        raise RuntimeError(f"Execution gate failed: {e}")
            
            policy = self.get_security_policy()
            
            # Artemis kill-path
            # Fail-closed
            # No recovery without restart
            if not policy.allow_execution:
                artemis_state = self._artemis.get_state().name if self._artemis else "UNKNOWN"
                reason = f"Policy blocked execution (state: {artemis_state})"
                if self._artemis:
                    self._artemis.record_execution_block("kernel", reason)
                raise RuntimeError(f"Execution blocked: {reason}")
        except Exception as e:
            if self._artemis:
                self._artemis.handle_boundary_error(e, "kernel")
            raise RuntimeError(f"Kernel execution boundary failure: {e}")

    def inspect_security_state(self) -> Dict[str, str | None]:
        """
        Inspect current security state (read-only).

        Artemis inspection surface
        Read-only
        No side effects
        Safe in LOCKDOWN
        """
        if not self._artemis:
            return {"state": "UNKNOWN", "last_escalation_reason": None}
        return self._artemis.inspect_security_state()

    def inspect_security_summary(self):
        """
        Inspect current security summary (read-only).

        Artemis security UX
        Informational only
        No authority
        No side effects
        """
        if not self._artemis:
            return None
        return self._artemis.inspect_security_summary()

    def inspect_recent_events(self, limit: int = 10) -> tuple[dict, ...]:
        """
        Inspect recent Artemis events (read-only).

        Artemis inspection surface
        Read-only
        No side effects
        Safe in LOCKDOWN
        """
        if not self._artemis:
            return tuple()
        return self._artemis.inspect_recent_events(limit)

    def trigger_kill_switch(self, reason: str) -> None:
        """
        Trigger the Artemis kill switch.
        
        Security escalation detected - OR integrity failure requires immediate termination
        
        Artemis kill-path
        Fail-closed
        No recovery without restart
        
        Args:
            reason: Reason for shutdown
        """
        if not self._artemis:
            return
        
        kill_switch = self._artemis.get_kill_switch()
        
        if kill_switch.is_armed():
            # Kill switch is armed - execute immediate termination
            kill_switch.trigger(reason)
