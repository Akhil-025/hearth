"""
Event Bus - Pub/sub communication between modules.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from ..shared.logging.structured_logger import StructuredLogger


class EventPriority(Enum):
    """Event processing priority."""
    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class Event:
    """Base event class."""
    event_type: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value
        }


class IEventHandler(ABC):
    """Event handler interface."""
    
    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """Handle an event."""
        pass


EventHandler = Callable[[Event], Awaitable[None]]


class EventSubscription:
    """Event subscription details."""
    
    def __init__(
        self,
        event_type: str,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL
    ):
        self.event_type = event_type
        self.handler = handler
        self.priority = priority
        self.id = str(uuid4())


class EventBus:
    """
    Asynchronous event bus for inter-service communication.
    
    Features:
    - Type-based event routing
    - Priority-based handling
    - Async handler support
    - Subscription management
    """
    
    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.subscriptions: Dict[str, List[EventSubscription]] = {}
        self.middleware: List[Callable[[Event], Awaitable[None]]] = []
        self.running = True
        
        # Statistics
        self.stats = {
            "events_published": 0,
            "events_handled": 0,
            "events_failed": 0,
            "active_subscriptions": 0
        }
    
    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL
    ) -> EventSubscription:
        """Subscribe to events of a specific type."""
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []
        
        subscription = EventSubscription(event_type, handler, priority)
        self.subscriptions[event_type].append(subscription)
        
        # Sort by priority
        self.subscriptions[event_type].sort(key=lambda s: s.priority.value)
        
        self.stats["active_subscriptions"] += 1
        self.logger.debug(
            "Event subscription created",
            event_type=event_type,
            subscription_id=subscription.id,
            priority=priority.value
        )
        
        return subscription
    
    def unsubscribe(self, subscription: EventSubscription) -> bool:
        """Remove an event subscription."""
        event_type = subscription.event_type
        
        if event_type not in self.subscriptions:
            return False
        
        for i, sub in enumerate(self.subscriptions[event_type]):
            if sub.id == subscription.id:
                self.subscriptions[event_type].pop(i)
                self.stats["active_subscriptions"] -= 1
                
                self.logger.debug(
                    "Event subscription removed",
                    event_type=event_type,
                    subscription_id=subscription.id
                )
                
                # Clean up empty lists
                if not self.subscriptions[event_type]:
                    del self.subscriptions[event_type]
                
                return True
        
        return False
    
    def add_middleware(self, middleware: Callable[[Event], Awaitable[None]]) -> None:
        """Add event processing middleware."""
        self.middleware.append(middleware)
    
    async def publish(self, event: Event) -> bool:
        """Publish an event to all subscribers."""
        if not self.running:
            self.logger.warning("Event bus not running, dropping event")
            return False
        
        self.stats["events_published"] += 1
        
        # Apply middleware
        for middleware in self.middleware:
            try:
                await middleware(event)
            except Exception as e:
                self.logger.error(
                    "Middleware failed",
                    error=str(e),
                    event_type=event.event_type
                )
        
        # Find subscribers
        subscribers = self.subscriptions.get(event.event_type, [])
        
        if not subscribers:
            self.logger.debug(
                "No subscribers for event",
                event_type=event.event_type
            )
            return True
        
        self.logger.debug(
            "Publishing event",
            event_type=event.event_type,
            subscriber_count=len(subscribers)
        )
        
        # Execute handlers
        tasks = []
        for subscription in subscribers:
            task = asyncio.create_task(self._execute_handler(subscription, event))
            tasks.append(task)
        
        # Wait for all handlers to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count failures
            for result in results:
                if isinstance(result, Exception):
                    self.stats["events_failed"] += 1
                else:
                    self.stats["events_handled"] += 1
        
        return True
    
    async def _execute_handler(self, subscription: EventSubscription, event: Event) -> None:
        """Execute a single event handler."""
        try:
            # Check if handler is coroutine function
            if inspect.iscoroutinefunction(subscription.handler):
                await subscription.handler(event)
            else:
                # Assume it's a regular function
                subscription.handler(event)
                
        except Exception as e:
            self.logger.error(
                "Event handler failed",
                error=str(e),
                event_type=event.event_type,
                subscription_id=subscription.id
            )
            raise
    
    def get_subscription_count(self, event_type: Optional[str] = None) -> int:
        """Get number of subscriptions."""
        if event_type:
            return len(self.subscriptions.get(event_type, []))
        
        total = 0
        for subscriptions in self.subscriptions.values():
            total += len(subscriptions)
        
        return total
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self.stats,
            "subscription_count": self.get_subscription_count(),
            "event_types": list(self.subscriptions.keys())
        }
    
    async def shutdown(self) -> None:
        """Shutdown the event bus."""
        self.running = False
        self.logger.info("Event bus shutdown")