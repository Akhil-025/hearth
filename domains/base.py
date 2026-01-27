"""
Domain Intelligence Base Interface
All domain modules must implement this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from ..core.kernel import IService, ServiceInfo, ServiceStatus
from ..shared.logging.structured_logger import StructuredLogger
from ..shared.schemas.memory import MemoryProposal, MemoryType


class DomainCapability(Enum):
    """Capabilities that domains can expose."""
    # Hermes
    DRAFT_MESSAGE = "draft_message"
    ANALYZE_TONE = "analyze_tone"
    SCHEDULE_PLANNING = "schedule_planning"
    CONVERSATION_ANALYSIS = "conversation_analysis"
    
    # Hephaestus
    CODE_ANALYSIS = "code_analysis"
    SYSTEM_DESIGN = "system_design"
    DEBUG_ASSISTANCE = "debug_assistance"
    TECH_STACK_PLANNING = "tech_stack_planning"
    
    # Apollo
    HABIT_ANALYSIS = "habit_analysis"
    HEALTH_PATTERN_MODELING = "health_pattern_modeling"
    ROUTINE_PLANNING = "routine_planning"
    RISK_FLAGGING = "risk_flagging"
    
    # Dionysus
    MOOD_ANALYSIS = "mood_analysis"
    MUSIC_RECOMMENDATION = "music_recommendation"
    LEISURE_PLANNING = "leisure_planning"
    CREATIVITY_PROMPTS = "creativity_prompts"


class DomainRequest(BaseModel):
    """Request to a domain module."""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    domain_name: str
    capability: DomainCapability
    user_id: str
    session_id: str
    input_data: Dict[str, Any]
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Permission context
    required_permissions: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class DomainResult(BaseModel):
    """Result from a domain module."""
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    domain_name: str
    capability: DomainCapability
    
    # Structured results (no prose)
    analysis: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    structured_output: Dict[str, Any] = Field(default_factory=dict)
    
    # Confidence and validation
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    validation_checks: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Memory proposals (to be reviewed by Hestia)
    memory_proposals: List[MemoryProposal] = Field(default_factory=list)
    
    # Metadata
    processing_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class DomainError(BaseModel):
    """Error from a domain module."""
    error_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    domain_name: str
    error_type: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    recoverable: bool = True


@dataclass
class DomainCapabilityInfo:
    """Information about a domain capability."""
    capability: DomainCapability
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    requires_memory_access: bool = False
    requires_knowledge_access: bool = False
    max_processing_time_ms: int = 5000


class IDomainModule(ABC):
    """
    Base interface for all domain intelligence modules.
    
    Rules:
    1. No direct user interaction
    2. No direct memory writes
    3. No direct LLM calls
    4. No autonomous execution
    5. Returns structured data only
    """
    
    @abstractmethod
    def get_domain_name(self) -> str:
        """Get the name of this domain."""
        pass
    
    @abstractmethod
    def get_domain_version(self) -> str:
        """Get the version of this domain."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[DomainCapabilityInfo]:
        """Get all capabilities exposed by this domain."""
        pass
    
    @abstractmethod
    def supports_capability(self, capability: DomainCapability) -> bool:
        """Check if domain supports a specific capability."""
        pass
    
    @abstractmethod
    async def process_request(self, request: DomainRequest) -> DomainResult:
        """
        Process a domain request.
        
        Must return structured results only.
        No prose, no direct actions.
        """
        pass
    
    @abstractmethod
    async def validate_input(self, capability: DomainCapability, input_data: Dict[str, Any]) -> List[str]:
        """Validate input data for a capability."""
        pass


