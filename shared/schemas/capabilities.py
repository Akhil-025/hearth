"""
Capability Declarations - Explicit service capability declarations.

Every service must declare:
- Allowed capabilities
- Explicit forbidden actions
- Resource requirements
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID

from pydantic import BaseModel, Field


class CapabilityType(Enum):
    """Types of capabilities."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    INFERENCE = "inference"
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"


class ResourceRequirement(Enum):
    """Resource requirements for capabilities."""
    MEMORY_ACCESS = "memory_access"
    KNOWLEDGE_ACCESS = "knowledge_access"
    LLM_ACCESS = "llm_access"
    PERMISSION_CHECK = "permission_check"
    USER_CONFIRMATION = "user_confirmation"


class CapabilityDeclaration(BaseModel):
    """Declaration of a single capability."""
    name: str
    description: str
    capability_type: CapabilityType
    
    # Allowed operations
    allowed_operations: List[str] = Field(default_factory=list)
    
    # Explicitly forbidden operations
    forbidden_operations: List[str] = Field(default_factory=list)
    
    # Resource requirements
    requires_resources: Set[ResourceRequirement] = Field(default_factory=set)
    
    # Constraints and limits
    constraints: Dict[str, any] = Field(default_factory=dict)
    
    # Validation rules (JSON Schema)
    validation_schema: Optional[Dict[str, any]] = None
    
    class Config:
        use_enum_values = True


class ServiceCapabilities(BaseModel):
    """Complete capability declaration for a service."""
    service_name: str
    service_version: str
    
    # Service identifier
    service_id: UUID = Field(default_factory=UUID)
    
    # Declared capabilities
    capabilities: List[CapabilityDeclaration] = Field(default_factory=list)
    
    # Global constraints
    global_constraints: Dict[str, any] = Field(default_factory=dict)
    
    # Audit trail
    declared_at: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())
    updated_at: Optional[str] = None
    
    class Config:
        use_enum_values = True


class CapabilityValidationError(Exception):
    """Raised when a capability validation fails."""
    pass


