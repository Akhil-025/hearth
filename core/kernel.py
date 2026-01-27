"""
HEARTH Kernel - Core runtime and orchestration engine.
"""
from __future__ import annotations

import asyncio
import logging
import signal
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Type

from pydantic import BaseModel, Field

from ..shared.logging.structured_logger import StructuredLogger
from .config_loader import ConfigLoader
from .event_bus import Event, EventBus
from .permission_manager import Permission, PermissionManager
from .service_registry import ServiceRegistry


class ServiceStatus(Enum):
    """Service lifecycle states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class ServiceInfo(BaseModel):
    """Service metadata."""
    name: str
    version: str
    dependencies: List[str] = Field(default_factory=list)
    status: ServiceStatus = ServiceStatus.STOPPED
    health_check_passed: bool = False
    last_error: Optional[str] = None


class IService(ABC):
    """Service interface for HEARTH modules."""
    
    @abstractmethod
    async def start(self) -> None:
        """Start the service."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the service."""
        pass
    
    @abstractmethod
    def get_service_info(self) -> ServiceInfo:
        """Get service metadata."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Perform health check."""
        pass


@dataclass
class KernelConfig:
    """Kernel configuration."""
    data_dir: str = "./data"
    log_level: str = "INFO"
    enable_audit: bool = True
    require_permissions: bool = True
    service_startup_timeout: int = 30
    service_shutdown_timeout: int = 10


