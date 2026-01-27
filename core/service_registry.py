"""
HEARTH Service Registry - Minimal Stub (v0.1)

DISABLED IN v0.1  not part of execution spine
"""
from typing import Any, Dict


class ServiceRegistry:
    """Minimal noop service registry."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
