"""
HEARTH Kernel - Minimal Stub (v0.1)

DISABLED IN v0.1:
- Service lifecycle management
- Dependency resolution
- Health monitoring
- Graceful shutdown
- Audit logging
"""
from dataclasses import dataclass
from typing import Optional

# DISABLED IN v0.1  not part of execution spine
# from ..shared.logging.structured_logger import StructuredLogger
from .event_bus import EventBus
from .permission_manager import PermissionManager
from .config_loader import ConfigLoader
from .service_registry import ServiceRegistry


@dataclass
class KernelConfig:
    """Kernel configuration."""
    data_dir: str = "./data"
    log_level: str = "INFO"
    enable_audit: bool = False  # DISABLED IN v0.1
    require_permissions: bool = False  # DISABLED IN v0.1
    service_startup_timeout: int = 30
    service_shutdown_timeout: int = 10


class HearthKernel:
    """
    Minimal kernel - just holds configuration.
    
    FUTURE: Will manage services, dependencies, lifecycle, audit.
    """
    
    def __init__(self, config: Optional[KernelConfig] = None):
        self.config = config or KernelConfig()
        
        # DISABLED IN v0.1  minimal noop instances
        self.event_bus = EventBus()
        self.service_registry = ServiceRegistry()
        self.permission_manager = PermissionManager()
        self.config_loader = ConfigLoader()
        
        self.running = False
