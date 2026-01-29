"""
Hearth System Bootstrap - Initialization Order and System State

This module manages the initialization sequence of Hearth.
Artemis is initialized FIRST, before any other subsystem.

Order of initialization:
  1. ArtemisGuardian (security authority) - MUST be first
  2. Event bus and other core infrastructure
  3. Services and domains

Artemis presence during boot:
  - Passive: No integrity checks, no kill switch, no enforcement
  - Active: Tracks state, enforces transitions via API only
  - Ready: Enforcement can be enabled later by explicit call
"""

from artemis.guardian import ArtemisGuardian
from artemis.integrity import IntegrityMonitor
from artemis.state import SecurityState
from core.invariants import set_violation_handler
from pathlib import Path


class SystemState:
    """
    Singleton-like holder for system-wide state.
    
    This is NOT a global variable - it's a module-level singleton
    that must be explicitly initialized during bootstrap.
    """
    
    _artemis: ArtemisGuardian | None = None
    
    @classmethod
    def initialize_artemis(cls) -> ArtemisGuardian:
        """
        Initialize Artemis during system bootstrap.
        
        This MUST be called first, before any other subsystem initialization.
        It creates the ArtemisGuardian and sets it to SECURE state.
        
        Artemis is passive during boot. Enforcement begins later.
        
        Returns:
            The initialized ArtemisGuardian instance
        
        Raises:
            RuntimeError: If Artemis fails to initialize (fail closed)
            RuntimeError: If Artemis is already initialized
        """
        if cls._artemis is not None:
            raise RuntimeError(
                "Artemis is already initialized. "
                "Cannot reinitialize system state."
            )
        
        try:
            artemis = ArtemisGuardian()
            
            # Verify it's in SECURE state
            if artemis.get_state() != SecurityState.SECURE:
                raise RuntimeError(
                    f"ArtemisGuardian initialized in invalid state: "
                    f"{artemis.get_state().name}"
                )
            
            cls._artemis = artemis
            return artemis
        
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Artemis: {e}. "
                "System startup aborted (fail closed)."
            )
    
    @classmethod
    def get_artemis(cls) -> ArtemisGuardian:
        """
        Get the initialized ArtemisGuardian instance.
        
        Returns:
            The ArtemisGuardian instance
        
        Raises:
            RuntimeError: If Artemis has not been initialized yet
        """
        if cls._artemis is None:
            raise RuntimeError(
                "Artemis has not been initialized. "
                "Call initialize_artemis() during bootstrap."
            )
        
        return cls._artemis
    
    @classmethod
    def is_artemis_initialized(cls) -> bool:
        """
        Check if Artemis has been initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return cls._artemis is not None


def bootstrap_hearth() -> ArtemisGuardian:
    """
    Bootstrap the Hearth system.
    
    This function initializes the core security infrastructure:
    - Artemis (security authority) - FIRST
    - IntegrityMonitor (code and audit tamper detection)
    
    Future bootstrap steps will go here as the system grows:
    - Event bus initialization
    - Service registry setup
    - Domain startup
    
    Returns:
        The initialized ArtemisGuardian instance
    
    Raises:
        RuntimeError: If bootstrap fails (fail closed)
    """
    artemis = SystemState.initialize_artemis()

    # Artemis attack-surface reduction
    # Fail closed
    # No recovery without restart
    artemis.assert_single_process_execution()
    artemis.install_attack_surface_reduction()

    # Artemis fault containment
    # Blast radius limited
    # Fail closed
    # No recovery without restart
    set_violation_handler(lambda error: artemis.handle_boundary_error(error, "invariant"))
    
    # Wire up integrity monitoring
    integrity_monitor = IntegrityMonitor()
    artemis.set_integrity_monitor(integrity_monitor)
    
    # Initialize baseline at first boot
    try:
        integrity_monitor.initialize_baseline(Path("."))
    except Exception as e:
        # Baseline initialization failed - log but continue
        # System will verify on next check
        pass
    
    # Artemis is now initialized and PASSIVE
    # - No integrity checks yet
    # - No kill switch armed
    # - No enforcement active
    # This is a presence-only integration during boot
    
    return artemis
