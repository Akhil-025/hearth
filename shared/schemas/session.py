"""
Session Boundary Semantics - Defines session lifecycle and context boundaries.

Prevents cross-session leakage and manages ephemeral vs promotable context.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SessionType(Enum):
    """Types of sessions."""
    EPHEMERAL = "ephemeral"      # Short-lived, no persistence
    WORKING = "working"          # Working session, some persistence
    PERSISTENT = "persistent"    # Long-lived, full persistence
    REVIEW = "review"            # Review/audit session


class SessionState(Enum):
    """Session states."""
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class ContextBoundary(Enum):
    """Context boundary types."""
    SESSION_ONLY = "session_only"        # Never leaves session
    PROMOTABLE = "promotable"            # Can be promoted to long-term memory
    CROSS_SESSION = "cross_session"      # Can be shared across sessions
    NEVER_PERSIST = "never_persist"      # Must never be persisted


class SessionContext(BaseModel):
    """Session context with boundary semantics."""
    context_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    
    # Content
    content: Dict[str, any]
    content_hash: str
    
    # Boundaries
    boundary: ContextBoundary = ContextBoundary.SESSION_ONLY
    tags: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    accessed_at: datetime = Field(default_factory=datetime.now)
    access_count: int = 0
    
    # Relationships
    derived_from: Optional[List[UUID]] = Field(default_factory=list)
    promoted_to: Optional[UUID] = None
    
    class Config:
        use_enum_values = True


class Session(BaseModel):
    """Session definition with boundary semantics."""
    session_id: UUID = Field(default_factory=uuid4)
    user_id: str
    session_type: SessionType = SessionType.WORKING
    
    # State
    state: SessionState = SessionState.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    
    # Timeouts
    ttl_seconds: int = 3600  # Default: 1 hour
    max_duration_seconds: int = 86400  # Default: 24 hours
    
    # Boundaries
    allowed_boundaries: Set[ContextBoundary] = Field(default_factory=set)
    
    # Context management
    context_items: List[UUID] = Field(default_factory=list)
    promoted_context_count: int = 0
    
    # Metadata
    metadata: Dict[str, any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        now = datetime.now()
        age = now - self.last_activity
        
        if age.total_seconds() > self.ttl_seconds:
            return True
        
        total_duration = now - self.created_at
        if total_duration.total_seconds() > self.max_duration_seconds:
            return True
        
        return False
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def can_promote_context(self) -> bool:
        """Check if session allows context promotion."""
        return ContextBoundary.PROMOTABLE in self.allowed_boundaries
    
    def can_share_cross_session(self) -> bool:
        """Check if session allows cross-session context sharing."""
        return ContextBoundary.CROSS_SESSION in self.allowed_boundaries


class SessionManager:
    """
    Manages session boundaries and context isolation.
    
    Ensures:
    - No cross-session leakage
    - Proper context promotion
    - Session TTL enforcement
    - Ephemeral context cleanup
    """
    
    def __init__(self):
        self.logger = __import__("..logging.structured_logger", fromlist=["StructuredLogger"]).StructuredLogger(__name__)
        
        # Session storage
        self.sessions: Dict[UUID, Session] = {}
        self.session_contexts: Dict[UUID, SessionContext] = {}
        
        # User session mapping
        self.user_sessions: Dict[str, List[UUID]] = {}
        
        # Default session configurations
        self.default_configs: Dict[SessionType, Dict[str, any]] = {
            SessionType.EPHEMERAL: {
                "ttl_seconds": 300,  # 5 minutes
                "max_duration_seconds": 1800,  # 30 minutes
                "allowed_boundaries": {ContextBoundary.SESSION_ONLY}
            },
            SessionType.WORKING: {
                "ttl_seconds": 3600,  # 1 hour
                "max_duration_seconds": 28800,  # 8 hours
                "allowed_boundaries": {ContextBoundary.SESSION_ONLY, ContextBoundary.PROMOTABLE}
            },
            SessionType.PERSISTENT: {
                "ttl_seconds": 86400,  # 24 hours
                "max_duration_seconds": 604800,  # 7 days
                "allowed_boundaries": {ContextBoundary.SESSION_ONLY, ContextBoundary.PROMOTABLE, ContextBoundary.CROSS_SESSION}
            },
            SessionType.REVIEW: {
                "ttl_seconds": 7200,  # 2 hours
                "max_duration_seconds": 14400,  # 4 hours
                "allowed_boundaries": {ContextBoundary.SESSION_ONLY, ContextBoundary.CROSS_SESSION}
            }
        }
        
        self.logger.info("Session manager initialized")
    
    def create_session(
        self,
        user_id: str,
        session_type: SessionType = SessionType.WORKING,
        metadata: Optional[Dict[str, any]] = None
    ) -> Session:
        """Create a new session with appropriate boundaries."""
        # Get default configuration
        config = self.default_configs.get(session_type, self.default_configs[SessionType.WORKING])
        
        # Create session
        session = Session(
            user_id=user_id,
            session_type=session_type,
            ttl_seconds=config["ttl_seconds"],
            max_duration_seconds=config["max_duration_seconds"],
            allowed_boundaries=config["allowed_boundaries"],
            metadata=metadata or {}
        )
        
        # Store session
        self.sessions[session.session_id] = session
        
        # Update user session mapping
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session.session_id)
        
        self.logger.info(
            "Session created",
            session_id=str(session.session_id)[:8],
            user_id=user_id,
            session_type=session_type.value
        )
        
        return session
    
    def get_session(self, session_id: UUID) -> Optional[Session]:
        """Get a session by ID."""
        session = self.sessions.get(session_id)
        
        if session:
            # Check if expired
            if session.is_expired():
                session.state = SessionState.EXPIRED
                self.logger.debug(
                    "Session expired",
                    session_id=str(session_id)[:8]
                )
            
            # Update activity
            session.update_activity()
        
        return session
    
    def end_session(self, session_id: UUID, reason: str = "user_request") -> bool:
        """End a session and clean up ephemeral context."""
        session = self.sessions.get(session_id)
        if not session or session.state == SessionState.ENDED:
            return False
        
        # Clean up ephemeral context
        ephemeral_contexts = self._get_ephemeral_contexts(session_id)
        for context_id in ephemeral_contexts:
            if context_id in self.session_contexts:
                del self.session_contexts[context_id]
        
        # Update session state
        session.state = SessionState.ENDED
        
        self.logger.info(
            "Session ended",
            session_id=str(session_id)[:8],
            reason=reason,
            ephemeral_contexts_cleaned=len(ephemeral_contexts)
        )
        
        return True
    
    def add_context(
        self,
        session_id: UUID,
        content: Dict[str, any],
        boundary: ContextBoundary = ContextBoundary.SESSION_ONLY,
        tags: Optional[List[str]] = None
    ) -> Optional[UUID]:
        """Add context to a session with specified boundary."""
        session = self.get_session(session_id)
        if not session:
            self.logger.error("Session not found", session_id=str(session_id)[:8])
            return None
        
        # Check boundary compatibility
        if boundary not in session.allowed_boundaries:
            self.logger.warning(
                "Boundary not allowed for session",
                session_id=str(session_id)[:8],
                requested_boundary=boundary.value,
                allowed_boundaries=[b.value for b in session.allowed_boundaries]
            )
            # Downgrade to session-only if not allowed
            boundary = ContextBoundary.SESSION_ONLY
        
        # Create context hash
        import hashlib
        import json
        content_json = json.dumps(content, sort_keys=True)
        content_hash = hashlib.sha256(content_json.encode()).hexdigest()
        
        # Create context
        context = SessionContext(
            session_id=session_id,
            content=content,
            content_hash=content_hash,
            boundary=boundary,
            tags=tags or []
        )
        
        # Store context
        self.session_contexts[context.context_id] = context
        session.context_items.append(context.context_id)
        
        self.logger.debug(
            "Context added to session",
            session_id=str(session_id)[:8],
            context_id=str(context.context_id)[:8],
            boundary=boundary.value,
            content_keys=list(content.keys())
        )
        
        return context.context_id
    
    def get_context(
        self,
        session_id: UUID,
        context_id: UUID
    ) -> Optional[SessionContext]:
        """Get context from a session."""
        context = self.session_contexts.get(context_id)
        
        if not context or context.session_id != session_id:
            return None
        
        # Update access metadata
        context.accessed_at = datetime.now()
        context.access_count += 1
        
        return context
    
    def promote_context(
        self,
        session_id: UUID,
        context_id: UUID,
        target_memory_type: str
    ) -> Optional[UUID]:
        """
        Promote session context to long-term memory.
        
        Returns:
            Memory ID if promotion successful, None otherwise
        """
        session = self.get_session(session_id)
        context = self.get_context(session_id, context_id)
        
        if not session or not context:
            return None
        
        # Check if promotion is allowed
        if context.boundary not in [ContextBoundary.PROMOTABLE, ContextBoundary.CROSS_SESSION]:
            self.logger.warning(
                "Context not promotable",
                session_id=str(session_id)[:8],
                context_id=str(context_id)[:8],
                boundary=context.boundary.value
            )
            return None
        
        # Create memory proposal (will be handled by Hestia)
        # This is a simplified version - actual implementation would
        # create a memory proposal for Hestia to process
        
        # Generate memory ID
        memory_id = uuid4()
        
        # Update context
        context.promoted_to = memory_id
        session.promoted_context_count += 1
        
        self.logger.info(
            "Context promoted to memory",
            session_id=str(session_id)[:8],
            context_id=str(context_id)[:8],
            memory_id=str(memory_id)[:8],
            memory_type=target_memory_type
        )
        
        return memory_id
    
    def share_context_across_sessions(
        self,
        source_session_id: UUID,
        target_session_id: UUID,
        context_id: UUID
    ) -> Optional[UUID]:
        """Share context from one session to another."""
        source_session = self.get_session(source_session_id)
        target_session = self.get_session(target_session_id)
        context = self.get_context(source_session_id, context_id)
        
        if not source_session or not target_session or not context:
            return None
        
        # Check if cross-session sharing is allowed
        if context.boundary != ContextBoundary.CROSS_SESSION:
            self.logger.warning(
                "Context not shareable across sessions",
                context_id=str(context_id)[:8],
                boundary=context.boundary.value
            )
            return None
        
        # Create new context in target session (derived from source)
        new_context = SessionContext(
            session_id=target_session_id,
            content=context.content,
            content_hash=context.content_hash,
            boundary=ContextBoundary.SESSION_ONLY,  # Downgrade boundary
            tags=context.tags + ["shared", f"from_session:{str(source_session_id)[:8]}"],
            derived_from=[context.context_id]
        )
        
        # Store new context
        self.session_contexts[new_context.context_id] = new_context
        target_session.context_items.append(new_context.context_id)
        
        self.logger.info(
            "Context shared across sessions",
            source_session=str(source_session_id)[:8],
            target_session=str(target_session_id)[:8],
            original_context=str(context_id)[:8],
            new_context=str(new_context.context_id)[:8]
        )
        
        return new_context.context_id
    
    def cleanup_expired_sessions(self) -> Dict[str, int]:
        """Clean up expired sessions and their ephemeral context."""
        expired_sessions = []
        cleaned_contexts = 0
        
        for session_id, session in self.sessions.items():
            if session.state == SessionState.ACTIVE and session.is_expired():
                # Clean up ephemeral context
                ephemeral_contexts = self._get_ephemeral_contexts(session_id)
                for context_id in ephemeral_contexts:
                    if context_id in self.session_contexts:
                        del self.session_contexts[context_id]
                        cleaned_contexts += 1
                
                # Mark session as expired
                session.state = SessionState.EXPIRED
                expired_sessions.append(session_id)
        
        # Remove very old ended/expired sessions (older than 7 days)
        old_sessions = []
        week_ago = datetime.now() - timedelta(days=7)
        
        for session_id, session in self.sessions.items():
            if session.state in [SessionState.ENDED, SessionState.EXPIRED, SessionState.ARCHIVED]:
                if session.last_activity < week_ago:
                    old_sessions.append(session_id)
        
        for session_id in old_sessions:
            del self.sessions[session_id]
        
        if expired_sessions or old_sessions:
            self.logger.info(
                "Session cleanup completed",
                expired_sessions=len(expired_sessions),
                cleaned_contexts=cleaned_contexts,
                removed_old_sessions=len(old_sessions)
            )
        
        return {
            "expired_sessions": len(expired_sessions),
            "cleaned_contexts": cleaned_contexts,
            "removed_old_sessions": len(old_sessions)
        }
    
    def _get_ephemeral_contexts(self, session_id: UUID) -> List[UUID]:
        """Get ephemeral contexts for a session."""
        ephemeral_contexts = []
        
        for context_id, context in self.session_contexts.items():
            if (context.session_id == session_id and 
                context.boundary == ContextBoundary.SESSION_ONLY):
                ephemeral_contexts.append(context_id)
        
        return ephemeral_contexts
    
    def get_session_stats(self, session_id: UUID) -> Optional[Dict[str, any]]:
        """Get statistics for a session."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        # Count contexts by boundary
        boundary_counts = {}
        for context_id in session.context_items:
            context = self.session_contexts.get(context_id)
            if context:
                boundary = context.boundary.value
                boundary_counts[boundary] = boundary_counts.get(boundary, 0) + 1
        
        return {
            "session_id": str(session_id),
            "session_type": session.session_type.value,
            "state": session.state.value,
            "age_seconds": (datetime.now() - session.created_at).total_seconds(),
            "inactive_seconds": (datetime.now() - session.last_activity).total_seconds(),
            "context_count": len(session.context_items),
            "promoted_contexts": session.promoted_context_count,
            "boundary_distribution": boundary_counts,
            "is_expired": session.is_expired()
        }
    
    def enforce_boundary_policy(
        self,
        session_id: UUID,
        operation: str,
        data: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Enforce session boundary policies on an operation.
        
        Returns:
            Dict with allowed status and any restrictions
        """
        session = self.get_session(session_id)
        if not session:
            return {
                "allowed": False,
                "reason": "session_not_found",
                "restrictions": ["no_session"]
            }
        
        # Check operation-specific boundaries
        restrictions = []
        
        if "memory_write" in operation and not session.can_promote_context():
            restrictions.append("no_context_promotion")
        
        if "cross_session" in operation and not session.can_share_cross_session():
            restrictions.append("no_cross_session_sharing")
        
        if restrictions:
            return {
                "allowed": False,
                "reason": "boundary_restrictions",
                "restrictions": restrictions,
                "session_type": session.session_type.value
            }
        
        return {
            "allowed": True,
            "reason": "no_restrictions",
            "session_type": session.session_type.value
        }


# Global session manager singleton
_session_manager: Optional[SessionManager] = None

def get_session_manager() -> SessionManager:
    """Get the global session manager (singleton)."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager