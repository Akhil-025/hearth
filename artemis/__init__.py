"""
Artemis - Root Security Authority for Hearth

Artemis is the absolute security authority for the Hearth system.
It is NOT a domain or faculty - it exists above all other components.

Key principles:
- Deterministic and explicit
- Fails closed
- No network calls
- Standard library only

Artemis kill-path
Fail-closed
No recovery without restart
"""

from artemis.state import SecurityState
from artemis.guardian import ArtemisGuardian
from artemis.integrity import IntegrityMonitor
from artemis.integrity_baseline import IntegrityBaseline
from artemis.kill_switch import KillSwitch
from artemis.boundary import LockdownPolicy, get_policy_for_state

__all__ = [
    "SecurityState",
    "ArtemisGuardian",
    "IntegrityMonitor",
    "IntegrityBaseline",
    "KillSwitch",
    "LockdownPolicy",
    "get_policy_for_state",
]
