"""
Test core kernel functionality.

Legacy suite skipped for v0.1 minimal spine.
"""
import pytest

pytest.skip("Legacy kernel tests disabled for v0.1 minimal spine", allow_module_level=True)

import asyncio
from unittest.mock import AsyncMock, Mock

from ...core.kernel import HearthKernel, KernelConfig, IService, ServiceInfo, ServiceStatus


class MockService(IService):
    """Mock service for testing."""
    
    def __init__(self, name: str, dependencies: list = None):
        self.name = name
        self.dependencies = dependencies or []
        self.started = False
        self.stopped = False
        
        self.service_info = ServiceInfo(
            name=name,
            version="1.0.0",
            dependencies=dependencies or []
        )
    
    async def start(self) -> None:
        self.started = True
        self.service_info.status = ServiceStatus.RUNNING
        await asyncio.sleep(0.01)  # Simulate startup time
    
    async def stop(self) -> None:
        self.stopped = True
        self.service_info.status = ServiceStatus.STOPPED
    
    def get_service_info(self) -> ServiceInfo:
        return self.service_info
    
    async def health_check(self) -> bool:
        return self.started and not self.stopped


@pytest.mark.asyncio
async def test_kernel_initialization(test_config: KernelConfig):
    """Test kernel initialization."""
    kernel = HearthKernel(test_config)
    
    assert kernel.config == test_config
    assert not kernel.running
    assert len(kernel.services) == 0


@pytest.mark.asyncio
async def test_service_registration(test_kernel: HearthKernel):
    """Test service registration."""
    service1 = MockService("service1")
    service2 = MockService("service2", ["service1"])
    
    await test_kernel.register_service(service1)
    await test_kernel.register_service(service2)
    
    assert "service1" in test_kernel.services
    assert "service2" in test_kernel.services
    assert "service1" in test_kernel.service_graph["service2"]


@pytest.mark.asyncio
async def test_dependency_resolution(test_kernel: HearthKernel):
    """Test dependency resolution."""
    service1 = MockService("service1")
    service2 = MockService("service2", ["service1"])
    service3 = MockService("service3", ["service2"])
    
    await test_kernel.register_service(service1)
    await test_kernel.register_service(service2)
    await test_kernel.register_service(service3)
    
    # Test resolution for service3
    order = test_kernel.resolve_dependencies("service3")
    assert order == ["service1", "service2", "service3"]
    
    # Test resolution for service1
    order = test_kernel.resolve_dependencies("service1")
    assert order == ["service1"]


@pytest.mark.asyncio
async def test_kernel_start_stop(test_kernel: HearthKernel):
    """Test kernel startup and shutdown."""
    service1 = MockService("service1")
    service2 = MockService("service2")
    
    await test_kernel.register_service(service1)
    await test_kernel.register_service(service2)
    
    # Start kernel
    await test_kernel.start()
    assert test_kernel.running
    assert service1.started
    assert service2.started
    
    # Check status
    status = test_kernel.get_kernel_status()
    assert status["running"] == True
    assert len(status["services"]) == 2
    
    # Stop kernel
    await test_kernel.shutdown()
    assert not test_kernel.running
    assert service1.stopped
    assert service2.stopped


@pytest.mark.asyncio
async def test_circular_dependency_detection(test_kernel: HearthKernel):
    """Test detection of circular dependencies."""
    service1 = MockService("service1", ["service3"])
    service2 = MockService("service2", ["service1"])
    service3 = MockService("service3", ["service2"])  # Circular
    
    await test_kernel.register_service(service1)
    await test_kernel.register_service(service2)
    await test_kernel.register_service(service3)
    
    # This should work because we don't validate circular dependencies until startup
    # The test verifies that we can register services with circular dependencies
    
    # But starting should fail
    with pytest.raises(RuntimeError):
        await test_kernel.start()


@pytest.mark.asyncio
async def test_service_restart(test_kernel: HearthKernel):
    """Test service restart."""
    service1 = MockService("service1")
    
    await test_kernel.register_service(service1)
    await test_kernel.start()
    
    assert service1.started
    service1.started = False  # Simulate service stopped
    
    # Restart service
    success = await test_kernel.restart_service("service1")
    assert success
    assert service1.started


@pytest.mark.asyncio
async def test_missing_dependency(test_kernel: HearthKernel):
    """Test missing dependency handling."""
    service1 = MockService("service1", ["nonexistent"])
    
    await test_kernel.register_service(service1)
    
    # Starting should fail due to missing dependency
    with pytest.raises(ValueError):
        await test_kernel.start()