class CapabilityRegistry:
    """
    Registry for service capability declarations.
    
    Validates service behavior against declared capabilities.
    """
    
    def __init__(self):
        self.declarations: Dict[str, ServiceCapabilities] = {}
        self.logger = __import__("..logging.structured_logger", fromlist=["StructuredLogger"]).StructuredLogger(__name__)
        
        self.logger.info("Capability registry initialized")
    
    def register(self, declaration: ServiceCapabilities) -> None:
        """Register a service's capability declaration."""
        service_name = declaration.service_name
        
        if service_name in self.declarations:
            # Update existing declaration
            old_declaration = self.declarations[service_name]
            declaration.updated_at = __import__("datetime").datetime.now().isoformat()
            
            # Check for capability reduction (safety check)
            old_capabilities = {c.name for c in old_declaration.capabilities}
            new_capabilities = {c.name for c in declaration.capabilities}
            
            removed_capabilities = old_capabilities - new_capabilities
            if removed_capabilities:
                self.logger.warning(
                    "Service capabilities reduced",
                    service_name=service_name,
                    removed_capabilities=list(removed_capabilities)
                )
        
        self.declarations[service_name] = declaration
        
        self.logger.info(
            "Capabilities registered",
            service_name=service_name,
            capability_count=len(declaration.capabilities)
        )
    
    def validate_operation(
        self,
        service_name: str,
        operation: str,
        context: Optional[Dict[str, any]] = None
    ) -> Dict[str, any]:
        """
        Validate an operation against declared capabilities.
        
        Returns:
            Validation result with details
        """
        if service_name not in self.declarations:
            return {
                "valid": False,
                "reason": f"Service '{service_name}' not registered",
                "allowed": False
            }
        
        declaration = self.declarations[service_name]
        context = context or {}
        
        # Check global constraints first
        if not self._check_global_constraints(declaration.global_constraints, context):
            return {
                "valid": False,
                "reason": "Violates global constraints",
                "allowed": False,
                "constraint_violation": True
            }
        
        # Find relevant capability
        relevant_capability = None
        for capability in declaration.capabilities:
            if operation in capability.allowed_operations:
                relevant_capability = capability
                break
        
        if not relevant_capability:
            # Check if operation is explicitly forbidden
            for capability in declaration.capabilities:
                if operation in capability.forbidden_operations:
                    return {
                        "valid": False,
                        "reason": f"Operation '{operation}' is explicitly forbidden",
                        "allowed": False,
                        "explicitly_forbidden": True
                    }
            
            # Operation not declared
            return {
                "valid": False,
                "reason": f"Operation '{operation}' not declared in capabilities",
                "allowed": False,
                "undeclared_operation": True
            }
        
        # Validate against capability constraints
        constraint_check = self._check_constraints(
            relevant_capability.constraints,
            context
        )
        
        if not constraint_check["valid"]:
            return {
                "valid": False,
                "reason": f"Violates capability constraints: {constraint_check['reason']}",
                "allowed": False,
                "capability_name": relevant_capability.name,
                "constraint_details": constraint_check.get("details")
            }
        
        # Validate input against schema if provided
        if relevant_capability.validation_schema and "input" in context:
            schema_check = self._validate_against_schema(
                relevant_capability.validation_schema,
                context["input"]
            )
            
            if not schema_check["valid"]:
                return {
                    "valid": False,
                    "reason": f"Input validation failed: {schema_check['reason']}",
                    "allowed": False,
                    "capability_name": relevant_capability.name,
                    "validation_errors": schema_check.get("errors")
                }
        
        # Check resource requirements
        missing_resources = self._check_resource_requirements(
            relevant_capability.requires_resources,
            context
        )
        
        if missing_resources:
            return {
                "valid": False,
                "reason": f"Missing required resources: {missing_resources}",
                "allowed": False,
                "capability_name": relevant_capability.name,
                "missing_resources": missing_resources
            }
        
        # Operation is valid and allowed
        return {
            "valid": True,
            "reason": "Operation permitted by declared capabilities",
            "allowed": True,
            "capability_name": relevant_capability.name,
            "requires_confirmation": ResourceRequirement.USER_CONFIRMATION in relevant_capability.requires_resources
        }
    
    def _check_global_constraints(
        self,
        constraints: Dict[str, any],
        context: Dict[str, any]
    ) -> bool:
        """Check global constraints."""
        if not constraints:
            return True
        
        # Check time-based constraints
        if "time_restrictions" in constraints:
            restrictions = constraints["time_restrictions"]
            current_hour = __import__("datetime").datetime.now().hour
            
            if "allowed_hours" in restrictions:
                allowed_hours = restrictions["allowed_hours"]
                if current_hour not in allowed_hours:
                    return False
            
            if "blocked_hours" in restrictions:
                blocked_hours = restrictions["blocked_hours"]
                if current_hour in blocked_hours:
                    return False
        
        # Check user context constraints
        if "user_context" in constraints:
            user_constraints = constraints["user_context"]
            
            if "required_session_state" in user_constraints:
                required_state = user_constraints["required_session_state"]
                session_state = context.get("session_state", {})
                
                for key, value in required_state.items():
                    if session_state.get(key) != value:
                        return False
        
        return True
    
    def _check_constraints(
        self,
        constraints: Dict[str, any],
        context: Dict[str, any]
    ) -> Dict[str, any]:
        """Check capability-specific constraints."""
        if not constraints:
            return {"valid": True}
        
        # Rate limiting constraints
        if "rate_limit" in constraints:
            rate_limit = constraints["rate_limit"]
            operation_count = context.get("operation_count", 0)
            time_window = context.get("time_window_seconds", 3600)
            
            if operation_count >= rate_limit:
                return {
                    "valid": False,
                    "reason": f"Rate limit exceeded: {operation_count}/{rate_limit} per {time_window}s",
                    "details": {"rate_limit": rate_limit, "current_count": operation_count}
                }
        
        # Input size constraints
        if "max_input_size" in constraints:
            max_size = constraints["max_input_size"]
            input_data = context.get("input", "")
            input_size = len(str(input_data))
            
            if input_size > max_size:
                return {
                    "valid": False,
                    "reason": f"Input too large: {input_size}/{max_size}",
                    "details": {"max_size": max_size, "actual_size": input_size}
                }
        
        # Confidence threshold constraints
        if "min_confidence" in constraints:
            min_confidence = constraints["min_confidence"]
            confidence = context.get("confidence", 1.0)
            
            if confidence < min_confidence:
                return {
                    "valid": False,
                    "reason": f"Confidence too low: {confidence:.2f}/{min_confidence:.2f}",
                    "details": {"min_confidence": min_confidence, "actual_confidence": confidence}
                }
        
        return {"valid": True}
    
    def _validate_against_schema(
        self,
        schema: Dict[str, any],
        data: any
    ) -> Dict[str, any]:
        """Validate data against JSON Schema."""
        try:
            import jsonschema
            jsonschema.validate(instance=data, schema=schema)
            return {"valid": True}
        except ImportError:
            # Fallback simple validation if jsonschema not available
            self.logger.warning("jsonschema not available, using fallback validation")
            return self._simple_schema_validation(schema, data)
        except jsonschema.ValidationError as e:
            return {
                "valid": False,
                "reason": f"Schema validation failed: {e.message}",
                "errors": [str(e)]
            }
    
    def _simple_schema_validation(
        self,
        schema: Dict[str, any],
        data: any
    ) -> Dict[str, any]:
        """Simple fallback schema validation."""
        errors = []
        
        # Check required fields
        if "required" in schema:
            required_fields = schema["required"]
            if isinstance(data, dict):
                for field in required_fields:
                    if field not in data:
                        errors.append(f"Missing required field: {field}")
        
        # Check type constraints
        if "type" in schema:
            expected_type = schema["type"]
            
            if expected_type == "string" and not isinstance(data, str):
                errors.append(f"Expected string, got {type(data).__name__}")
            elif expected_type == "object" and not isinstance(data, dict):
                errors.append(f"Expected object/dict, got {type(data).__name__}")
            elif expected_type == "array" and not isinstance(data, list):
                errors.append(f"Expected array/list, got {type(data).__name__}")
            elif expected_type == "number" and not isinstance(data, (int, float)):
                errors.append(f"Expected number, got {type(data).__name__}")
            elif expected_type == "boolean" and not isinstance(data, bool):
                errors.append(f"Expected boolean, got {type(data).__name__}")
        
        if errors:
            return {
                "valid": False,
                "reason": f"Schema validation failed: {errors[0]}",
                "errors": errors
            }
        
        return {"valid": True}
    
    def _check_resource_requirements(
        self,
        requirements: Set[ResourceRequirement],
        context: Dict[str, any]
    ) -> List[str]:
        """Check if required resources are available."""
        missing = []
        
        for requirement in requirements:
            if requirement == ResourceRequirement.MEMORY_ACCESS:
                memory_available = context.get("memory_access", False)
                if not memory_available:
                    missing.append("memory_access")
            
            elif requirement == ResourceRequirement.KNOWLEDGE_ACCESS:
                knowledge_available = context.get("knowledge_access", False)
                if not knowledge_available:
                    missing.append("knowledge_access")
            
            elif requirement == ResourceRequirement.LLM_ACCESS:
                llm_available = context.get("llm_access", False)
                if not llm_available:
                    missing.append("llm_access")
            
            elif requirement == ResourceRequirement.PERMISSION_CHECK:
                permission_granted = context.get("permission_granted", False)
                if not permission_granted:
                    missing.append("permission_check")
            
            elif requirement == ResourceRequirement.USER_CONFIRMATION:
                user_confirmed = context.get("user_confirmed", False)
                if not user_confirmed:
                    missing.append("user_confirmation")
        
        return missing
    
    def get_service_capabilities(self, service_name: str) -> Optional[ServiceCapabilities]:
        """Get capability declaration for a service."""
        return self.declarations.get(service_name)
    
    def list_services(self) -> List[str]:
        """List all registered services."""
        return list(self.declarations.keys())
    
    def enforce_capability(
        self,
        service_name: str,
        operation: str,
        context: Optional[Dict[str, any]] = None
    ) -> None:
        """
        Enforce capability validation.
        
        Raises:
            CapabilityValidationError: If operation is not allowed
        """
        validation = self.validate_operation(service_name, operation, context)
        
        if not validation["valid"]:
            raise CapabilityValidationError(
                f"Capability validation failed for {service_name}.{operation}: {validation['reason']}"
            )


