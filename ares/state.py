# ARES — Active Defense & Deterrence
# Phase 0: Detection, Deception, Reporting
# No execution authority
# No persistence
# No autonomy
# Reports to Artemis only

"""
Ephemeral state management for ARES.

This module maintains:
- In-memory state only
- Cleared on restart
- No disk writes
- No environment mutation
- Immutable data structures

Design:
- All state frozen (immutable tuples and frozensets)
- No stateful methods (everything is append/replace)
- Fail-closed on any state corruption
"""

from dataclasses import dataclass
from typing import Tuple, FrozenSet, Dict, Any
from enum import Enum


class AresState(Enum):
    """ARES operational state (does NOT affect plan execution)."""
    IDLE = "idle"
    OBSERVING = "observing"
    SUSPICIOUS = "suspicious"
    ESCALATED = "escalated"


@dataclass(frozen=True)
class EphemeralStore:
    """
    Immutable in-memory state container.
    
    Does:
    - Stores signals in memory
    - Stores sensor events in memory
    - Stores deception records in memory
    - Stores behavioral profiles in memory
    - Provides read-only access
    
    Does NOT:
    - Write to disk
    - Write to environment
    - Persist across restarts
    - Modify on access
    """
    
    signals: Tuple = ()  # Immutable tuple of Signal objects
    sensor_events: Tuple = ()  # Immutable tuple of SensorEvent objects
    deception_records: Tuple = ()  # Immutable tuple of DeceptionRecord objects
    profiles: FrozenSet = frozenset()  # Immutable set of profiles
    state: AresState = AresState.IDLE
    
    def add_signal(self, signal: Any) -> "EphemeralStore":
        """
        Add a signal without mutation.
        
        Does:
        - Creates new store with signal appended
        - Returns new immutable instance
        
        Does NOT:
        - Modify self
        - Persist data
        - Execute any action
        """
        return EphemeralStore(
            signals=self.signals + (signal,),
            sensor_events=self.sensor_events,
            deception_records=self.deception_records,
            profiles=self.profiles,
            state=self.state,
        )
    
    def add_sensor_event(self, event: Any) -> "EphemeralStore":
        """
        Add a sensor event without mutation.
        
        Does:
        - Creates new store with event appended
        - Returns new immutable instance
        
        Does NOT:
        - Modify self
        - Persist data
        - Execute any action
        """
        return EphemeralStore(
            signals=self.signals,
            sensor_events=self.sensor_events + (event,),
            deception_records=self.deception_records,
            profiles=self.profiles,
            state=self.state,
        )
    
    def add_deception_record(self, record: Any) -> "EphemeralStore":
        """
        Add a deception record without mutation.
        
        Does:
        - Creates new store with record appended
        - Returns new immutable instance
        
        Does NOT:
        - Modify self
        - Persist data
        - Execute any action
        """
        return EphemeralStore(
            signals=self.signals,
            sensor_events=self.sensor_events,
            deception_records=self.deception_records + (record,),
            profiles=self.profiles,
            state=self.state,
        )
    
    def update_state(self, new_state: AresState) -> "EphemeralStore":
        """
        Update internal state without mutation.
        
        Does:
        - Creates new store with state updated
        - Returns new immutable instance
        
        Does NOT:
        - Modify self
        - Persist data
        - Affect plan execution
        """
        return EphemeralStore(
            signals=self.signals,
            sensor_events=self.sensor_events,
            deception_records=self.deception_records,
            profiles=self.profiles,
            state=new_state,
        )
    
    def get_signal_count(self) -> int:
        """Get count of signals. Does NOT execute or persist."""
        return len(self.signals)
    
    def get_sensor_event_count(self) -> int:
        """Get count of sensor events. Does NOT execute or persist."""
        return len(self.sensor_events)
    
    def get_deception_record_count(self) -> int:
        """Get count of deception records. Does NOT execute or persist."""
        return len(self.deception_records)


# Global ephemeral store (cleared on process restart)
_global_store = EphemeralStore()


def get_store() -> EphemeralStore:
    """
    Get current ephemeral store.
    
    Does:
    - Returns current in-memory state
    
    Does NOT:
    - Load from disk
    - Persist
    - Modify
    - Execute
    """
    return _global_store


def update_store(store: EphemeralStore) -> None:
    """
    Update global store (internal only).
    
    Does:
    - Updates in-memory state
    
    Does NOT:
    - Persist to disk
    - Modify environment
    - Execute actions
    
    Warning: Only for internal ARES use.
    """
    global _global_store
    _global_store = store


def clear_store() -> None:
    """
    Clear all ephemeral state (for testing only).
    
    Does:
    - Resets to empty state
    
    Does NOT:
    - Delete files
    - Modify environment
    - Execute actions
    """
    global _global_store
    _global_store = EphemeralStore()
