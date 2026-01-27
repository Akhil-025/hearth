"""
Global Kill Switches / Safe Modes

Allows runtime disabling of critical system capabilities.
Safe mode overrides all module behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from ..shared.logging.structured_logger import StructuredLogger


class SafeModeLevel(Enum):
    """Safe mode severity levels."""
    NORMAL = "normal"        # All operations allowed
    GUARDED = "guarded"      # Additional checks and confirmations
    RESTRICTED = "restricted" # Critical operations disabled
    LOCKDOWN = "lockdown"    # Read-only, no changes allowed


class CapabilityLock(Enum):
    """Capabilities that can be locked in safe mode."""
    MEMORY_WRITES = "memory_writes"
    BEHAVIORAL_INFERENCE = "behavioral_inference"
    FINANCIAL_REASONING = "financial_reasoning"
    EXTERNAL_IO = "external_io"
    LLM_REQUESTS = "llm_requests"
    DOMAIN_INTELLIGENCE = "domain_intelligence"
    ALL_WRITES = "all_writes"
    ALL_INFERENCE = "all_inference"


@dataclass
class SafeModeOverride:
    """Override for a specific operation in safe mode."""
    operation: str
    allowed_levels: Set[SafeModeLevel]
    fallback_behavior: str
    requires_confirmation: bool = False


class SafeModeConfig(BaseModel):
    """Safe mode configuration."""
    current_level: SafeModeLevel = SafeModeLevel.NORMAL
    locked_capabilities: Set[CapabilityLock] = Field(default_factory=set)
    overrides: List[SafeModeOverride] = Field(default_factory=list)
    
    # Manual overrides (set by user/admin)
    manual_overrides: Dict[str, bool] = Field(default_factory=dict)
    
    # Audit trail
    activation_history: List[Dict[str, str]] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class SafeModeManager:
    """
    Manages global kill switches and safe modes.
    
    Enforces restrictions across all modules.
    """
    
    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.config = SafeModeConfig()
        
        # Default capability locks per level
        self.level_locks: Dict[SafeModeLevel, Set[CapabilityLock]] = {
            SafeModeLevel.NORMAL: set(),
            SafeModeLevel.GUARDED: {
                CapabilityLock.FINANCIAL_REASONING,
                CapabilityLock.BEHAVIORAL_INFERENCE
            },
            SafeModeLevel.RESTRICTED: {
                CapabilityLock.MEMORY_WRITES,
                CapabilityLock.FINANCIAL_REASONING,
                CapabilityLock.BEHAVIORAL_INFERENCE,
                CapabilityLock.EXTERNAL_IO
            },
            SafeModeLevel.LOCKDOWN: {
                CapabilityLock.ALL_WRITES,
                CapabilityLock.ALL_INFERENCE,
                CapabilityLock.EXTERNAL_IO
            }
        }
        
        # Default overrides
        self._register_default_overrides()
        
        self.logger.info("Safe mode manager initialized")
    
    def _register_default_overrides(self) -> None:
        """Register default safe mode overrides."""
        # Memory reads are always allowed
        self.config.overrides.append(SafeModeOverride(
            operation="memory_read",
            allowed_levels={
                SafeModeLevel.NORMAL,
                SafeModeLevel.GUARDED,
                SafeModeLevel.RESTRICTED,
                SafeModeLevel.LOCKDOWN
            },
            fallback_behavior="allow",
            requires_confirmation=False
        ))
        
        # Identity memory writes (new versions) allowed in guarded mode
        self.config.overrides.append(SafeModeOverride(
            operation="identity_memory_create",
            allowed_levels={
                SafeModeLevel.NORMAL,
                SafeModeLevel.GUARDED
            },
            fallback_behavior="require_confirmation",
            requires_confirmation=True
        ))
        
        # Health advisory always allowed (but with confirmation)
        self.config.overrides.append(SafeModeOverride(
            operation="health_advisory",
            allowed_levels={
                SafeModeLevel.NORMAL,
                SafeModeLevel.GUARDED,
                SafeModeLevel.RESTRICTED
            },
            fallback_behavior="require_confirmation",
            requires_confirmation=True
        ))
    
    def set_safe_mode(self, level: SafeModeLevel, reason: str) -> None:
        """
        Set safe mode level.
        
        Args:
            level: New safe mode level
            reason: Reason for change (audit trail)
        """
        previous_level = self.config.current_level
        
        # Update level
        self.config.current_level = level
        
        # Update locked capabilities
        self.config.locked_capabilities = self.level_locks.get(level, set())
        
        # Record activation
        self.config.activation_history.append({
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "previous_level": previous_level.value,
            "new_level": level.value,
            "reason": reason,
            "locked_capabilities": [c.value for c in self.config.locked_capabilities]
        })
        
        # Keep only last 100 activations
        if len(self.config.activation_history) > 100:
            self.config.activation_history = self.config.activation_history[-100:]
        
        self.logger.warning(
            "Safe mode level changed",
            previous_level=previous_level.value,
            new_level=level.value,
            reason=reason
        )
    
    def check_operation_allowed(
        self,
        module: str,
        operation: str,
        capability: Optional[CapabilityLock] = None
    ) -> Dict[str, any]:
        """
        Check if an operation is allowed in current safe mode.
        
        Returns:
            Dict with allowed status and any restrictions
        """
        current_level = self.config.current_level
        
        # Check manual overrides first
        override_key = f"{module}.{operation}"
        if override_key in self.config.manual_overrides:
            allowed = self.config.manual_overrides[override_key]
            return {
                "allowed": allowed,
                "reason": "manual_override",
                "requires_confirmation": False,
                "safe_mode_level": current_level.value
            }
        
        # Check operation-specific overrides
        for override in self.config.overrides:
            if override.operation == operation:
                if current_level in override.allowed_levels:
                    return {
                        "allowed": True,
                        "reason": "operation_override",
                        "requires_confirmation": override.requires_confirmation,
                        "safe_mode_level": current_level.value
                    }
                else:
                    return {
                        "allowed": False,
                        "reason": f"operation_disabled_in_{current_level.value}",
                        "fallback_behavior": override.fallback_behavior,
                        "safe_mode_level": current_level.value
                    }
        
        # Check capability locks
        if capability and capability in self.config.locked_capabilities:
            return {
                "allowed": False,
                "reason": f"capability_locked_{capability.value}",
                "safe_mode_level": current_level.value
            }
        
        # Check if operation involves locked capabilities
        operation_capabilities = self._map_operation_to_capabilities(module, operation)
        locked_ops = operation_capabilities.intersection(self.config.locked_capabilities)
        
        if locked_ops:
            return {
                "allowed": False,
                "reason": f"involves_locked_capabilities: {[c.value for c in locked_ops]}",
                "safe_mode_level": current_level.value
            }
        
        # Operation is allowed
        return {
            "allowed": True,
            "reason": "no_restrictions",
            "requires_confirmation": current_level == SafeModeLevel.GUARDED,
            "safe_mode_level": current_level.value
        }
    
    def _map_operation_to_capabilities(
        self,
        module: str,
        operation: str
    ) -> Set[CapabilityLock]:
        """Map module/operation to capabilities."""
        capabilities = set()
        
        # Memory operations
        if module == "mnemosyne" or "memory" in operation:
            if "write" in operation or "create" in operation or "update" in operation:
                capabilities.add(CapabilityLock.MEMORY_WRITES)
        
        # Behavioral operations
        if module == "mnemosyne" and "behavioral" in operation:
            capabilities.add(CapabilityLock.BEHAVIORAL_INFERENCE)
        
        # Financial operations
        if module == "pluto":
            capabilities.add(CapabilityLock.FINANCIAL_REASONING)
        
        # External I/O
        if any(term in operation for term in ["network", "socket", "http", "api", "external"]):
            capabilities.add(CapabilityLock.EXTERNAL_IO)
        
        # LLM requests
        if "llm" in operation or "ollama" in operation:
            capabilities.add(CapabilityLock.LLM_REQUESTS)
        
        # Domain intelligence
        if module in ["hermes", "hephaestus", "apollo", "dionysus"]:
            capabilities.add(CapabilityLock.DOMAIN_INTELLIGENCE)
        
        return capabilities
    
    def enforce_operation(
        self,
        module: str,
        operation: str,
        capability: Optional[CapabilityLock] = None
    ) -> None:
        """
        Enforce safe mode restrictions on an operation.
        
        Raises:
            SafeModeRestrictionError: If operation is not allowed
        """
        check_result = self.check_operation_allowed(module, operation, capability)
        
        if not check_result["allowed"]:
            raise SafeModeRestrictionError(
                module=module,
                operation=operation,
                reason=check_result["reason"],
                safe_mode_level=self.config.current_level.value
            )
    
    def add_manual_override(
        self,
        module: str,
        operation: str,
        allowed: bool,
        reason: str
    ) -> None:
        """
        Add a manual override for a specific operation.
        
        Use with extreme caution - bypasses safe mode protections.
        """
        override_key = f"{module}.{operation}"
        self.config.manual_overrides[override_key] = allowed
        
        self.logger.critical(
            "Manual safe mode override added",
            module=module,
            operation=operation,
            allowed=allowed,
            reason=reason,
            safe_mode_level=self.config.current_level.value
        )
    
    def remove_manual_override(self, module: str, operation: str) -> bool:
        """Remove a manual override."""
        override_key = f"{module}.{operation}"
        if override_key in self.config.manual_overrides:
            del self.config.manual_overrides[override_key]
            self.logger.info(
                "Manual safe mode override removed",
                module=module,
                operation=operation
            )
            return True
        return False
    
    def get_status(self) -> Dict[str, any]:
        """Get current safe mode status."""
        return {
            "current_level": self.config.current_level.value,
            "locked_capabilities": [c.value for c in self.config.locked_capabilities],
            "manual_overrides_count": len(self.config.manual_overrides),
            "recent_activations": self.config.activation_history[-5:] if self.config.activation_history else []
        }


class SafeModeRestrictionError(Exception):
    """Raised when an operation is restricted by safe mode."""
    
    def __init__(self, module: str, operation: str, reason: str, safe_mode_level: str):
        self.module = module
        self.operation = operation
        self.reason = reason
        self.safe_mode_level = safe_mode_level
        super().__init__(
            f"Safe mode restriction: {module}.{operation} - {reason} (level: {safe_mode_level})"
        )


# Global safe mode manager singleton
_safe_mode_manager: Optional[SafeModeManager] = None

def get_safe_mode_manager() -> SafeModeManager:
    """Get the global safe mode manager (singleton)."""
    global _safe_mode_manager
    if _safe_mode_manager is None:
        _safe_mode_manager = SafeModeManager()
    return _safe_mode_manager


# Decorator for safe mode checking
def require_safe_mode(module: str, operation: str, capability: Optional[CapabilityLock] = None):
    """
    Decorator to enforce safe mode restrictions.
    
    Usage:
        @require_safe_mode(module="hestia", operation="process_input")
        async def process_input(self, user_input):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = get_safe_mode_manager()
            manager.enforce_operation(module, operation, capability)
            return func(*args, **kwargs)
        
        async def async_wrapper(*args, **kwargs):
            manager = get_safe_mode_manager()
            manager.enforce_operation(module, operation, capability)
            return await func(*args, **kwargs)
        
        return async_wrapper if __import__("inspect").iscoroutinefunction(func) else wrapper
    
    return decorator