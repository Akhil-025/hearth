"""
Cache Manager - Performance optimization with intelligent caching.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Generic, Optional, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

from ...shared.logging.structured_logger import StructuredLogger


T = TypeVar('T')


class CachePolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live


class CacheEntry(BaseModel, Generic[T]):
    """Cache entry with metadata."""
    key: str
    value: T
    created_at: float = Field(default_factory=time.time)
    accessed_at: float = Field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[float] = None
    tags: Dict[str, Any] = Field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_at > self.ttl_seconds
    
    def access(self) -> None:
        """Update access metadata."""
        self.accessed_at = time.time()
        self.access_count += 1


class CacheMetrics(BaseModel):
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    hit_rate: float = 0.0
    avg_access_time_ms: float = 0.0
    
    def update_hit_rate(self):
        """Update hit rate calculation."""
        total = self.hits + self.misses
        self.hit_rate = self.hits / max(total, 1)


class ICacheBackend(ABC, Generic[T]):
    """Cache backend interface."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry[T]]:
        """Get entry from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, entry: CacheEntry[T]) -> None:
        """Set entry in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all entries."""
        pass
    
    @abstractmethod
    async def size(self) -> int:
        """Get cache size in entries."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> int:
        """Cleanup expired entries."""
        pass


class MemoryCacheBackend(ICacheBackend[T]):
    """In-memory cache backend."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.store: Dict[str, CacheEntry[T]] = OrderedDict()
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[CacheEntry[T]]:
        async with self.lock:
            entry = self.store.get(key)
            if entry:
                # Move to end (most recently used)
                self.store.move_to_end(key)
                entry.access()
            return entry
    
    async def set(self, key: str, entry: CacheEntry[T]) -> None:
        async with self.lock:
            self.store[key] = entry
            self.store.move_to_end(key)
            
            # Evict if over size limit
            while len(self.store) > self.max_size:
                self.store.popitem(last=False)
    
    async def delete(self, key: str) -> bool:
        async with self.lock:
            if key in self.store:
                del self.store[key]
                return True
            return False
    
    async def clear(self) -> None:
        async with self.lock:
            self.store.clear()
    
    async def size(self) -> int:
        async with self.lock:
            return len(self.store)
    
    async def cleanup(self) -> int:
        """Remove expired entries."""
        async with self.lock:
            expired_keys = [
                key for key, entry in self.store.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.store[key]
            
            return len(expired_keys)


class CacheManager:
    """
    Intelligent cache manager with multiple backends and policies.
    
    Features:
    - Multi-level caching
    - Automatic eviction
    - Metrics collection
    - Cache warming
    - Tag-based invalidation
    """
    
    def __init__(
        self,
        backend: Optional[ICacheBackend] = None,
        policy: CachePolicy = CachePolicy.LRU,
        max_size: int = 10000,
        default_ttl: Optional[float] = None
    ):
        self.logger = StructuredLogger(__name__)
        self.backend = backend or MemoryCacheBackend(max_size)
        self.policy = policy
        self.default_ttl = default_ttl
        
        # Metrics
        self.metrics = CacheMetrics()
        self.access_times: List[float] = []
        
        # Tag index for invalidation
        self.tag_index: Dict[str, set] = {}
        
        # Background cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None
        self.running = False
        
        self.logger.info(
            "Cache manager initialized",
            policy=policy.value,
            max_size=max_size,
            default_ttl=default_ttl
        )
    
    async def start(self) -> None:
        """Start cache manager with background cleanup."""
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self) -> None:
        """Stop cache manager."""
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while self.running:
            await asyncio.sleep(60)  # Run every minute
            try:
                expired = await self.backend.cleanup()
                if expired > 0:
                    self.logger.debug(
                        "Cache cleanup",
                        expired_entries=expired
                    )
            except Exception as e:
                self.logger.error("Cache cleanup failed", error=str(e))
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes."""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (int, float)):
                return 8  # Approximation
            else:
                # Serialize to JSON and measure
                json_str = json.dumps(value)
                return len(json_str.encode('utf-8'))
        except (TypeError, ValueError):
            return 1024  # Conservative estimate
    
    def _generate_key(self, namespace: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        # Create deterministic string representation
        key_parts = [namespace]
        
        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword arguments (sorted for consistency)
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        # Create hash
        key_str = ":".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]
    
    async def get(
        self,
        namespace: str,
        *args,
        **kwargs
    ) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            namespace: Cache namespace
            *args, **kwargs: Used to generate cache key
        
        Returns:
            Cached value or None
        """
        start_time = time.time()
        key = self._generate_key(namespace, *args, **kwargs)
        
        try:
            entry = await self.backend.get(key)
            
            if entry and not entry.is_expired():
                self.metrics.hits += 1
                self.access_times.append(time.time() - start_time)
                self.metrics.avg_access_time_ms = (
                    sum(self.access_times) / len(self.access_times) * 1000
                )
                
                self.logger.debug(
                    "Cache hit",
                    namespace=namespace,
                    key=key[:8]
                )
                
                return entry.value
            else:
                self.metrics.misses += 1
                
                if entry and entry.is_expired():
                    await self.backend.delete(key)
                
                self.logger.debug(
                    "Cache miss",
                    namespace=namespace,
                    key=key[:8]
                )
                
                return None
                
        except Exception as e:
            self.logger.error(
                "Cache get failed",
                namespace=namespace,
                error=str(e)
            )
            self.metrics.misses += 1
            return None
    
    async def set(
        self,
        value: Any,
        namespace: str,
        ttl_seconds: Optional[float] = None,
        tags: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> str:
        """
        Set value in cache.
        
        Args:
            value: Value to cache
            namespace: Cache namespace
            ttl_seconds: Time to live in seconds
            tags: Tags for invalidation
            *args, **kwargs: Used to generate cache key
        
        Returns:
            Cache key
        """
        key = self._generate_key(namespace, *args, **kwargs)
        
        # Calculate size
        size_bytes = self._calculate_size(value)
        
        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            size_bytes=size_bytes,
            ttl_seconds=ttl_seconds or self.default_ttl,
            tags=tags or {}
        )
        
        try:
            await self.backend.set(key, entry)
            
            # Update tag index
            if tags:
                for tag_key, tag_value in tags.items():
                    tag_id = f"{tag_key}:{tag_value}"
                    if tag_id not in self.tag_index:
                        self.tag_index[tag_id] = set()
                    self.tag_index[tag_id].add(key)
            
            self.metrics.total_size_bytes += size_bytes
            
            self.logger.debug(
                "Cache set",
                namespace=namespace,
                key=key[:8],
                size_bytes=size_bytes,
                ttl_seconds=ttl_seconds
            )
            
            return key
            
        except Exception as e:
            self.logger.error(
                "Cache set failed",
                namespace=namespace,
                error=str(e)
            )
            raise
    
    async def invalidate(self, **tags) -> int:
        """
        Invalidate cache entries by tags.
        
        Args:
            **tags: Tags to match
        
        Returns:
            Number of entries invalidated
        """
        invalidated = 0
        
        for tag_key, tag_value in tags.items():
            tag_id = f"{tag_key}:{tag_value}"
            
            if tag_id in self.tag_index:
                keys = self.tag_index[tag_id].copy()
                
                for key in keys:
                    if await self.backend.delete(key):
                        invalidated += 1
                
                del self.tag_index[tag_id]
        
        if invalidated > 0:
            self.logger.debug(
                "Cache invalidated by tags",
                tags=tags,
                entries=invalidated
            )
        
        return invalidated
    
    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all entries in namespace."""
        # Note: This is expensive for large caches
        # In production, consider using Redis SCAN or similar
        
        # Simple implementation for memory cache
        if isinstance(self.backend, MemoryCacheBackend):
            async with self.backend.lock:
                keys_to_delete = [
                    key for key in self.backend.store.keys()
                    if key.startswith(namespace + ":")  # Approximation
                ]
                
                for key in keys_to_delete:
                    del self.backend.store[key]
                
                invalidated = len(keys_to_delete)
        else:
            # Fallback: can't efficiently do this without scanning
            invalidated = 0
        
        if invalidated > 0:
            self.logger.debug(
                "Namespace invalidated",
                namespace=namespace,
                entries=invalidated
            )
        
        return invalidated
    
    async def cached(
        self,
        namespace: str,
        ttl_seconds: Optional[float] = None,
        tags: Optional[Dict[str, Any]] = None
    ):
        """
        Decorator for caching function results.
        
        Usage:
            @cache_manager.cached("my_function", ttl_seconds=300)
            async def expensive_function(param1, param2):
                return await do_expensive_work(param1, param2)
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Try to get from cache
                cached_result = await self.get(namespace, *args, **kwargs)
                
                if cached_result is not None:
                    return cached_result
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                await self.set(
                    result,
                    namespace,
                    ttl_seconds=ttl_seconds,
                    tags=tags,
                    *args,
                    **kwargs
                )
                
                return result
            
            return wrapper
        
        return decorator
    
    def get_metrics(self) -> CacheMetrics:
        """Get cache metrics."""
        self.metrics.update_hit_rate()
        return self.metrics.copy()
    
    async def warm_cache(
        self,
        generator_func,
        namespace: str,
        count: int = 100,
        concurrency: int = 10
    ):
        """
        Warm cache with generated data.
        
        Args:
            generator_func: Async function that yields (key_args, value)
            namespace: Cache namespace
            count: Maximum number of items to warm
            concurrency: Maximum concurrent generations
        """
        self.logger.info(
            "Warming cache",
            namespace=namespace,
            count=count
        )
        
        semaphore = asyncio.Semaphore(concurrency)
        warmed = 0
        
        async def warm_item(key_args, value):
            async with semaphore:
                await self.set(
                    value,
                    namespace,
                    *key_args
                )
        
        try:
            tasks = []
            async for key_args, value in generator_func():
                if warmed >= count:
                    break
                
                task = asyncio.create_task(warm_item(key_args, value))
                tasks.append(task)
                warmed += 1
            
            await asyncio.gather(*tasks)
            
            self.logger.info(
                "Cache warmed",
                namespace=namespace,
                items=warmed
            )
            
        except Exception as e:
            self.logger.error(
                "Cache warming failed",
                namespace=namespace,
                error=str(e)
            )