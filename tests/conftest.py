"""
Test configuration and fixtures.
"""
import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..core.kernel import HearthKernel, KernelConfig
from ..hestia.agent import HestiaAgent
from ..mnemosyne.memory_store import MemoryStore
from ..shared.logging.structured_logger import StructuredLogger


# Configure logging for tests
logger = StructuredLogger(__name__, level="WARNING")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_dir: Path) -> KernelConfig:
    """Create test configuration."""
    return KernelConfig(
        data_dir=str(temp_dir / "data"),
        log_level="DEBUG",
        enable_audit=False,
        require_permissions=False,
        service_startup_timeout=5,
        service_shutdown_timeout=2
    )


@pytest_asyncio.fixture
async def test_kernel(test_config: KernelConfig) -> AsyncGenerator[HearthKernel, None]:
    """Create test kernel."""
    kernel = HearthKernel(test_config)
    yield kernel
    await kernel.shutdown()


@pytest_asyncio.fixture
async def memory_store(temp_dir: Path) -> AsyncGenerator[MemoryStore, None]:
    """Create test memory store."""
    db_path = temp_dir / "test_memory.db"
    store = MemoryStore(str(db_path))
    
    await store.start()
    yield store
    await store.stop()


@pytest_asyncio.fixture
async def hestia_agent() -> AsyncGenerator[HestiaAgent, None]:
    """Create test Hestia agent."""
    agent = HestiaAgent()
    await agent.start()
    yield agent
    await agent.stop()


@pytest.fixture
def sample_user_input() -> dict:
    """Create sample user input."""
    return {
        "text": "Hello, how are you?",
        "session_id": "test_session",
        "user_id": "test_user"
    }


@pytest.fixture
def sample_structured_memory() -> dict:
    """Create sample structured memory."""
    return {
        "user_id": "test_user",
        "memory_type": "structured",
        "category": "preferences",
        "key": "favorite_color",
        "value": "blue",
        "confidence": 0.9,
        "tags": ["preference", "color"]
    }