# Global capability registry singleton
_capability_registry: Optional[CapabilityRegistry] = None

def get_capability_registry() -> CapabilityRegistry:
    """Get the global capability registry (singleton)."""
    global _capability_registry
    if _capability_registry is None:
        _capability_registry = CapabilityRegistry()
    return _capability_registry


# Decorator for capability validation
def validate_capability(service_name: str, operation: str):
    """
    Decorator to validate operations against declared capabilities.
    
    Usage:
        @validate_capability(service_name="hestia", operation="process_input")
        async def process_input(self, user_input):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            registry = get_capability_registry()
            
            # Build context from function arguments
            context = {
                "function": func.__name__,
                "args": str(args)[:100],
                "kwargs": str(kwargs)[:100],
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
            
            # Validate capability
            registry.enforce_capability(service_name, operation, context)
            
            return func(*args, **kwargs)
        
        async def async_wrapper(*args, **kwargs):
            registry = get_capability_registry()
            
            context = {
                "function": func.__name__,
                "args": str(args)[:100],
                "kwargs": str(kwargs)[:100],
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
            
            registry.enforce_capability(service_name, operation, context)
            return await func(*args, **kwargs)
        
        return async_wrapper if __import__("inspect").iscoroutinefunction(func) else wrapper
    
    return decorator


# Example capability declarations for core services

def create_hestia_capabilities() -> ServiceCapabilities:
    """Create capability declaration for Hestia service."""
    return ServiceCapabilities(
        service_name="hestia",
        service_version="0.2.0",
        capabilities=[
            CapabilityDeclaration(
                name="user_interaction",
                description="Process user input and generate responses",
                capability_type=CapabilityType.EXECUTE,
                allowed_operations=[
                    "process_input",
                    "generate_response",
                    "classify_intent",
                    "build_context"
                ],
                forbidden_operations=[
                    "direct_memory_write",
                    "direct_transaction_execution"
                ],
                requires_resources={
                    ResourceRequirement.LLM_ACCESS,
                    ResourceRequirement.MEMORY_ACCESS,
                    ResourceRequirement.PERMISSION_CHECK
                },
                constraints={
                    "rate_limit": 100,  # Max 100 operations per hour
                    "min_confidence": 0.3  # Minimum confidence threshold
                }
            ),
            CapabilityDeclaration(
                name="memory_proposal",
                description="Propose memory writes for review",
                capability_type=CapabilityType.WRITE,
                allowed_operations=[
                    "create_memory_proposal",
                    "submit_memory_proposal",
                    "review_memory_proposal"
                ],
                forbidden_operations=[
                    "direct_memory_write",
                    "bypass_memory_review"
                ],
                requires_resources={
                    ResourceRequirement.MEMORY_ACCESS,
                    ResourceRequirement.PERMISSION_CHECK,
                    ResourceRequirement.USER_CONFIRMATION
                },
                constraints={
                    "max_proposals_per_hour": 50,
                    "require_review_threshold": 0.7  # Confidence threshold requiring review
                }
            )
        ],
        global_constraints={
            "time_restrictions": {
                "allowed_hours": list(range(0, 24))  # 24/7 operation
            }
        }
    )


def create_mnemosyne_capabilities() -> ServiceCapabilities:
    """Create capability declaration for Mnemosyne service."""
    return ServiceCapabilities(
        service_name="mnemosyne",
        service_version="0.1.0",
        capabilities=[
            CapabilityDeclaration(
                name="memory_storage",
                description="Store and retrieve memories",
                capability_type=CapabilityType.WRITE,
                allowed_operations=[
                    "store_memory",
                    "retrieve_memory",
                    "query_memories",
                    "update_memory"
                ],
                forbidden_operations=[
                    "modify_identity_memory",
                    "autonomous_memory_deletion",
                    "bypass_encryption"
                ],
                requires_resources={
                    ResourceRequirement.PERMISSION_CHECK
                },
                constraints={
                    "max_memory_size_mb": 10,
                    "encryption_required": True
                }
            ),
            CapabilityDeclaration(
                name="memory_analysis",
                description="Analyze memory patterns and relationships",
                capability_type=CapabilityType.ANALYSIS,
                allowed_operations=[
                    "analyze_patterns",
                    "detect_contradictions",
                    "calculate_decay",
                    "generate_summaries"
                ],
                forbidden_operations=[
                    "infer_preferences",
                    "autonomous_promotion",
                    "behavior_manipulation"
                ],
                requires_resources=set(),
                constraints={
                    "analysis_interval_hours": 24,
                    "require_confirmation": True
                }
            )
        ]
    )