"""
Mnemosyne Service - Single Public Entry Point for Hearth.

Pure, deterministic, explicit memory interface.
No background tasks, no autonomous indexing, no watchers.
All operations are synchronous and user-triggered.

Wrapper around external Mnemosyne project components.
Disables: tasks, workers, schedulers, watchdog, web, auto-indexing.
Enables: write(), read(), stats(), health_check() only.
"""
from typing import Dict, Any, List, Optional

from .service_config import MnemosyneConfig
from .memory_store import MemoryStore, MemoryRecord


# Safety guards (hardening v0.1.1)
MAX_SINGLE_MEMORY_SIZE = 50_000  # 50KB per entry (hard limit)
MIN_MEMORY_LENGTH = 1  # Must have at least 1 non-whitespace char


class MnemosyneService:
    """
    Single public interface for memory in Hearth.
    
    - Explicit: write() and read() only on user intent
    - Non-autonomous: no background processing
    - Safe: graceful degradation if disabled
    - Pure: same read() on same db = same result
    """
    
    def __init__(self, config: Optional[MnemosyneConfig] = None):
        """
        Initialize Mnemosyne service.
        
        Args:
            config: MnemosyneConfig (uses defaults if None)
        """
        self.config = config or MnemosyneConfig()
        self.memory_store: Optional[MemoryStore] = None
        self._health_status = "unchecked"
        
        # Initialize memory store if enabled
        if self.config.enabled:
            try:
                self.memory_store = MemoryStore(db_path=str(self.config.db_path))
                self._health_status = "healthy"
            except Exception as e:
                self._health_status = f"initialization_failed: {e}"
                self.memory_store = None
    
    def write(
        self,
        content: str,
        memory_type: str = "note",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Write memory explicitly (user-confirmed only).
        
        Args:
            content: Memory content
            memory_type: Type of memory (default: "note")
            metadata: Optional metadata dict
        
        Returns:
            True if written, False if disabled, invalid, or error
        
        Rejects:
            - Empty or whitespace-only content
            - Content exceeding MAX_SINGLE_MEMORY_SIZE
        """
        if not self.config.enabled or not self.memory_store:
            return False
        
        # Guard 1: Reject empty/whitespace-only content (LIMIT-2.1 fixed)
        if not content or not content.strip():
            return False
        
        # Guard 2: Reject oversized entries (LIMIT-2.2 fixed)
        if len(content.encode('utf-8')) > MAX_SINGLE_MEMORY_SIZE:
            return False
        
        try:
            record = MemoryRecord(
                content=content,
                memory_type=memory_type,
                source="user_confirmation",
                metadata=metadata or {}
            )
            self.memory_store.append(record)
            return True
        except Exception as e:
            self._health_status = f"write_failed: {e}"
            return False
    
    def read(self, limit: int = 5) -> List[str]:
        """
        Read recent memories (explicit user request only).
        
        Args:
            limit: Number of memories to return
        
        Returns:
            List of memory content strings (most recent first)
        """
        if not self.config.enabled or not self.memory_store:
            return []
        
        try:
            records = self.memory_store.get_recent(count=limit)
            return [record.content for record in records]
        except Exception as e:
            self._health_status = f"read_failed: {e}"
            return []
    
    def search(self, query: str, limit: int = 5) -> List[str]:
        """
        Search memories by keyword (explicit user request only).
        
        NOT IMPLEMENTED - Mnemosyne's search requires vector DB.
        This method is a placeholder for future enhancement.
        
        Args:
            query: Search query
            limit: Number of results
        
        Returns:
            Empty list (not yet implemented)
        """
        # Vector search is disabled in v0.1
        # Future: could implement simple keyword search
        return []
    
    def stats(self) -> Dict[str, Any]:
        """
        Get service statistics.
        
        Returns:
            Dict with memory count, status, enabled flag
        """
        result = {
            "enabled": self.config.enabled,
            "status": self._health_status,
            "memory_count": 0,
        }
        
        if self.config.enabled and self.memory_store:
            try:
                result["memory_count"] = self.memory_store.count()
            except Exception as e:
                result["error"] = str(e)
        
        return result
    
    def health_check(self) -> bool:
        """
        Check service health.
        
        Returns:
            True if healthy and enabled, False otherwise
        """
        if not self.config.enabled:
            return False
        
        if self.memory_store is None:
            return False
        
        return self._health_status == "healthy"
    
    # Legacy methods for backward compatibility with v0.1
    
    def save(self, content: str, memory_type: str = "note") -> bool:
        """
        Legacy v0.1 save method.
        Redirects to write().
        """
        return self.write(content, memory_type=memory_type)
    
    def query_recent(self, limit: int = 10) -> List[str]:
        """
        Legacy v0.1 query_recent method.
        Redirects to read().
        """
        return self.read(limit=limit)
