"""
Credential Management with Artemis Lockdown Support

Credentials are frozen when Artemis enters COMPROMISED or LOCKDOWN state.
Once frozen, credentials cannot be retrieved until system restart.

Artemis kill-path
Fail-closed
No recovery without restart
"""

from typing import Dict, Optional, Any


class CredentialStore:
    """
    Secure credential storage with Artemis lockdown support.
    
    When frozen:
    - All get() calls raise RuntimeError
    - No credentials can be retrieved
    - Freezing is permanent until restart
    """
    
    def __init__(self):
        """Initialize credential store."""
        self._credentials: Dict[str, Any] = {}
        self._frozen = False
        self._freeze_reason: Optional[str] = None
    
    def store(self, key: str, value: Any) -> None:
        """
        Store a credential.

        Artemis attack-surface reduction
        Fail closed
        No recovery without restart

        Writes are allowed only before freeze.
        
        Args:
            key: Credential identifier
            value: Credential value (any type)
        
        Raises:
            RuntimeError: If store is frozen
        """
        if self._frozen:
            raise RuntimeError(
                f"Credential storage blocked by Artemis security state: {self._freeze_reason}"
            )
        
        self._credentials[key] = value
    
    def get(self, key: str) -> Any:
        """
        Retrieve a credential.
        
        Artemis kill-path
        Fail-closed
        No recovery without restart
        
        Args:
            key: Credential identifier
        
        Returns:
            Credential value
        
        Raises:
            RuntimeError: If store is frozen
            KeyError: If credential not found
        """
        if self._frozen:
            # Artemis kill-path
            # Fail-closed
            # No recovery without restart
            raise RuntimeError(
                f"Credential access blocked by Artemis security state: {self._freeze_reason}"
            )
        
        if key not in self._credentials:
            raise KeyError(f"Credential not found: {key}")
        
        return self._credentials[key]
    
    def has(self, key: str) -> bool:
        """
        Check if credential exists WITHOUT retrieving it.
        
        This is allowed even when frozen, for inspection purposes.
        
        Args:
            key: Credential identifier
        
        Returns:
            True if credential exists, False otherwise
        """
        return key in self._credentials
    
    def freeze(self, reason: str) -> None:
        """
        Freeze credential access immediately.
        
        Called by Artemis when entering COMPROMISED or LOCKDOWN.
        
        Args:
            reason: Reason for freeze (SecurityState name)
        """
        if self._frozen:
            # Already frozen - no-op
            return
        
        self._frozen = True
        self._freeze_reason = reason
    
    def unfreeze(self) -> None:
        """
        Unfreeze credential access.
        
        REQUIRES MANUAL ACTION - called only during system restart.
        Not called automatically.
        
        This is intentionally not called by normal code paths.
        """
        self._frozen = False
        self._freeze_reason = None
    
    def is_frozen(self) -> bool:
        """Check if credential store is frozen."""
        return self._frozen
    
    def get_freeze_reason(self) -> Optional[str]:
        """Get the reason credentials are frozen, if frozen."""
        return self._freeze_reason
    
    def list_keys(self) -> tuple:
        """
        List all credential keys (for inspection).
        
        Returns keys even if frozen - allows inspection during lockdown.
        Does NOT return values.
        
        Returns:
            Tuple of credential keys
        """
        return tuple(self._credentials.keys())


# Global credential store singleton
_credential_store: Optional[CredentialStore] = None


def get_credential_store() -> CredentialStore:
    """
    Get the global credential store instance.
    
    Returns:
        The CredentialStore singleton
    """
    global _credential_store
    if _credential_store is None:
        _credential_store = CredentialStore()
    return _credential_store
