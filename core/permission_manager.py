"""
Permission Manager - Fine-grained access control.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field, validator

from ..shared.crypto.encryption import encrypt_data, decrypt_data
from ..shared.logging.structured_logger import StructuredLogger


class PermissionLevel(Enum):
    """Permission levels."""
    NONE = 0
    READ = 1
    WRITE = 2
    ADMIN = 3


class ResourceType(Enum):
    """Resource types for permission management."""
    MEMORY_IDENTITY = "memory:identity"
    MEMORY_STRUCTURED = "memory:structured"
    MEMORY_EPISODIC = "memory:episodic"
    MEMORY_BEHAVIORAL = "memory:behavioral"
    KNOWLEDGE_DOCUMENT = "knowledge:document"
    FINANCIAL_LEDGER = "financial:ledger"
    FINANCIAL_BUDGET = "financial:budget"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_AUDIT = "system:audit"


@dataclass
class Resource:
    """Resource identifier."""
    type: ResourceType
    id: Optional[str] = None
    path: Optional[str] = None


class PermissionRequest(BaseModel):
    """Permission request model."""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    requester: str
    resource: Resource
    action: str
    level: PermissionLevel
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ResourceType: lambda rt: rt.value,
            PermissionLevel: lambda pl: pl.value
        }


class PermissionGrant(BaseModel):
    """Permission grant model."""
    grant_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    resource: Resource
    action: str
    level: PermissionLevel
    granted_to: str
    granted_by: str
    granted_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    conditions: Dict[str, Any] = Field(default_factory=dict)
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if grant is still valid."""
        if self.revoked:
            return False
        
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        
        return True


class IPermissionPolicy(ABC):
    """Permission policy interface."""
    
    @abstractmethod
    async def evaluate(
        self,
        request: PermissionRequest,
        existing_grants: List[PermissionGrant]
    ) -> bool:
        """Evaluate permission request against policy."""
        pass


