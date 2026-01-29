"""
Security state definitions for Artemis.
"""

from enum import Enum, auto


class SecurityState(Enum):
    """
    Global security state of the Hearth system.
    
    States are ordered by severity:
    - SECURE: Normal operation, all checks pass
    - DEGRADED: Minor issues detected, system operational but compromised
    - COMPROMISED: Serious security violation detected
    - LOCKDOWN: System locked, no operations permitted
    
    Once LOCKDOWN is entered, only a system restart can recover.
    """
    
    SECURE = auto()
    DEGRADED = auto()
    COMPROMISED = auto()
    LOCKDOWN = auto()
