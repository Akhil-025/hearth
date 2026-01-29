"""
Artemis Lockdown Boundaries - Formal Definition of Security Policy

This module defines what operations are allowed or disallowed
in each security state.

CRITICAL PRINCIPLE:
  Lockdown is a frozen execution state, not system death.
  Policy evaluation is separate from enforcement.
  
  This file DEFINES the boundaries. Enforcement happens elsewhere.
"""

from dataclasses import dataclass
from artemis.state import SecurityState


@dataclass(frozen=True)
class LockdownPolicy:
    """
    Immutable policy definition for a security state.
    
    Each boolean explicitly states what is ALLOWED in this state.
    Missing a state in the policy => LOCKDOWN behavior (fail closed).
    
    Attributes:
        allow_execution: Can user tasks execute?
        allow_planning: Can Hestia perform reasoning/planning? (read-only)
        allow_memory_read: Can subsystems read from memory/knowledge?
        allow_memory_write: Can subsystems write to memory/knowledge?
        allow_network: Can subsystems make network calls?
        allow_domains: Can domain services execute?
        allow_cli: Can CLI interface accept input and display output?
        allow_ui: Can UI layer function?
        allow_shutdown: Can the system shut down gracefully?
    """
    
    allow_execution: bool
    allow_planning: bool
    allow_memory_read: bool
    allow_memory_write: bool
    allow_network: bool
    allow_domains: bool
    allow_cli: bool
    allow_ui: bool
    allow_shutdown: bool
    
    def __repr__(self) -> str:
        """Human-readable representation."""
        allowed = []
        disallowed = []
        
        for attr in [
            "execution", "planning", "memory_read", "memory_write",
            "network", "domains", "cli", "ui", "shutdown"
        ]:
            key = f"allow_{attr}"
            if getattr(self, key):
                allowed.append(attr)
            else:
                disallowed.append(attr)
        
        return (
            f"LockdownPolicy(allowed={allowed}, "
            f"disallowed={disallowed})"
        )


# SECURE: Full operation
POLICY_SECURE = LockdownPolicy(
    allow_execution=True,
    allow_planning=True,
    allow_memory_read=True,
    allow_memory_write=True,
    allow_network=True,
    allow_domains=True,
    allow_cli=True,
    allow_ui=True,
    allow_shutdown=True,
)

# DEGRADED: Restrict some write operations, network
POLICY_DEGRADED = LockdownPolicy(
    allow_execution=True,
    allow_planning=True,
    allow_memory_read=True,
    allow_memory_write=False,  # No writes during degraded
    allow_network=False,  # No network during degraded
    allow_domains=True,
    allow_cli=True,
    allow_ui=True,
    allow_shutdown=True,
)

# COMPROMISED: Only read operations and inspection
POLICY_COMPROMISED = LockdownPolicy(
    allow_execution=False,  # No execution
    allow_planning=True,    # Reasoning OK (read-only)
    allow_memory_read=True,
    allow_memory_write=False,
    allow_network=False,
    allow_domains=False,  # No domain execution
    allow_cli=True,       # Inspection/alerts via CLI
    allow_ui=True,        # UI for alerts
    allow_shutdown=True,  # Can shut down
)

# LOCKDOWN: Frozen execution state
# Lockdown is a frozen execution state, not system death.
# The system can still be inspected and shut down, but no mutations
# or operations that could spread compromise.
POLICY_LOCKDOWN = LockdownPolicy(
    allow_execution=False,     # No execution - FROZEN
    allow_planning=True,       # Reasoning OK (read-only investigation)
    allow_memory_read=True,    # Can read memory for analysis
    allow_memory_write=False,  # No writes - state frozen
    allow_network=False,       # No network - isolated
    allow_domains=False,       # No domain operations
    allow_cli=True,            # CLI for alerts and inspection
    allow_ui=True,             # UI for status display
    allow_shutdown=True,       # Can shut down gracefully
)


def get_policy_for_state(state: SecurityState) -> LockdownPolicy:
    """
    Get the access policy for a given security state.
    
    Args:
        state: The SecurityState to get policy for
    
    Returns:
        The LockdownPolicy for this state
    
    Raises:
        ValueError: If state is unknown (fail closed)
    """
    policies = {
        SecurityState.SECURE: POLICY_SECURE,
        SecurityState.DEGRADED: POLICY_DEGRADED,
        SecurityState.COMPROMISED: POLICY_COMPROMISED,
        SecurityState.LOCKDOWN: POLICY_LOCKDOWN,
    }
    
    if state not in policies:
        # Fail closed: unknown state => LOCKDOWN policy
        raise ValueError(
            f"Unknown security state: {state}. "
            "Assuming LOCKDOWN (fail closed)."
        )
    
    return policies[state]
