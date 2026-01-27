"""
Domain Permission Checker - Validates permissions for domain operations.
"""
from typing import Dict, List, Set
from uuid import UUID

from ..core.permission_manager import (
    PermissionManager,
    PermissionRequest,
    Resource,
    ResourceType,
    PermissionLevel
)
from ..shared.logging.structured_logger import StructuredLogger
from .base import DomainCapability


class DomainPermissionChecker:
    """
    Validates permissions for domain operations.
    
    Ensures domains only access resources they're authorized for.
    """
    
    def __init__(self, permission_manager: PermissionManager):
        self.permission_manager = permission_manager
        self.logger = StructuredLogger(__name__)
        
        # Capability to required permissions mapping
        self.capability_permissions: Dict[DomainCapability, Set[str]] = {
            # Hermes
            DomainCapability.DRAFT_MESSAGE: {"communication:write"},
            DomainCapability.ANALYZE_TONE: {"communication:read"},
            DomainCapability.CONVERSATION_ANALYSIS: {"communication:read", "memory:read"},
            
            # Hephaestus
            DomainCapability.CODE_ANALYSIS: {"code:read"},
            DomainCapability.SYSTEM_DESIGN: {"system:read", "system:write"},
            DomainCapability.TECH_STACK_PLANNING: {"system:read"},
            
            # Apollo
            DomainCapability.HABIT_ANALYSIS: {"health:read", "memory:read"},
            DomainCapability.ROUTINE_PLANNING: {"health:write", "schedule:write"},
            
            # Dionysus
            DomainCapability.MUSIC_RECOMMENDATION: {"entertainment:read"},
            DomainCapability.LEISURE_PLANNING: {"schedule:read", "entertainment:read"},
        }
        
        self.logger.info("Domain permission checker initialized")
    
    async def check_domain_permission(
        self,
        user_id: str,
        capability: DomainCapability,
        resource_id: Optional[UUID] = None,
        resource_path: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission for domain capability.
        
        Args:
            user_id: User identifier
            capability: Domain capability being requested
            resource_id: Specific resource ID (optional)
            resource_path: Resource path (optional)
        
        Returns:
            True if permission granted
        """
        # Get required permissions for capability
        required_perms = self.capability_permissions.get(capability, set())
        
        if not required_perms:
            # No specific permissions required
            return True
        
        # Determine resource type based on capability
        resource_type = self._map_capability_to_resource(capability)
        
        # Create resource identifier
        resource = Resource(
            type=resource_type,
            id=resource_id,
            path=resource_path
        )
        
        # Check each required permission
        for perm_action in required_perms:
            # Parse permission action (e.g., "communication:read" -> action="read")
            if ":" in perm_action:
                _, action = perm_action.split(":", 1)
            else:
                action = perm_action
            
            # Check permission
            has_perm = await self.permission_manager.check_permission(
                principal=user_id,
                resource=resource,
                action=action,
                min_level=PermissionLevel.READ
            )
            
            if not has_perm:
                self.logger.warning(
                    "Domain permission denied",
                    user_id=user_id,
                    capability=capability.value,
                    required_permission=perm_action,
                    resource_type=resource_type.value
                )
                return False
        
        self.logger.debug(
            "Domain permission granted",
            user_id=user_id,
            capability=capability.value
        )
        
        return True
    
    def _map_capability_to_resource(self, capability: DomainCapability) -> ResourceType:
        """Map domain capability to resource type."""
        capability_map = {
            # Hermes
            DomainCapability.DRAFT_MESSAGE: ResourceType.MEMORY_EPISODIC,
            DomainCapability.ANALYZE_TONE: ResourceType.MEMORY_EPISODIC,
            DomainCapability.CONVERSATION_ANALYSIS: ResourceType.MEMORY_EPISODIC,
            
            # Hephaestus
            DomainCapability.CODE_ANALYSIS: ResourceType.KNOWLEDGE_DOCUMENT,
            DomainCapability.SYSTEM_DESIGN: ResourceType.SYSTEM_CONFIG,
            
            # Apollo
            DomainCapability.HABIT_ANALYSIS: ResourceType.MEMORY_BEHAVIORAL,
            DomainCapability.ROUTINE_PLANNING: ResourceType.MEMORY_STRUCTURED,
            
            # Dionysus
            DomainCapability.MUSIC_RECOMMENDATION: ResourceType.MEMORY_STRUCTURED,
            DomainCapability.LEISURE_PLANNING: ResourceType.MEMORY_STRUCTURED,
        }
        
        return capability_map.get(
            capability,
            ResourceType.MEMORY_STRUCTURED  # Default
        )
    
    async def request_domain_permission(
        self,
        user_id: str,
        capability: DomainCapability,
        reason: str,
        duration_minutes: int = 60
    ) -> bool:
        """
        Request temporary permission for domain capability.
        
        Args:
            user_id: User identifier
            capability: Domain capability
            reason: Justification for permission
            duration_minutes: How long permission should last
        
        Returns:
            True if permission granted
        """
        from datetime import datetime, timedelta
        
        # Get required permissions
        required_perms = self.capability_permissions.get(capability, set())
        
        if not required_perms:
            return True  # No permissions required
        
        # Create permission requests
        resource_type = self._map_capability_to_resource(capability)
        
        for perm_action in required_perms:
            if ":" in perm_action:
                _, action = perm_action.split(":", 1)
            else:
                action = perm_action
            
            # Create permission request
            request = PermissionRequest(
                requester=user_id,
                resource=Resource(type=resource_type),
                action=action,
                level=PermissionLevel.READ,
                context={
                    "capability": capability.value,
                    "reason": reason,
                    "domain": "domain_request"
                },
                expires_at=datetime.now() + timedelta(minutes=duration_minutes)
            )
            
            # Submit request
            grant = await self.permission_manager.request_permission(request)
            
            if not grant:
                self.logger.warning(
                    "Domain permission request denied",
                    user_id=user_id,
                    capability=capability.value,
                    action=action
                )
                return False
        
        self.logger.info(
            "Domain permission granted temporarily",
            user_id=user_id,
            capability=capability.value,
            duration_minutes=duration_minutes
        )
        
        return True
    
    def get_capability_permissions(self, capability: DomainCapability) -> List[str]:
        """Get required permissions for a capability."""
        perms = self.capability_permissions.get(capability, set())
        return list(perms)
    
    async def validate_domain_access(
        self,
        user_id: str,
        domain_name: str,
        capabilities: List[DomainCapability]
    ) -> Dict[DomainCapability, bool]:
        """
        Validate access to multiple domain capabilities.
        
        Returns mapping of capability to access status.
        """
        results = {}
        
        for capability in capabilities:
            has_access = await self.check_domain_permission(
                user_id=user_id,
                capability=capability
            )
            results[capability] = has_access
        
        # Log overall access status
        granted = sum(1 for access in results.values() if access)
        total = len(results)
        
        self.logger.info(
            "Domain access validation complete",
            domain=domain_name,
            granted=granted,
            total=total,
            user_id=user_id
        )
        
        return results