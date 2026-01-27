"""
HEARTH Event Bus - Minimal Stub (v0.1)

DISABLED IN v0.1  not part of execution spine
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4


@dataclass
class Event:
    """Minimal event class for type compatibility."""
    event_type: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)


class EventBus:
    """Minimal noop event bus."""
    
    def __init__(self):
        pass
