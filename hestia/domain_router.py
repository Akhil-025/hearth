"""
Hestia Domain Router - Routes requests to domain intelligence modules.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from ..core.service_registry import ServiceRegistry
from ..domains.base import (
    DomainCapability,
    DomainRequest,
    DomainResult,
    IDomainModule
)
from ..shared.logging.structured_logger import StructuredLogger


class DomainRoute(BaseModel):
    """Route configuration for domain capabilities."""
    capability: DomainCapability
    domain_name: str
    priority: int = 1  # Higher priority = tried first
    enabled: bool = True
    requires_permissions: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class DomainRouter:
    """
    Routes user requests to appropriate domain modules.
    
    Responsibilities:
    - Capability discovery
    - Domain selection
    - Permission checks
    - Result aggregation
    - Error handling
    """
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.logger = StructuredLogger(__name__)
        
        # Capability to domain routing table
        self.routes: Dict[DomainCapability, List[DomainRoute]] = {}
        
        # Domain cache
        self.domains: Dict[str, IDomainModule] = {}
        
        # Statistics
        self.stats = {
            "requests_routed": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "domain_usage": {}
        }
        
        self.logger.info("Domain router initialized")
    
    async def discover_domains(self) -> Dict[str, List[DomainCapability]]:
        """Discover available domains and their capabilities."""
        domains_capabilities = {}
        
        # Get all services with domain_ prefix
        services = self.service_registry.list_services()
        
        for service_name, service_type in services.items():
            if service_name.startswith("domain_"):
                try:
                    domain_service = self.service_registry.get(service_name, IDomainModule)
                    
                    # Cache domain
                    domain_name = domain_service.get_domain_name()
                    self.domains[domain_name] = domain_service
                    
                    # Get capabilities
                    capabilities = domain_service.get_capabilities()
                    capability_names = [c.capability for c in capabilities]
                    
                    domains_capabilities[domain_name] = capability_names
                    
                    # Build routing table
                    for capability_info in capabilities:
                        route = DomainRoute(
                            capability=capability_info.capability,
                            domain_name=domain_name,
                            requires_permissions=(
                                ["memory:read"] if capability_info.requires_memory_access else []
                            )
                        )
                        
                        if capability_info.capability not in self.routes:
                            self.routes[capability_info.capability] = []
                        
                        self.routes[capability_info.capability].append(route)
                        self.routes[capability_info.capability].sort(
                            key=lambda r: r.priority,
                            reverse=True
                        )
                    
                    self.logger.info(
                        "Domain discovered",
                        domain=domain_name,
                        capabilities=len(capability_names)
                    )
                    
                except (KeyError, TypeError) as e:
                    self.logger.warning(
                        "Failed to load domain service",
                        service_name=service_name,
                        error=str(e)
                    )
        
        # Log routing table
        for capability, routes in self.routes.items():
            self.logger.debug(
                "Routing configured",
                capability=capability.value,
                routes=[r.domain_name for r in routes]
            )
        
        return domains_capabilities
    
    def get_available_capabilities(self) -> List[DomainCapability]:
        """Get all available capabilities."""
        return list(self.routes.keys())
    
    def find_domain_for_capability(
        self,
        capability: DomainCapability
    ) -> Optional[str]:
        """Find the best domain for a capability."""
        if capability not in self.routes:
            return None
        
        # Get enabled routes sorted by priority
        enabled_routes = [
            r for r in self.routes[capability]
            if r.enabled
        ]
        
        if not enabled_routes:
            return None
        
        # Return highest priority domain
        return enabled_routes[0].domain_name
    
    async def route_to_domain(
        self,
        capability: DomainCapability,
        user_id: str,
        session_id: str,
        input_data: Dict[str, any],
        context: Optional[Dict[str, any]] = None
    ) -> DomainResult:
        """
        Route a request to the appropriate domain.
        
        Returns structured domain result.
        """
        self.stats["requests_routed"] += 1
        
        # Find domain
        domain_name = self.find_domain_for_capability(capability)
        
        if not domain_name:
            self.stats["failed_routes"] += 1
            raise ValueError(f"No domain found for capability: {capability.value}")
        
        # Get domain service
        if domain_name not in self.domains:
            # Try to get from service registry
            try:
                domain_service = self.service_registry.get(
                    f"domain_{domain_name}",
                    IDomainModule
                )
                self.domains[domain_name] = domain_service
            except (KeyError, TypeError):
                self.stats["failed_routes"] += 1
                raise ValueError(f"Domain not available: {domain_name}")
        
        domain_service = self.domains[domain_name]
        
        # Check capability support
        if not domain_service.supports_capability(capability):
            self.stats["failed_routes"] += 1
            raise ValueError(
                f"Domain {domain_name} doesn't support capability: {capability.value}"
            )
        
        # Create domain request
        request = DomainRequest(
            domain_name=domain_name,
            capability=capability,
            user_id=user_id,
            session_id=session_id,
            input_data=input_data,
            context=context or {}
        )
        
        self.logger.info(
            "Routing to domain",
            capability=capability.value,
            domain=domain_name,
            user_id=user_id
        )
        
        try:
            # Process request
            result = await domain_service.process_request(request)
            
            # Update statistics
            self.stats["successful_routes"] += 1
            self.stats["domain_usage"][domain_name] = (
                self.stats["domain_usage"].get(domain_name, 0) + 1
            )
            
            self.logger.debug(
                "Domain processing complete",
                domain=domain_name,
                processing_time_ms=result.processing_time_ms,
                confidence=result.confidence
            )
            
            return result
            
        except Exception as e:
            self.stats["failed_routes"] += 1
            self.logger.error(
                "Domain processing failed",
                domain=domain_name,
                capability=capability.value,
                error=str(e)
            )
            raise
    
    async def route_with_fallback(
        self,
        capability: DomainCapability,
        user_id: str,
        session_id: str,
        input_data: Dict[str, any],
        context: Optional[Dict[str, any]] = None
    ) -> DomainResult:
        """
        Route with fallback through multiple domains.
        
        Tries domains in priority order until one succeeds.
        """
        if capability not in self.routes:
            raise ValueError(f"No routes for capability: {capability.value}")
        
        # Get enabled routes in priority order
        routes = [
            r for r in self.routes[capability]
            if r.enabled
        ]
        
        if not routes:
            raise ValueError(f"No enabled routes for capability: {capability.value}")
        
        errors = []
        
        for route in routes:
            try:
                result = await self.route_to_domain(
                    capability=capability,
                    user_id=user_id,
                    session_id=session_id,
                    input_data=input_data,
                    context=context
                )
                return result
                
            except Exception as e:
                errors.append({
                    "domain": route.domain_name,
                    "error": str(e)
                })
                continue
        
        # All routes failed
        self.logger.error(
            "All domain routes failed",
            capability=capability.value,
            errors=errors
        )
        
        raise RuntimeError(
            f"All domains failed for {capability.value}. Errors: {errors}"
        )
    
    def get_domain_capabilities(self, domain_name: str) -> List[DomainCapability]:
        """Get capabilities provided by a specific domain."""
        capabilities = []
        
        for capability, routes in self.routes.items():
            for route in routes:
                if route.domain_name == domain_name and route.enabled:
                    capabilities.append(capability)
                    break
        
        return capabilities
    
    def enable_domain(self, domain_name: str, enabled: bool = True) -> bool:
        """Enable or disable a domain."""
        domain_affected = False
        
        for capability, routes in self.routes.items():
            for route in routes:
                if route.domain_name == domain_name:
                    route.enabled = enabled
                    domain_affected = True
        
        if domain_affected:
            status = "enabled" if enabled else "disabled"
            self.logger.info(f"Domain {status}", domain=domain_name)
        
        return domain_affected
    
    def get_router_stats(self) -> Dict[str, any]:
        """Get router statistics."""
        return {
            **self.stats,
            "total_domains": len(self.domains),
            "total_capabilities": len(self.routes),
            "success_rate": (
                self.stats["successful_routes"] / 
                max(self.stats["requests_routed"], 1)
            )
        }