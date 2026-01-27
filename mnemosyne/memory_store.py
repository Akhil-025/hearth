"""
HEARTH Memory Store - Minimal Append-Only Storage (v0.1)

ENABLED IN v0.1:
- Append-only memory writes
- Human-readable timestamped records
- Simple SQLite storage

DISABLED IN v0.1:
- Memory decay
- Behavioral inference
- Automatic promotion
- Summaries
- Vector search
- Cross-session reasoning
- Encryption
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class MemoryRecord:
    """Minimal memory record."""
    
    def __init__(
        self,
        content: str,
        memory_type: str = "note",
        source: str = "user_confirmation",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid4())
        self.timestamp = datetime.now().isoformat()
        self.type = memory_type
        self.content = content
        self.source = source
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type,
            "content": self.content,
            "source": self.source,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryRecord:
        """Create from dictionary."""
        record = cls(
            content=data["content"],
            memory_type=data.get("type", "note"),
            source=data.get("source", "user_confirmation"),
            metadata=data.get("metadata", {})
        )
        record.id = data["id"]
        record.timestamp = data["timestamp"]
        return record


class MemoryStore:
    """
    Minimal append-only memory store.
    
    Storage: SQLite (local, human-readable via SQL)
    Operations: Write-only (append), Read-all
    Security: None (plaintext, local file)
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or "./data/memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()
    
    def _ensure_schema(self) -> None:
        """Create database schema if not exists."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON memories(timestamp DESC)
            """)
            conn.commit()
        finally:
            conn.close()
    
    def append(self, record: MemoryRecord) -> None:
        """
        Append memory record (write-only).
        
        Args:
            record: Memory record to store
            
        Raises:
            sqlite3.Error: If write fails
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO memories (id, timestamp, type, content, source, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.timestamp,
                    record.type,
                    record.content,
                    record.source,
                    json.dumps(record.metadata)
                )
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_all(self, limit: int = 100) -> List[MemoryRecord]:
        """
        Retrieve all memories (most recent first).
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of memory records
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT id, timestamp, type, content, source, metadata
                FROM memories
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,)
            )
            
            records = []
            for row in cursor.fetchall():
                record = MemoryRecord(
                    content=row[3],
                    memory_type=row[2],
                    source=row[4],
                    metadata=json.loads(row[5])
                )
                record.id = row[0]
                record.timestamp = row[1]
                records.append(record)
            
            return records
        finally:
            conn.close()
    
    def count(self) -> int:
        """Get total number of stored memories."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM memories")
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    def get_recent(self, count: int = 10) -> List[MemoryRecord]:
        """Get most recent N memories."""
        return self.get_all(limit=count)
