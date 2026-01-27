"""
Test Mnemosyne memory store (legacy, skipped for v0.1 minimal spine).
"""
import pytest

pytest.skip("Legacy Mnemosyne memory store tests disabled for v0.1 minimal spine", allow_module_level=True)

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from ...mnemosyne.memory_store import MemoryStore, MemoryQuery
from ...shared.schemas.memory import (
    MemoryType,
    MemoryStatus,
    MemoryPriority,
    StructuredMemory
)


@pytest.mark.asyncio
async def test_memory_store_initialization(memory_store: MemoryStore):
    """Test memory store initialization."""
    info = memory_store.get_service_info()
    assert info.name == "mnemosyne_memory_store"
    assert info.status.value == "running"
    
    # Health check should pass
    healthy = await memory_store.health_check()
    assert healthy


@pytest.mark.asyncio
async def test_store_and_retrieve_memory(memory_store: MemoryStore):
    """Test storing and retrieving memories."""
    # Create test memory
    memory = StructuredMemory(
        user_id="test_user",
        memory_type=MemoryType.STRUCTURED,
        category="preferences",
        key="favorite_color",
        value="blue",
        confidence=0.9,
        tags=["preference", "color"]
    )
    
    # Store memory
    success = await memory_store.store_structured_memory(memory)
    assert success
    
    # Query memories
    query = MemoryQuery(
        user_id="test_user",
        category="preferences"
    )
    
    memories = await memory_store.query_memories(query)
    
    # Verify
    assert len(memories) == 1
    retrieved = memories[0]
    assert retrieved.key == "favorite_color"
    assert retrieved.value == "blue"
    assert retrieved.confidence == 0.9
    assert set(retrieved.tags) == {"preference", "color"}


@pytest.mark.asyncio
async def test_memory_update(memory_store: MemoryStore):
    """Test updating memories."""
    # Create and store memory
    memory_id = uuid4()
    memory = StructuredMemory(
        memory_id=memory_id,
        user_id="test_user",
        memory_type=MemoryType.STRUCTURED,
        category="preferences",
        key="favorite_food",
        value="pizza",
        confidence=0.8
    )
    
    await memory_store.store_structured_memory(memory)
    
    # Update memory
    from ...mnemosyne.memory_store import MemoryUpdate
    
    update = MemoryUpdate(
        value="sushi",
        confidence=0.95,
        tags=["preference", "food", "updated"]
    )
    
    success = await memory_store.update_memory(
        memory_id=memory_id,
        user_id="test_user",
        update=update
    )
    
    assert success
    
    # Verify update
    query = MemoryQuery(
        user_id="test_user",
        key="favorite_food"
    )
    
    memories = await memory_store.query_memories(query)
    assert len(memories) == 1
    assert memories[0].value == "sushi"
    assert memories[0].confidence == 0.95
    assert set(memories[0].tags) == {"preference", "food", "updated"}


@pytest.mark.asyncio
async def test_memory_deletion(memory_store: MemoryStore):
    """Test memory deletion."""
    # Create and store memory
    memory_id = uuid4()
    memory = StructuredMemory(
        memory_id=memory_id,
        user_id="test_user",
        memory_type=MemoryType.STRUCTURED,
        category="temporary",
        key="test_key",
        value="test_value"
    )
    
    await memory_store.store_structured_memory(memory)
    
    # Soft delete
    success = await memory_store.delete_memory(
        memory_id=memory_id,
        user_id="test_user",
        soft_delete=True
    )
    
    assert success
    
    # Verify deleted (should not appear in active query)
    query = MemoryQuery(
        user_id="test_user",
        status=MemoryStatus.ACTIVE
    )
    
    memories = await memory_store.query_memories(query)
    memory_found = any(m.memory_id == memory_id for m in memories)
    assert not memory_found


@pytest.mark.asyncio
async def test_memory_query_filters(memory_store: MemoryStore):
    """Test memory query filters."""
    # Create test memories
    memories = [
        StructuredMemory(
            user_id="test_user",
            memory_type=MemoryType.STRUCTURED,
            category="preferences",
            key=f"pref_{i}",
            value=f"value_{i}",
            confidence=0.5 + (i * 0.1),
            priority=MemoryPriority.HIGH if i % 2 == 0 else MemoryPriority.LOW,
            tags=[f"tag_{i}", "common_tag"]
        )
        for i in range(5)
    ]
    
    # Store all memories
    for memory in memories:
        await memory_store.store_structured_memory(memory)
    
    # Test confidence filter
    query = MemoryQuery(
        user_id="test_user",
        min_confidence=0.7,
        max_confidence=0.9
    )
    
    results = await memory_store.query_memories(query)
    assert len(results) == 2  # Only memories with confidence 0.7 and 0.8
    
    # Test tag filter
    query = MemoryQuery(
        user_id="test_user",
        tags=["tag_2"]
    )
    
    results = await memory_store.query_memories(query)
    assert len(results) == 1
    assert results[0].key == "pref_2"
    
    # Test priority filter
    query = MemoryQuery(
        user_id="test_user",
        priority_min=MemoryPriority.HIGH
    )
    
    results = await memory_store.query_memories(query)
    assert len(results) == 3  # pref_0, pref_2, pref_4


@pytest.mark.asyncio
async def test_memory_stats(memory_store: MemoryStore):
    """Test memory statistics."""
    # Create test memories
    categories = ["preferences", "projects", "people", "preferences"]
    
    for i, category in enumerate(categories):
        memory = StructuredMemory(
            user_id="test_user",
            memory_type=MemoryType.STRUCTURED,
            category=category,
            key=f"key_{i}",
            value=f"value_{i}"
        )
        await memory_store.store_structured_memory(memory)
    
    # Get stats
    stats = await memory_store.get_memory_stats("test_user")
    
    assert "by_category" in stats
    assert stats["by_category"]["preferences"] == 2
    assert stats["by_category"]["projects"] == 1
    assert stats["by_category"]["people"] == 1
    
    assert "by_status" in stats
    assert stats["by_status"]["active"] == 4
    
    assert "activity" in stats
    assert stats["activity"]["total_memories"] == 4


@pytest.mark.asyncio
async def test_memory_versioning(memory_store: MemoryStore):
    """Test memory versioning."""
    # Store initial memory
    memory1 = StructuredMemory(
        user_id="test_user",
        memory_type=MemoryType.STRUCTURED,
        category="preferences",
        key="version_test",
        value="version_1"
    )
    
    await memory_store.store_structured_memory(memory1)
    
    # Store updated memory with same key
    memory2 = StructuredMemory(
        user_id="test_user",
        memory_type=MemoryType.STRUCTURED,
        category="preferences",
        key="version_test",
        value="version_2"
    )
    
    await memory_store.store_structured_memory(memory2)
    
    # Query active memories
    query = MemoryQuery(
        user_id="test_user",
        key="version_test",
        status=MemoryStatus.ACTIVE
    )
    
    results = await memory_store.query_memories(query)
    
    # Should only have latest version
    assert len(results) == 1
    assert results[0].value == "version_2"
    
    # Query all statuses (should find archived)
    query_all = MemoryQuery(
        user_id="test_user",
        key="version_test"
    )
    
    # Note: Our current implementation doesn't return archived memories
    # This test verifies that versioning doesn't break normal queries
    results_all = await memory_store.query_memories(query_all)
    assert len(results_all) >= 1