class PermissionManager:
    """
    Central permission management with auditing.
    
    Features:
    - Role-based and attribute-based access control
    - Temporary permissions with expiration
    - Audit logging
    - Policy evaluation
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.logger = StructuredLogger(__name__)
        self.encryption_key = encryption_key
        
        # Storage
        self.grants: Dict[str, PermissionGrant] = {}
        self.policies: List[IPermissionPolicy] = []
        
        # Cache for performance
        self.grant_cache: Dict[str, List[PermissionGrant]] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.last_cache_update = datetime.now()
    
    def register_policy(self, policy: IPermissionPolicy) -> None:
        """Register a permission policy."""
        self.policies.append(policy)
        self.logger.debug("Permission policy registered", policy=type(policy).__name__)
    
    async def request_permission(self, request: PermissionRequest) -> Optional[PermissionGrant]:
        """Request and evaluate permission."""
        self.logger.info(
            "Permission request",
            request_id=request.request_id,
            requester=request.requester,
            resource=f"{request.resource.type}:{request.resource.id or request.resource.path}",
            action=request.action,
            level=request.level.value
        )
        
        # Check existing grants
        existing = self._get_grants_for_resource(request.resource, request.requester)
        
        # Check if existing grant covers request
        for grant in existing:
            if (grant.action == request.action and 
                grant.level.value >= request.level.value and
                grant.is_valid()):
                self.logger.debug(
                    "Existing grant found",
                    grant_id=grant.grant_id,
                    request_id=request.request_id
                )
                return grant
        
        # Evaluate policies
        policy_result = await self._evaluate_policies(request, existing)
        
        if not policy_result:
            self.logger.warning(
                "Permission denied by policy",
                request_id=request.request_id
            )
            return None
        
        # Create new grant
        grant = PermissionGrant(
            request_id=request.request_id,
            resource=request.resource,
            action=request.action,
            level=request.level,
            granted_to=request.requester,
            granted_by="system",  # TODO: Implement user authentication
            expires_at=request.expires_at,
            conditions=request.context
        )
        
        # Store grant
        self.grants[grant.grant_id] = grant
        self._invalidate_cache()
        
        self.logger.info(
            "Permission granted",
            grant_id=grant.grant_id,
            request_id=request.request_id
        )
        
        # Audit log
        await self._audit_grant(grant)
        
        return grant
    
    async def _evaluate_policies(
        self,
        request: PermissionRequest,
        existing_grants: List[PermissionGrant]
    ) -> bool:
        """Evaluate all registered policies."""
        if not self.policies:
            # Default policy: deny by default
            return False
        
        results = []
        for policy in self.policies:
            try:
                result = await policy.evaluate(request, existing_grants)
                results.append(result)
            except Exception as e:
                self.logger.error(
                    "Policy evaluation failed",
                    policy=type(policy).__name__,
                    error=str(e)
                )
                results.append(False)
        
        # All policies must approve
        return all(results)
    
    def _get_grants_for_resource(
        self,
        resource: Resource,
        principal: str
    ) -> List[PermissionGrant]:
        """Get valid grants for a resource and principal."""
        cache_key = f"{principal}:{resource.type.value}:{resource.id or resource.path}"
        
        # Check cache
        if (cache_key in self.grant_cache and 
            datetime.now() - self.last_cache_update < self.cache_ttl):
            return self.grant_cache[cache_key]
        
        # Query grants
        grants = []
        for grant in self.grants.values():
            if (grant.granted_to == principal and
                grant.resource.type == resource.type and
                (resource.id is None or grant.resource.id == resource.id) and
                (resource.path is None or grant.resource.path == resource.path) and
                grant.is_valid()):
                grants.append(grant)
        
        # Update cache
        self.grant_cache[cache_key] = grants
        self.last_cache_update = datetime.now()
        
        return grants
    
    async def check_permission(
        self,
        principal: str,
        resource: Resource,
        action: str,
        min_level: PermissionLevel = PermissionLevel.READ
    ) -> bool:
        """Check if principal has permission."""
        grants = self._get_grants_for_resource(resource, principal)
        
        for grant in grants:
            if (grant.action == action and 
                grant.level.value >= min_level.value and
                grant.is_valid()):
                return True
        
        return False
    
    async def revoke_permission(
        self,
        grant_id: str,
        revoked_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """Revoke a permission grant."""
        if grant_id not in self.grants:
            return False
        
        grant = self.grants[grant_id]
        
        if grant.revoked:
            return False
        
        grant.revoked = True
        grant.revoked_at = datetime.now()
        grant.revoked_by = revoked_by
        
        self._invalidate_cache()
        
        self.logger.info(
            "Permission revoked",
            grant_id=grant_id,
            revoked_by=revoked_by,
            reason=reason
        )
        
        # Audit log
        await self._audit_revocation(grant, reason)
        
        return True
    
    def revoke_all_for_principal(self, principal: str, revoked_by: str) -> int:
        """Revoke all grants for a principal."""
        revoked_count = 0
        
        for grant in self.grants.values():
            if grant.granted_to == principal and not grant.revoked:
                grant.revoked = True
                grant.revoked_at = datetime.now()
                grant.revoked_by = revoked_by
                revoked_count += 1
        
        if revoked_count > 0:
            self._invalidate_cache()
            self.logger.info(
                "All permissions revoked for principal",
                principal=principal,
                count=revoked_count
            )
        
        return revoked_count
    
    def get_active_grants(self, principal: Optional[str] = None) -> List[PermissionGrant]:
        """Get all active grants, optionally filtered by principal."""
        grants = []
        
        for grant in self.grants.values():
            if not grant.is_valid():
                continue
            
            if principal and grant.granted_to != principal:
                continue
            
            grants.append(grant)
        
        return grants
    
    async def _audit_grant(self, grant: PermissionGrant) -> None:
        """Audit permission grant."""
        audit_data = {
            "event": "permission_granted",
            "grant_id": grant.grant_id,
            "request_id": grant.request_id,
            "resource": {
                "type": grant.resource.type.value,
                "id": grant.resource.id,
                "path": grant.resource.path
            },
            "action": grant.action,
            "level": grant.level.value,
            "granted_to": grant.granted_to,
            "granted_by": grant.granted_by,
            "granted_at": grant.granted_at.isoformat(),
            "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
            "conditions": grant.conditions
        }
        
        # Encrypt sensitive data if encryption key is available
        if self.encryption_key:
            audit_data["encrypted"] = True
            audit_data = encrypt_data(json.dumps(audit_data), self.encryption_key)
        
        # TODO: Store in audit log
        self.logger.audit("Permission granted", **audit_data)
    
    async def _audit_revocation(
        self,
        grant: PermissionGrant,
        reason: Optional[str]
    ) -> None:
        """Audit permission revocation."""
        audit_data = {
            "event": "permission_revoked",
            "grant_id": grant.grant_id,
            "revoked_by": grant.revoked_by,
            "revoked_at": grant.revoked_at.isoformat() if grant.revoked_at else None,
            "reason": reason
        }
        
        if self.encryption_key:
            audit_data["encrypted"] = True
            audit_data = encrypt_data(json.dumps(audit_data), self.encryption_key)
        
        self.logger.audit("Permission revoked", **audit_data)
    
    def _invalidate_cache(self) -> None:
        """Invalidate grant cache."""
        self.grant_cache.clear()