"""
HEARTH Permission Manager - Minimal Stub (v0.1)

DISABLED IN v0.1  not part of execution spine
Security and permissions are explicitly disabled.
"""
from enum import Enum


class Permission(Enum):
    """Minimal permission enum for type compatibility."""
    READ = "read"
    WRITE = "write"


class PermissionManager:
    """
    Minimal noop permission manager.
    
    SECURITY DISABLED: All operations allowed in v0.1.
    """
    
    def __init__(self):
        pass