class BaseDomainService(IService, IDomainModule):
    """
    Base implementation for domain services.
    Provides common functionality and enforces constraints.
    """
    
    def __init__(self, domain_name: str, domain_version: str):
        self.domain_name = domain_name
        self.domain_version = domain_version
        self.logger = StructuredLogger(f"domain.{domain_name}")
        
        # Capability registry
        self._capabilities: List[DomainCapabilityInfo] = []
        self._capability_map: Dict[DomainCapability, DomainCapabilityInfo] = {}
        
        # Service info for Hearth kernel
        self.service_info = ServiceInfo(
            name=f"domain_{domain_name}",
            version=domain_version,
            dependencies=["hestia"]  # All domains depend on Hestia
        )
        
        # Register capabilities
        self._register_capabilities()
        
        self.logger.info(
            f"{domain_name} domain initialized",
            version=domain_version,
            capabilities=[c.capability.value for c in self._capabilities]
        )
    
    def _register_capabilities(self) -> None:
        """Register domain capabilities. Override in subclasses."""
        pass
    
    def register_capability(self, capability_info: DomainCapabilityInfo) -> None:
        """Register a capability."""
        self._capabilities.append(capability_info)
        self._capability_map[capability_info.capability] = capability_info
        
        self.logger.debug(
            "Capability registered",
            capability=capability_info.capability.value,
            description=capability_info.description
        )
    
    def get_domain_name(self) -> str:
        return self.domain_name
    
    def get_domain_version(self) -> str:
        return self.domain_version
    
    def get_capabilities(self) -> List[DomainCapabilityInfo]:
        return self._capabilities.copy()
    
    def supports_capability(self, capability: DomainCapability) -> bool:
        return capability in self._capability_map
    
    async def start(self) -> None:
        """Start the domain service."""
        self.service_info.status = ServiceStatus.STARTING
        self.service_info.status = ServiceStatus.RUNNING
        self.logger.info(f"{self.domain_name} domain started")
    
    async def stop(self) -> None:
        """Stop the domain service."""
        self.service_info.status = ServiceStatus.STOPPING
        self.service_info.status = ServiceStatus.STOPPED
        self.logger.info(f"{self.domain_name} domain stopped")
    
    def get_service_info(self) -> ServiceInfo:
        return self.service_info
    
    async def health_check(self) -> bool:
        """Health check for domain service."""
        # Basic health check - verify capabilities are registered
        return len(self._capabilities) > 0
    
    async def process_request(self, request: DomainRequest) -> DomainResult:
        """
        Process a domain request with validation and error handling.
        
        This is the main entry point called by Hestia.
        """
        start_time = datetime.now()
        
        self.logger.info(
            "Processing domain request",
            request_id=request.request_id,
            capability=request.capability.value,
            user_id=request.user_id
        )
        
        # Validate request is for this domain
        if request.domain_name != self.domain_name:
            raise ValueError(
                f"Request for wrong domain: {request.domain_name} != {self.domain_name}"
            )
        
        # Check capability support
        if not self.supports_capability(request.capability):
            raise ValueError(
                f"Unsupported capability: {request.capability.value}"
            )
        
        # Validate input
        validation_errors = await self.validate_input(
            request.capability,
            request.input_data
        )
        
        if validation_errors:
            raise ValueError(
                f"Input validation failed: {validation_errors}"
            )
        
        try:
            # Process with capability-specific handler
            result = await self._process_capability(request)
            
            # Add processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result.processing_time_ms = processing_time
            
            self.logger.info(
                "Domain request processed",
                request_id=request.request_id,
                processing_time_ms=processing_time,
                confidence=result.confidence
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Domain processing failed",
                request_id=request.request_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _process_capability(self, request: DomainRequest) -> DomainResult:
        """
        Process specific capability. Override in subclasses.
        
        Must return structured DomainResult.
        """
        # This should be overridden by subclasses
        # For base class, return empty result
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=request.capability
        )
    
    async def validate_input(self, capability: DomainCapability, input_data: Dict[str, Any]) -> List[str]:
        """
        Validate input data for a capability.
        
        Returns list of validation errors (empty if valid).
        """
        errors = []
        
        # Get capability info
        if capability not in self._capability_map:
            errors.append(f"Unknown capability: {capability.value}")
            return errors
        
        capability_info = self._capability_map[capability]
        
        # Basic validation against schema
        # TODO: Implement JSON Schema validation
        required_fields = capability_info.input_schema.get("required", [])
        
        for field in required_fields:
            if field not in input_data:
                errors.append(f"Missing required field: {field}")
        
        return errors
    
    def _create_memory_proposal(
        self,
        memory_type: MemoryType,
        data: Dict[str, Any],
        reason: str,
        confidence: float = 0.8
    ) -> MemoryProposal:
        """Helper to create memory proposals (for Hestia to forward)."""
        from ..shared.schemas.memory import MemoryProposal
        
        return MemoryProposal(
            requester=self.domain_name,
            operation="CREATE",
            memory_type=memory_type,
            new_memory=data,
            reason=reason,
            confidence=confidence
        )