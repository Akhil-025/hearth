"""
Memory Store - SQL-based structured memory storage.
"""
from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import pandas as pd
from pydantic import BaseModel, ValidationError

from ..core.kernel import IService, ServiceInfo, ServiceStatus
from ..shared.crypto.encryption import encrypt_data, decrypt_data
from ..shared.logging.structured_logger import StructuredLogger
from ..shared.schemas.memory import (
    IdentityMemory,
    MemoryPriority,
    MemoryStatus,
    MemoryType,
    StructuredMemory
)


class MemoryQuery(BaseModel):
    """Memory query parameters."""
    user_id: str
    memory_type: Optional[MemoryType] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    key: Optional[str] = None
    parent_id: Optional[UUID] = None
    status: Optional[MemoryStatus] = MemoryStatus.ACTIVE
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    priority_min: Optional[MemoryPriority] = None
    priority_max: Optional[MemoryPriority] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = 100
    offset: int = 0
    order_by: str = "created_at"
    order_desc: bool = True


class MemoryUpdate(BaseModel):
    """Memory update parameters."""
    value: Optional[Any] = None
    tags: Optional[List[str]] = None
    priority: Optional[MemoryPriority] = None
    confidence: Optional[float] = None
    status: Optional[MemoryStatus] = None
    expires_at: Optional[datetime] = None
    related_ids: Optional[List[UUID]] = None