class HearthKernel:
    """
    Main kernel orchestrating all HEARTH services.
    
    Responsibilities:
    - Service lifecycle management
    - Dependency resolution
    - Graceful shutdown
    - Health monitoring
    """
    
    def __init__(self, config: Optional[KernelConfig] = None):
        self.config = config or KernelConfig()
        self.logger = StructuredLogger(__name__)
        self.event_bus = EventBus()
        self.service_registry = ServiceRegistry()
        self.permission_manager = PermissionManager()
        self.config_loader = ConfigLoader()
        
        self.services: Dict[str, IService] = {}
        self.service_graph: Dict[str, Set[str]] = {}
        self.running = False
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        self.logger.info(
            "Kernel initialized",
            config=self.config.__dict__
        )
    
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_shutdown_signal)
    
    def _handle_shutdown_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        self.logger.warning(
            "Received shutdown signal",
            signal=signum,
            frame=frame
        )
        asyncio.create_task(self.shutdown())
    
    async def register_service(self, service: IService) -> None:
        """Register a service with the kernel."""
        service_info = service.get_service_info()
        
        if service_info.name in self.services:
            raise ValueError(f"Service already registered: {service_info.name}")
        
        self.services[service_info.name] = service
        self.service_graph[service_info.name] = set(service_info.dependencies)
        
        # Register service in registry
        self.service_registry.register(service_info.name, service)
        
        self.logger.info(
            "Service registered",
            service=service_info.name,
            dependencies=service_info.dependencies
        )
    
    def resolve_dependencies(self, service_name: str) -> List[str]:
        """
        Resolve service startup order using topological sort.
        
        Returns services in order of dependency.
        """
        visited = set()
        order = []
        
        def visit(node: str) -> None:
            if node in visited:
                return
            visited.add(node)
            
            for dependency in self.service_graph.get(node, set()):
                if dependency not in self.services:
                    raise ValueError(
                        f"Missing dependency: {dependency} for service {node}"
                    )
                visit(dependency)
            
            order.append(node)
        
        visit(service_name)
        return order
    
    async def start(self) -> None:
        """Start the kernel and all registered services."""
        if self.running:
            self.logger.warning("Kernel already running")
            return
        
        self.logger.info("Starting HEARTH kernel")
        self.running = True
        
        # Start services in dependency order
        all_services = list(self.services.keys())
        startup_order = []
        
        for service_name in all_services:
            startup_order.extend(self.resolve_dependencies(service_name))
        
        # Remove duplicates while preserving order
        startup_order = list(dict.fromkeys(startup_order))
        
        self.logger.debug(
            "Service startup order",
            order=startup_order
        )
        
        # Start each service
        for service_name in startup_order:
            service = self.services[service_name]
            
            try:
                self.logger.info(
                    "Starting service",
                    service=service_name
                )
                
                # Update status
                service_info = service.get_service_info()
                service_info.status = ServiceStatus.STARTING
                
                # Start service
                await asyncio.wait_for(
                    service.start(),
                    timeout=self.config.service_startup_timeout
                )
                
                # Health check
                healthy = await service.health_check()
                service_info.health_check_passed = healthy
                service_info.status = ServiceStatus.RUNNING
                
                if healthy:
                    self.logger.info(
                        "Service started successfully",
                        service=service_name
                    )
                else:
                    self.logger.error(
                        "Service health check failed",
                        service=service_name
                    )
                    raise RuntimeError(f"Health check failed for {service_name}")
                    
            except asyncio.TimeoutError:
                self.logger.error(
                    "Service startup timeout",
                    service=service_name,
                    timeout=self.config.service_startup_timeout
                )
                raise
            except Exception as e:
                self.logger.error(
                    "Failed to start service",
                    service=service_name,
                    error=str(e)
                )
                service_info.status = ServiceStatus.ERROR
                service_info.last_error = str(e)
                raise
        
        self.logger.info("HEARTH kernel started successfully")
    
    async def shutdown(self) -> None:
        """Shutdown the kernel and all services gracefully."""
        if not self.running:
            return
        
        self.logger.info("Shutting down HEARTH kernel")
        self.running = False
        
        # Shutdown services in reverse dependency order
        all_services = list(self.services.keys())
        
        for service_name in reversed(all_services):
            service = self.services[service_name]
            service_info = service.get_service_info()
            
            if service_info.status != ServiceStatus.RUNNING:
                continue
            
            try:
                self.logger.info(
                    "Stopping service",
                    service=service_name
                )
                
                service_info.status = ServiceStatus.STOPPING
                
                await asyncio.wait_for(
                    service.stop(),
                    timeout=self.config.service_shutdown_timeout
                )
                
                service_info.status = ServiceStatus.STOPPED
                self.logger.info(
                    "Service stopped",
                    service=service_name
                )
                
            except asyncio.TimeoutError:
                self.logger.error(
                    "Service shutdown timeout",
                    service=service_name
                )
            except Exception as e:
                self.logger.error(
                    "Error stopping service",
                    service=service_name,
                    error=str(e)
                )
        
        self.logger.info("HEARTH kernel shutdown complete")
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart a specific service and its dependents."""
        if service_name not in self.services:
            self.logger.error("Service not found", service=service_name)
            return False
        
        # Get all services that depend on this one
        dependents = [
            name for name, deps in self.service_graph.items()
            if service_name in deps
        ]
        
        services_to_restart = [service_name] + dependents
        
        self.logger.info(
            "Restarting services",
            services=services_to_restart
        )
        
        # Stop services in reverse order
        for name in reversed(services_to_restart):
            if name in self.services:
                await self.services[name].stop()
        
        # Start services in dependency order
        for name in services_to_restart:
            if name in self.services:
                await self.services[name].start()
        
        return True
    
    def get_kernel_status(self) -> Dict[str, Any]:
        """Get current kernel status."""
        services_status = {}
        
        for name, service in self.services.items():
            info = service.get_service_info()
            services_status[name] = {
                "status": info.status.value,
                "healthy": info.health_check_passed,
                "version": info.version,
                "last_error": info.last_error
            }
        
        return {
            "running": self.running,
            "services": services_status,
            "config": self.config.__dict__
        }
    
    @asynccontextmanager
    async def service_context(self, service_name: str) -> AsyncIterator[IService]:
        """Context manager for accessing services."""
        if service_name not in self.services:
            raise ValueError(f"Service not found: {service_name}")
        
        yield self.services[service_name]