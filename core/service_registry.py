"""
Service Registry - Central registry for service discovery.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar('T')


class ServiceRegistry:
    """
    Thread-safe service registry for dependency injection.
    
    Provides:
    - Service registration
    - Type-safe service retrieval
    - Optional service resolution
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._lock = threading.RLock()
    
    def register(self, name: str, service: Any) -> None:
        """Register a service with the registry."""
        with self._lock:
            if name in self._services:
                raise ValueError(f"Service already registered: {name}")
            
            self._services[name] = service
    
    def unregister(self, name: str) -> None:
        """Unregister a service."""
        with self._lock:
            if name in self._services:
                del self._services[name]
    
    def get(self, name: str, service_type: Optional[Type[T]] = None) -> T:
        """Get a service by name with optional type checking."""
        with self._lock:
            if name not in self._services:
                raise KeyError(f"Service not found: {name}")
            
            service = self._services[name]
            
            if service_type and not isinstance(service, service_type):
                raise TypeError(
                    f"Service {name} is not of type {service_type.__name__}"
                )
            
            return service
    
    def get_optional(self, name: str, service_type: Optional[Type[T]] = None) -> Optional[T]:
        """Get a service if it exists, otherwise return None."""
        try:
            return self.get(name, service_type)
        except KeyError:
            return None
    
    def has_service(self, name: str) -> bool:
        """Check if a service is registered."""
        with self._lock:
            return name in self._services
    
    def clear(self) -> None:
        """Clear all registered services."""
        with self._lock:
            self._services.clear()
    
    def list_services(self) -> Dict[str, str]:
        """List all registered services with their types."""
        with self._lock:
            return {
                name: type(service).__name__
                for name, service in self._services.items()
            }