class MemoryStore(IService):
    """
    SQL-based memory storage with encryption.
    
    Features:
    - Encrypted storage at rest
    - Type-safe operations
    - Versioning
    - Soft deletion
    - Query optimization
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        encryption_key: Optional[str] = None
    ):
        self.db_path = Path(db_path or "./data/memory.db")
        self.encryption_key = encryption_key
        self.logger = StructuredLogger(__name__)
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Service info
        self.service_info = ServiceInfo(
            name="mnemosyne_memory_store",
            version="0.1.0",
            dependencies=[]
        )
        
        # Database connection pool
        self.connections = {}
        self.lock = asyncio.Lock()
        
        self.logger.info(
            "Memory store initialized",
            db_path=str(self.db_path),
            encrypted=bool(encryption_key)
        )
    
    async def start(self) -> None:
        """Start memory store service."""
        self.service_info.status = ServiceStatus.STARTING
        
        # Initialize database
        await self._initialize_database()
        
        self.service_info.status = ServiceStatus.RUNNING
        self.logger.info("Memory store started")
    
    async def stop(self) -> None:
        """Stop memory store service."""
        self.service_info.status = ServiceStatus.STOPPING
        
        # Close all connections
        async with self.lock:
            for conn in self.connections.values():
                conn.close()
            self.connections.clear()
        
        self.service_info.status = ServiceStatus.STOPPED
        self.logger.info("Memory store stopped")
    
    def get_service_info(self) -> ServiceInfo:
        """Get service metadata."""
        return self.service_info
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            async with self._get_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return False
    
    @contextlib.asynccontextmanager
    async def _get_connection(self):
        """Get database connection with connection pooling."""
        thread_id = threading.get_ident()
        
        async with self.lock:
            if thread_id not in self.connections:
                self.connections[thread_id] = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False
                )
                # Enable foreign keys and WAL mode
                self.connections[thread_id].execute("PRAGMA foreign_keys = ON")
                self.connections[thread_id].execute("PRAGMA journal_mode = WAL")
            
            conn = self.connections[thread_id]
        
        yield conn
    
    async def _initialize_database(self) -> None:
        """Initialize database schema."""
        async with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Identity memory table (immutable, versioned)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS identity_memory (
                    memory_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    memory_type TEXT NOT NULL,
                    profile_encrypted TEXT NOT NULL,
                    constraints_encrypted TEXT,
                    system_rules_encrypted TEXT,
                    source TEXT NOT NULL,
                    confidence REAL CHECK (confidence >= 0 AND confidence <= 1),
                    immutable BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(user_id, version)
                )
            """)
            
            # Structured memory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS structured_memory (
                    memory_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    tags_encrypted TEXT,
                    key TEXT NOT NULL,
                    value_encrypted TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    parent_id TEXT,
                    related_ids_encrypted TEXT,
                    priority INTEGER DEFAULT 50,
                    confidence REAL CHECK (confidence >= 0 AND confidence <= 1),
                    expires_at TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY(parent_id) REFERENCES structured_memory(memory_id),
                    UNIQUE(user_id, category, key)
                )
            """)
            
            # Indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_structured_user_category 
                ON structured_memory(user_id, category)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_structured_tags 
                ON structured_memory(tags_encrypted)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_structured_status 
                ON structured_memory(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_structured_created 
                ON structured_memory(created_at)
            """)
            
            # Memory audit table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    old_value_encrypted TEXT,
                    new_value_encrypted TEXT,
                    performed_by TEXT NOT NULL,
                    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT,
                    
                    FOREIGN KEY(memory_id) REFERENCES structured_memory(memory_id)
                )
            """)
            
            conn.commit()
            
            self.logger.debug("Database schema initialized")
    
    def _encrypt_field(self, data: Any) -> str:
        """Encrypt field data."""
        if self.encryption_key:
            return encrypt_data(json.dumps(data), self.encryption_key)
        return json.dumps(data)
    
    def _decrypt_field(self, encrypted: str) -> Any:
        """Decrypt field data."""
        if self.encryption_key:
            return json.loads(decrypt_data(encrypted, self.encryption_key))
        return json.loads(encrypted)
    
    async def store_identity_memory(self, memory: IdentityMemory) -> bool:
        """Store identity memory (immutable, versioned)."""
        async with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO identity_memory (
                        memory_id, user_id, version, memory_type,
                        profile_encrypted, constraints_encrypted,
                        system_rules_encrypted, source, confidence, immutable
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(memory.memory_id),
                    memory.user_id,
                    memory.version,
                    memory.memory_type.value,
                    self._encrypt_field(memory.profile),
                    self._encrypt_field(memory.constraints),
                    self._encrypt_field(memory.system_rules),
                    memory.source,
                    memory.confidence,
                    memory.immutable
                ))
                
                conn.commit()
                self.logger.debug(
                    "Identity memory stored",
                    memory_id=str(memory.memory_id),
                    version=memory.version
                )
                return True
                
            except sqlite3.IntegrityError as e:
                self.logger.error(
                    "Failed to store identity memory",
                    error=str(e),
                    memory_id=str(memory.memory_id)
                )
                return False
    
    async def store_structured_memory(self, memory: StructuredMemory) -> bool:
        """Store structured memory."""
        async with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if memory with same key exists
            cursor.execute("""
                SELECT memory_id, status FROM structured_memory
                WHERE user_id = ? AND category = ? AND key = ?
            """, (memory.user_id, memory.category, memory.key))
            
            existing = cursor.fetchone()
            
            try:
                if existing:
                    # Update existing memory (soft delete and create new)
                    existing_id, existing_status = existing
                    
                    if existing_status == "active":
                        # Archive old version
                        cursor.execute("""
                            UPDATE structured_memory
                            SET status = 'archived', updated_at = CURRENT_TIMESTAMP
                            WHERE memory_id = ?
                        """, (existing_id,))
                        
                        # Audit trail
                        cursor.execute("""
                            INSERT INTO memory_audit (
                                memory_id, operation, old_value_encrypted,
                                new_value_encrypted, performed_by, reason
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            existing_id,
                            "archive",
                            self._encrypt_field({"status": "active"}),
                            self._encrypt_field({"status": "archived"}),
                            "system",
                            "Version update"
                        ))
                
                # Insert new memory
                cursor.execute("""
                    INSERT INTO structured_memory (
                        memory_id, user_id, memory_type, category, subcategory,
                        tags_encrypted, key, value_encrypted, schema_version,
                        parent_id, related_ids_encrypted, priority, confidence,
                        expires_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(memory.memory_id),
                    memory.user_id,
                    memory.memory_type.value,
                    memory.category,
                    memory.subcategory,
                    self._encrypt_field(memory.tags),
                    memory.key,
                    self._encrypt_field(memory.value),
                    memory.schema_version,
                    str(memory.parent_id) if memory.parent_id else None,
                    self._encrypt_field([str(id) for id in memory.related_ids]),
                    memory.priority.value,
                    memory.confidence,
                    memory.expires_at.isoformat() if memory.expires_at else None,
                    memory.status.value
                ))
                
                conn.commit()
                
                self.logger.debug(
                    "Structured memory stored",
                    memory_id=str(memory.memory_id),
                    category=memory.category,
                    key=memory.key
                )
                return True
                
            except Exception as e:
                conn.rollback()
                self.logger.error(
                    "Failed to store structured memory",
                    error=str(e),
                    memory_id=str(memory.memory_id)
                )
                return False
    
    async def query_memories(self, query: MemoryQuery) -> List[StructuredMemory]:
        """Query structured memories with filtering."""
        async with self._get_connection() as conn:
            # Build query
            sql = """
                SELECT 
                    memory_id, user_id, memory_type, category, subcategory,
                    tags_encrypted, key, value_encrypted, schema_version,
                    parent_id, related_ids_encrypted, priority, confidence,
                    expires_at, status, created_at, updated_at
                FROM structured_memory
                WHERE user_id = ? AND status = ?
            """
            
            params = [query.user_id, query.status.value]
            
            # Add filters
            filters = []
            
            if query.memory_type:
                filters.append("memory_type = ?")
                params.append(query.memory_type.value)
            
            if query.category:
                filters.append("category = ?")
                params.append(query.category)
            
            if query.key:
                filters.append("key = ?")
                params.append(query.key)
            
            if query.parent_id:
                filters.append("parent_id = ?")
                params.append(str(query.parent_id))
            
            if query.tags:
                # Search for memories containing all tags
                for tag in query.tags:
                    filters.append("tags_encrypted LIKE ?")
                    params.append(f'%{tag}%')
            
            if query.min_confidence > 0:
                filters.append("confidence >= ?")
                params.append(query.min_confidence)
            
            if query.max_confidence < 1.0:
                filters.append("confidence <= ?")
                params.append(query.max_confidence)
            
            if query.priority_min:
                filters.append("priority >= ?")
                params.append(query.priority_min.value)
            
            if query.priority_max:
                filters.append("priority <= ?")
                params.append(query.priority_max.value)
            
            if query.created_after:
                filters.append("created_at >= ?")
                params.append(query.created_after.isoformat())
            
            if query.created_before:
                filters.append("created_at <= ?")
                params.append(query.created_before.isoformat())
            
            if filters:
                sql += " AND " + " AND ".join(filters)
            
            # Add ordering
            sql += f" ORDER BY {query.order_by} {'DESC' if query.order_desc else 'ASC'}"
            
            # Add limit/offset
            sql += " LIMIT ? OFFSET ?"
            params.extend([query.limit, query.offset])
            
            # Execute query
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Parse results
            memories = []
            for row in rows:
                try:
                    memory = StructuredMemory(
                        memory_id=UUID(row[0]),
                        user_id=row[1],
                        memory_type=MemoryType(row[2]),
                        category=row[3],
                        subcategory=row[4],
                        tags=self._decrypt_field(row[5]) if row[5] else [],
                        key=row[6],
                        value=self._decrypt_field(row[7]),
                        schema_version=row[8],
                        parent_id=UUID(row[9]) if row[9] else None,
                        related_ids=[
                            UUID(id_str) for id_str in self._decrypt_field(row[10])
                        ] if row[10] else [],
                        priority=MemoryPriority(row[11]),
                        confidence=row[12],
                        expires_at=datetime.fromisoformat(row[13]) if row[13] else None,
                        status=MemoryStatus(row[14]),
                        created_at=datetime.fromisoformat(row[15]),
                        updated_at=datetime.fromisoformat(row[16])
                    )
                    memories.append(memory)
                except (ValidationError, ValueError) as e:
                    self.logger.warning(
                        "Failed to parse memory row",
                        memory_id=row[0],
                        error=str(e)
                    )
            
            self.logger.debug(
                "Memory query executed",
                query_params=query.dict(),
                results=len(memories)
            )
            
            return memories
    
    async def update_memory(
        self,
        memory_id: UUID,
        user_id: str,
        update: MemoryUpdate
    ) -> bool:
        """Update structured memory with audit trail."""
        async with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Get current value for audit
                cursor.execute("""
                    SELECT value_encrypted, tags_encrypted, priority,
                           confidence, status, expires_at, related_ids_encrypted
                    FROM structured_memory
                    WHERE memory_id = ? AND user_id = ?
                """, (str(memory_id), user_id))
                
                current = cursor.fetchone()
                if not current:
                    return False
                
                old_value = {
                    "value": self._decrypt_field(current[0]) if current[0] else None,
                    "tags": self._decrypt_field(current[1]) if current[1] else [],
                    "priority": MemoryPriority(current[2]) if current[2] else None,
                    "confidence": current[3],
                    "status": MemoryStatus(current[4]) if current[4] else None,
                    "expires_at": current[5],
                    "related_ids": self._decrypt_field(current[6]) if current[6] else []
                }
                
                # Build update query
                updates = []
                params = []
                
                if update.value is not None:
                    updates.append("value_encrypted = ?")
                    params.append(self._encrypt_field(update.value))
                
                if update.tags is not None:
                    updates.append("tags_encrypted = ?")
                    params.append(self._encrypt_field(update.tags))
                
                if update.priority is not None:
                    updates.append("priority = ?")
                    params.append(update.priority.value)
                
                if update.confidence is not None:
                    updates.append("confidence = ?")
                    params.append(update.confidence)
                
                if update.status is not None:
                    updates.append("status = ?")
                    params.append(update.status.value)
                
                if update.expires_at is not None:
                    updates.append("expires_at = ?")
                    params.append(update.expires_at.isoformat())
                
                if update.related_ids is not None:
                    updates.append("related_ids_encrypted = ?")
                    params.append(self._encrypt_field([
                        str(id) for id in update.related_ids
                    ]))
                
                if not updates:
                    return False  # Nothing to update
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                
                # Execute update
                update_sql = f"""
                    UPDATE structured_memory
                    SET {', '.join(updates)}
                    WHERE memory_id = ? AND user_id = ?
                """
                params.extend([str(memory_id), user_id])
                
                cursor.execute(update_sql, params)
                
                if cursor.rowcount == 0:
                    return False
                
                # Create audit entry
                new_value = old_value.copy()
                if update.value is not None:
                    new_value["value"] = update.value
                if update.tags is not None:
                    new_value["tags"] = update.tags
                if update.priority is not None:
                    new_value["priority"] = update.priority
                if update.confidence is not None:
                    new_value["confidence"] = update.confidence
                if update.status is not None:
                    new_value["status"] = update.status
                if update.expires_at is not None:
                    new_value["expires_at"] = update.expires_at
                if update.related_ids is not None:
                    new_value["related_ids"] = update.related_ids
                
                cursor.execute("""
                    INSERT INTO memory_audit (
                        memory_id, operation, old_value_encrypted,
                        new_value_encrypted, performed_by
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    str(memory_id),
                    "update",
                    self._encrypt_field(old_value),
                    self._encrypt_field(new_value),
                    "system"
                ))
                
                conn.commit()
                
                self.logger.debug(
                    "Memory updated",
                    memory_id=str(memory_id),
                    updates=len(updates) - 1  # Exclude updated_at
                )
                return True
                
            except Exception as e:
                conn.rollback()
                self.logger.error(
                    "Failed to update memory",
                    error=str(e),
                    memory_id=str(memory_id)
                )
                return False
    
    async def delete_memory(
        self,
        memory_id: UUID,
        user_id: str,
        soft_delete: bool = True
    ) -> bool:
        """Delete memory (soft or hard)."""
        async with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                if soft_delete:
                    # Soft delete (update status)
                    cursor.execute("""
                        UPDATE structured_memory
                        SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
                        WHERE memory_id = ? AND user_id = ?
                    """, (str(memory_id), user_id))
                    
                    # Audit trail
                    cursor.execute("""
                        INSERT INTO memory_audit (
                            memory_id, operation, performed_by
                        ) VALUES (?, ?, ?)
                    """, (str(memory_id), "soft_delete", "system"))
                    
                else:
                    # Hard delete
                    cursor.execute("""
                        DELETE FROM structured_memory
                        WHERE memory_id = ? AND user_id = ?
                    """, (str(memory_id), user_id))
                    
                    # Audit trail
                    cursor.execute("""
                        INSERT INTO memory_audit (
                            memory_id, operation, performed_by
                        ) VALUES (?, ?, ?)
                    """, (str(memory_id), "hard_delete", "system"))
                
                conn.commit()
                
                delete_type = "soft" if soft_delete else "hard"
                self.logger.debug(
                    "Memory deleted",
                    memory_id=str(memory_id),
                    type=delete_type
                )
                
                return cursor.rowcount > 0
                
            except Exception as e:
                conn.rollback()
                self.logger.error(
                    "Failed to delete memory",
                    error=str(e),
                    memory_id=str(memory_id)
                )
                return False
    
    async def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for user."""
        async with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count by category
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM structured_memory
                WHERE user_id = ? AND status = 'active'
                GROUP BY category
                ORDER BY count DESC
            """, (user_id,))
            
            stats["by_category"] = {
                row[0]: row[1] for row in cursor.fetchall()
            }
            
            # Count by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM structured_memory
                WHERE user_id = ?
                GROUP BY status
            """, (user_id,))
            
            stats["by_status"] = {
                row[0]: row[1] for row in cursor.fetchall()
            }
            
            # Recent activity
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_memories,
                    SUM(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END) as recent_additions,
                    SUM(CASE WHEN updated_at >= datetime('now', '-7 days') AND created_at < datetime('now', '-7 days') THEN 1 ELSE 0 END) as recent_updates
                FROM structured_memory
                WHERE user_id = ?
            """, (user_id,))
            
            activity_row = cursor.fetchone()
            if activity_row:
                stats["activity"] = {
                    "total_memories": activity_row[0] or 0,
                    "recent_additions": activity_row[1] or 0,
                    "recent_updates": activity_row[2] or 0
                }
            
            return stats