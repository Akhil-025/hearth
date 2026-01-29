# ARES — Active Defense & Deterrence
# Phase 0: Detection, Deception, Reporting
# No execution authority
# No persistence
# No autonomy
# Reports to Artemis only

"""
Event correlation and timeline reconstruction.

Timeline:
- In-memory only
- Append-only
- Ordered
- Correlate signals, events, deceptions

Does:
- Record events
- Correlate events
- Build timeline
- Emit composite signals

Does NOT:
- Persist
- Execute
- Modify events
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import hashlib

from .signals import Signal, SignalType, ConfidenceLevel, SignalPattern
from .sensors import SensorEvent


@dataclass(frozen=True)
class TimelineEvent:
    """
    Immutable timeline event (represents any recorded event).
    
    Does:
    - Records event occurrence
    - Captures timestamp and source
    
    Does NOT:
    - Persist
    - Execute
    """
    
    event_id: str
    event_type: str  # "signal", "sensor_event", "deception"
    timestamp: datetime
    source: str
    event_data: dict  # Frozen representation
    
    @staticmethod
    def create(
        event_type: str,
        source: str,
        event_data: dict,
    ) -> "TimelineEvent":
        """
        Create timeline event.
        
        Does:
        - Records event with timestamp
        
        Does NOT:
        - Persist
        - Execute
        """
        timestamp = datetime.utcnow()
        id_str = f"{event_type}_{source}_{timestamp.isoformat()}"
        event_id = f"tev-{hashlib.sha256(id_str.encode()).hexdigest()[:12]}"
        
        return TimelineEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            source=source,
            event_data=dict(event_data),
        )


class Timeline:
    """
    Append-only timeline of events.
    
    Does:
    - Records events in order
    - Correlates related events
    - Builds composite signals
    
    Does NOT:
    - Persist
    - Execute
    - Modify recorded events
    """
    
    def __init__(self):
        """Initialize timeline (does NOT execute on import)."""
        self.events: List[TimelineEvent] = []
        self.correlations: List[Tuple[str, str, str]] = []  # (event_id, event_id, reason)
    
    def add_event(
        self,
        event_type: str,
        source: str,
        event_data: dict,
    ) -> TimelineEvent:
        """
        Add event to timeline (append-only).
        
        Does:
        - Appends event
        - Returns immutable record
        
        Does NOT:
        - Persist
        - Modify existing events
        - Execute
        """
        event = TimelineEvent.create(event_type, source, event_data)
        self.events.append(event)
        return event
    
    def add_signal_event(self, signal: Signal) -> TimelineEvent:
        """
        Add signal as timeline event.
        
        Does:
        - Records signal in timeline
        
        Does NOT:
        - Persist
        - Execute
        """
        return self.add_event(
            event_type="signal",
            source=signal.source_subsystem,
            event_data=signal.to_dict(),
        )
    
    def add_sensor_event(self, sensor_event: SensorEvent) -> TimelineEvent:
        """
        Add sensor event to timeline.
        
        Does:
        - Records sensor event in timeline
        
        Does NOT:
        - Persist
        - Execute
        """
        return self.add_event(
            event_type="sensor",
            source=sensor_event.source,
            event_data={
                "event_type": sensor_event.event_type.value,
                "description": sensor_event.description,
                "context": sensor_event.context,
            },
        )
    
    def correlate_events(
        self,
        event_id_1: str,
        event_id_2: str,
        reason: str,
    ) -> None:
        """
        Record correlation between events.
        
        Does:
        - Records correlation
        
        Does NOT:
        - Persist
        - Execute
        """
        self.correlations.append((event_id_1, event_id_2, reason))
    
    def find_events_near(
        self,
        target_time: datetime,
        window_seconds: int,
    ) -> List[TimelineEvent]:
        """
        Find events within time window.
        
        Does:
        - Returns matching events
        
        Does NOT:
        - Persist
        - Execute
        """
        cutoff_min = target_time - timedelta(seconds=window_seconds)
        cutoff_max = target_time + timedelta(seconds=window_seconds)
        
        return [
            evt for evt in self.events
            if cutoff_min <= evt.timestamp <= cutoff_max
        ]
    
    def find_pattern(
        self,
        event_type: str,
        source: str,
        count: int,
        window_seconds: int,
    ) -> Optional[List[TimelineEvent]]:
        """
        Find pattern of events.
        
        Does:
        - Finds events matching pattern
        - Returns matching sequence
        
        Does NOT:
        - Persist
        - Execute
        """
        matching = [
            evt for evt in self.events
            if evt.event_type == event_type and evt.source == source
        ]
        
        if len(matching) < count:
            return None
        
        # Check if count events are within window
        recent = matching[-count:]
        if recent:
            time_span = (recent[-1].timestamp - recent[0].timestamp).total_seconds()
            if time_span <= window_seconds:
                return recent
        
        return None
    
    def get_timeline_summary(self, last_n: int = 10) -> List[dict]:
        """
        Get recent timeline events.
        
        Does:
        - Returns last N events
        
        Does NOT:
        - Persist
        - Execute
        """
        events_to_return = self.events[-last_n:] if last_n > 0 else self.events
        
        return [
            {
                "event_id": evt.event_id,
                "event_type": evt.event_type,
                "timestamp": evt.timestamp.isoformat(),
                "source": evt.source,
            }
            for evt in events_to_return
        ]


# Global timeline (does NOT execute on import)
_timeline = None


def get_timeline() -> Timeline:
    """
    Get global timeline.
    
    Does:
    - Returns timeline (creates if needed)
    
    Does NOT:
    - Execute
    - Persist
    """
    global _timeline
    if _timeline is None:
        _timeline = Timeline()
    return _timeline


def clear_timeline() -> None:
    """
    Clear timeline (for testing only).
    
    Does:
    - Resets timeline
    
    Does NOT:
    - Persist
    - Execute
    """
    global _timeline
    _timeline = Timeline()
