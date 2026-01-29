"""
KillSwitch - Immediate process termination mechanism.

Artemis kill-path
Fail-closed
No recovery without restart
"""

import os
import sys


class KillSwitch:
    """
    Emergency termination mechanism for Hearth.
    
    This is the nuclear option - it terminates the process immediately
    without cleanup, without grace, without mercy.
    
    Should only be invoked by ArtemisGuardian in response to
    unrecoverable security violations.
    
    Life cycle:
    1. arm() - Prepare kill switch (no termination yet)
    2. execute() - Terminate process immediately
    
    arm() is called when entering COMPROMISED/LOCKDOWN.
    execute() is only called on explicit shutdown or integrity failure.
    """
    
    def __init__(self):
        """Initialize kill switch."""
        self._triggered = False
        self._armed = False
        self._arm_reason: str | None = None
    
    def arm(self, reason: str) -> None:
        """
        Arm the kill switch.
        
        Called by ArtemisGuardian when entering COMPROMISED or LOCKDOWN.
        Does NOT immediately terminate - preparation only.
        
        Args:
            reason: Why the kill switch was armed
        """
        if not reason or not reason.strip():
            reason = "Unknown reason"
        
        self._armed = True
        self._arm_reason = reason
    
    def is_armed(self) -> bool:
        """Check if kill switch is armed (but not yet triggered)."""
        return self._armed and not self._triggered
    
    def get_arm_reason(self) -> str | None:
        """Get the reason the kill switch was armed, if armed."""
        return self._arm_reason
    
    def trigger(self, reason: str) -> None:
        """
        Immediately terminate the process.
        
        This uses os._exit(1) which:
        - Does NOT call cleanup handlers
        - Does NOT flush buffers
        - Does NOT run finally blocks
        - Terminates IMMEDIATELY
        
        Only call this if:
        - User explicitly requests shutdown while armed
        - OR integrity failure escalates beyond recovery
        
        Artemis kill-path
        Fail-closed
        No recovery without restart
        
        Args:
            reason: Why the kill switch was triggered
        
        Note:
            This function does not return.
        """
        if not reason or not reason.strip():
            reason = "Unknown reason"
        
        self._triggered = True
        
        # Attempt to write to stderr (may fail if file descriptors are compromised)
        try:
            sys.stderr.write(f"\n{'='*60}\n")
            sys.stderr.write("ARTEMIS KILL SWITCH TRIGGERED\n")
            sys.stderr.write(f"Armed for: {self._arm_reason}\n" if self._arm_reason else "")
            sys.stderr.write(f"Triggered for: {reason}\n")
            sys.stderr.write(f"{'='*60}\n")
            sys.stderr.flush()
        except Exception:
            # If we can't even write to stderr, we're in deep trouble
            # Proceed with termination anyway
            pass
        
        # Brutal, immediate termination
        # Exit code 1 indicates abnormal termination
        os._exit(1)
    
    def is_triggered(self) -> bool:
        """
        Check if kill switch has been triggered.
        
        Note:
            If this returns True, the process is about to terminate.
            In practice, this will rarely return True because the
            process exits immediately upon trigger().
        
        Returns:
            True if triggered, False otherwise
        """
        return self._triggered
