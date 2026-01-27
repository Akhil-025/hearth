"""
System Invariants - Non-negotiable runtime rules for HEARTH.

Invariants are checked at critical execution points.
Violations raise fatal errors - system cannot proceed in invalid state.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type
from uuid import UUID

from ..shared.logging.structured_logger import StructuredLogger


class InvariantSeverity(Enum):
    """Invariant violation severity."""
    FATAL = "fatal"      # System must halt
    CRITICAL = "critical" # Operation must be rejected
    WARNING = "warning"   # Log warning but continue


@dataclass
class InvariantViolation:
    """Record of an invariant violation."""
    invariant_id: str
    severity: InvariantSeverity
    module: str
    operation: str
    context: Dict[str, Any]
    timestamp: str
    stack_trace: Optional[str] = None


class SystemInvariant:
    """
    Base class for system invariants.
    
    Each invariant must be:
    - Explicitly defined
    - Programmatically checkable
    - Enforced at runtime
    """
    
    def __init__(
        self,
        invariant_id: str,
        description: str,
        severity: InvariantSeverity = InvariantSeverity.CRITICAL
    ):
        self.invariant_id = invariant_id
        self.description = description
        self.severity = severity
        self.violation_count = 0
    
    def check(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        """
        Check if invariant holds in given context.
        
        Returns:
            InvariantViolation if invariant is violated, None otherwise
        """
        raise NotImplementedError
    
    def __call__(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        """Make invariant callable."""
        return self.check(context)


class InvariantRegistry:
    """
    Central registry for system invariants.
    
    Enforces invariants at critical execution points.
    """
    
    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.invariants: Dict[str, SystemInvariant] = {}
        self.violations: List[InvariantViolation] = []
        
        # Register core invariants
        self._register_core_invariants()
        
        self.logger.info("Invariant registry initialized")
    
    def _register_core_invariants(self) -> None:
        """Register non-negotiable system invariants."""
        
        # 1. Hestia cannot write memory directly
        self.register(NoDirectMemoryWriteInvariant())
        
        # 2. Athena cannot infer preferences
        self.register(NoPreferenceInferenceInvariant())
        
        # 3. Pluto cannot execute transactions
        self.register(NoTransactionExecutionInvariant())
        
        # 4. Behavioral memory cannot self-promote
        self.register(NoBehavioralSelfPromotionInvariant())
        
        # 5. Identity memory cannot be modified
        self.register(IdentityMemoryImmutableInvariant())
        
        # 6. No module may call Ollama directly (except Hestia)
        self.register(NoDirectLLMAccessInvariant())
        
        # 7. No module may bypass Hearth permissions
        self.register(PermissionBypassInvariant())
        
        # 8. No autonomous execution
        self.register(NoAutonomousExecutionInvariant())
        
        # 9. No cloud APIs
        self.register(NoCloudAPIsInvariant())
        
        self.logger.info(
            "Core invariants registered",
            count=len(self.invariants)
        )
    
    def register(self, invariant: SystemInvariant) -> None:
        """Register an invariant."""
        if invariant.invariant_id in self.invariants:
            raise ValueError(f"Invariant already registered: {invariant.invariant_id}")
        
        self.invariants[invariant.invariant_id] = invariant
        self.logger.debug(
            "Invariant registered",
            invariant_id=invariant.invariant_id,
            description=invariant.description
        )
    
    def enforce(
        self,
        module: str,
        operation: str,
        context: Dict[str, Any],
        check_all: bool = False
    ) -> None:
        """
        Enforce all relevant invariants.
        
        Args:
            module: Module performing the operation
            operation: Operation being performed
            context: Context for invariant checking
            check_all: If True, check all invariants; otherwise check relevant ones
        
        Raises:
            InvariantViolationError: If any invariant is violated
        """
        violations = []
        
        for invariant_id, invariant in self.invariants.items():
            # Add context about operation
            check_context = {
                **context,
                "module": module,
                "operation": operation
            }
            
            violation = invariant(check_context)
            if violation:
                violations.append(violation)
                invariant.violation_count += 1
                
                # Log violation
                self.logger.error(
                    "Invariant violation detected",
                    invariant_id=invariant_id,
                    module=module,
                    operation=operation,
                    severity=violation.severity.value
                )
                
                # If fatal, break immediately
                if violation.severity == InvariantSeverity.FATAL:
                    break
        
        if violations:
            # Record violations
            self.violations.extend(violations)
            
            # Raise appropriate exception
            fatal_violations = [
                v for v in violations 
                if v.severity == InvariantSeverity.FATAL
            ]
            
            if fatal_violations:
                raise FatalInvariantViolationError(fatal_violations)
            else:
                raise InvariantViolationError(violations)
    
    def get_violations(
        self,
        module: Optional[str] = None,
        operation: Optional[str] = None
    ) -> List[InvariantViolation]:
        """Get violation records, optionally filtered."""
        violations = self.violations
        
        if module:
            violations = [v for v in violations if v.module == module]
        if operation:
            violations = [v for v in violations if v.operation == operation]
        
        return violations
    
    def get_invariant_stats(self) -> Dict[str, Any]:
        """Get statistics about invariants."""
        stats = {
            "total_invariants": len(self.invariants),
            "total_violations": len(self.violations),
            "invariants": {}
        }
        
        for invariant_id, invariant in self.invariants.items():
            stats["invariants"][invariant_id] = {
                "description": invariant.description,
                "severity": invariant.severity.value,
                "violation_count": invariant.violation_count
            }
        
        return stats


# Core Invariant Implementations

class NoDirectMemoryWriteInvariant(SystemInvariant):
    """Hestia cannot write memory directly."""
    
    def __init__(self):
        super().__init__(
            invariant_id="NO_DIRECT_MEMORY_WRITE",
            description="Hestia cannot write memory directly; must use proposals",
            severity=InvariantSeverity.FATAL
        )
    
    def check(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        module = context.get("module", "")
        operation = context.get("operation", "")
        
        if module == "hestia" and operation in ["memory_write", "direct_memory_update"]:
            return InvariantViolation(
                invariant_id=self.invariant_id,
                severity=self.severity,
                module=module,
                operation=operation,
                context=context,
                timestamp=__import__("datetime").datetime.now().isoformat()
            )
        return None


class NoPreferenceInferenceInvariant(SystemInvariant):
    """Athena cannot infer preferences."""
    
    def __init__(self):
        super().__init__(
            invariant_id="NO_PREFERENCE_INFERENCE",
            description="Athena cannot infer or store personal preferences",
            severity=InvariantSeverity.CRITICAL
        )
    
    def check(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        module = context.get("module", "")
        operation = context.get("operation", "")
        data = context.get("data", {})
        
        if module == "athena" and "preference" in str(data).lower():
            return InvariantViolation(
                invariant_id=self.invariant_id,
                severity=self.severity,
                module=module,
                operation=operation,
                context=context,
                timestamp=__import__("datetime").datetime.now().isoformat()
            )
        return None


class NoTransactionExecutionInvariant(SystemInvariant):
    """Pluto cannot execute transactions."""
    
    def __init__(self):
        super().__init__(
            invariant_id="NO_TRANSACTION_EXECUTION",
            description="Pluto cannot execute financial transactions",
            severity=InvariantSeverity.FATAL
        )
    
    def check(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        module = context.get("module", "")
        operation = context.get("operation", "")
        
        if module == "pluto" and "execute_transaction" in operation:
            return InvariantViolation(
                invariant_id=self.invariant_id,
                severity=self.severity,
                module=module,
                operation=operation,
                context=context,
                timestamp=__import__("datetime").datetime.now().isoformat()
            )
        return None


class NoBehavioralSelfPromotionInvariant(SystemInvariant):
    """Behavioral memory cannot self-promote."""
    
    def __init__(self):
        super().__init__(
            invariant_id="NO_BEHAVIORAL_SELF_PROMOTION",
            description="Behavioral memory patterns cannot promote themselves",
            severity=InvariantSeverity.CRITICAL
        )
    
    def check(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        memory_type = context.get("memory_type", "")
        operation = context.get("operation", "")
        
        if memory_type == "behavioral" and operation == "self_promote":
            return InvariantViolation(
                invariant_id=self.invariant_id,
                severity=self.severity,
                module=context.get("module", "unknown"),
                operation=operation,
                context=context,
                timestamp=__import__("datetime").datetime.now().isoformat()
            )
        return None


class IdentityMemoryImmutableInvariant(SystemInvariant):
    """Identity memory cannot be modified."""
    
    def __init__(self):
        super().__init__(
            invariant_id="IDENTITY_MEMORY_IMMUTABLE",
            description="Identity memory is immutable; only new versions can be created",
            severity=InvariantSeverity.FATAL
        )
    
    def check(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        memory_type = context.get("memory_type", "")
        operation = context.get("operation", "")
        
        if memory_type == "identity" and operation in ["update", "modify", "delete"]:
            return InvariantViolation(
                invariant_id=self.invariant_id,
                severity=self.severity,
                module=context.get("module", "unknown"),
                operation=operation,
                context=context,
                timestamp=__import__("datetime").datetime.now().isoformat()
            )
        return None


class NoDirectLLMAccessInvariant(SystemInvariant):
    """No module may call Ollama directly (except Hestia)."""
    
    def __init__(self):
        super().__init__(
            invariant_id="NO_DIRECT_LLM_ACCESS",
            description="Only Hestia may call Ollama directly",
            severity=InvariantSeverity.FATAL
        )
    
    def check(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        module = context.get("module", "")
        operation = context.get("operation", "")
        
        if module != "hestia" and "ollama" in operation.lower():
            return InvariantViolation(
                invariant_id=self.invariant_id,
                severity=self.severity,
                module=module,
                operation=operation,
                context=context,
                timestamp=__import__("datetime").datetime.now().isoformat()
            )
        return None


class PermissionBypassInvariant(SystemInvariant):
    """No module may bypass Hearth permissions."""
    
    def __init__(self):
        super().__init__(
            invariant_id="NO_PERMISSION_BYPASS",
            description="All operations must go through Hearth permission system",
            severity=InvariantSeverity.FATAL
        )
    
    def check(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        operation = context.get("operation", "")
        permission_check = context.get("permission_check", True)
        
        if not permission_check and "bypass" not in operation:
            return InvariantViolation(
                invariant_id=self.invariant_id,
                severity=self.severity,
                module=context.get("module", "unknown"),
                operation=operation,
                context=context,
                timestamp=__import__("datetime").datetime.now().isoformat()
            )
        return None


class NoAutonomousExecutionInvariant(SystemInvariant):
    """No autonomous execution."""
    
    def __init__(self):
        super().__init__(
            invariant_id="NO_AUTONOMOUS_EXECUTION",
            description="No module may execute actions without explicit user intent",
            severity=InvariantSeverity.FATAL
        )
    
    def check(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        trigger = context.get("trigger", "")
        user_intent = context.get("user_intent", False)
        
        if trigger == "autonomous" and not user_intent:
            return InvariantViolation(
                invariant_id=self.invariant_id,
                severity=self.severity,
                module=context.get("module", "unknown"),
                operation=context.get("operation", ""),
                context=context,
                timestamp=__import__("datetime").datetime.now().isoformat()
            )
        return None


class NoCloudAPIsInvariant(SystemInvariant):
    """No cloud APIs."""
    
    def __init__(self):
        super().__init__(
            invariant_id="NO_CLOUD_APIS",
            description="No external cloud API calls allowed",
            severity=InvariantSeverity.FATAL
        )
    
    def check(self, context: Dict[str, Any]) -> Optional[InvariantViolation]:
        operation = context.get("operation", "")
        target = context.get("target", "")
        
        cloud_domains = ["api.", "cloud.", "aws.", "azure.", "gcp.", "openai.", "google."]
        
        if any(domain in target.lower() for domain in cloud_domains):
            return InvariantViolation(
                invariant_id=self.invariant_id,
                severity=self.severity,
                module=context.get("module", "unknown"),
                operation=operation,
                context=context,
                timestamp=__import__("datetime").datetime.now().isoformat()
            )
        return None


# Exception classes

class InvariantViolationError(Exception):
    """Raised when an invariant is violated."""
    
    def __init__(self, violations: List[InvariantViolation]):
        self.violations = violations
        messages = [f"{v.invariant_id}: {v.severity.value}" for v in violations]
        super().__init__(f"Invariant violations: {', '.join(messages)}")


class FatalInvariantViolationError(InvariantViolationError):
    """Raised when a fatal invariant is violated."""
    
    def __init__(self, violations: List[InvariantViolation]):
        super().__init__(violations)
        self.message = "FATAL: System cannot continue in invalid state"


# Global invariant registry singleton
_invariant_registry: Optional[InvariantRegistry] = None

def get_invariant_registry() -> InvariantRegistry:
    """Get the global invariant registry (singleton)."""
    global _invariant_registry
    if _invariant_registry is None:
        _invariant_registry = InvariantRegistry()
    return _invariant_registry


# Decorator for invariant checking
def enforce_invariants(module: str, operation: str):
    """
    Decorator to enforce invariants on function execution.
    
    Usage:
        @enforce_invariants(module="hestia", operation="process_input")
        async def process_input(self, user_input):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            registry = get_invariant_registry()
            
            # Build context from function arguments
            context = {
                "function": func.__name__,
                "args": str(args)[:100],  # Truncate for safety
                "kwargs": str(kwargs)[:100],
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
            
            # Enforce invariants before execution
            registry.enforce(module, operation, context)
            
            # Execute function
            return func(*args, **kwargs)
        
        # For async functions
        async def async_wrapper(*args, **kwargs):
            registry = get_invariant_registry()
            
            context = {
                "function": func.__name__,
                "args": str(args)[:100],
                "kwargs": str(kwargs)[:100],
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
            
            registry.enforce(module, operation, context)
            return await func(*args, **kwargs)
        
        return async_wrapper if __import__("inspect").iscoroutinefunction(func) else wrapper
    
    return decorator