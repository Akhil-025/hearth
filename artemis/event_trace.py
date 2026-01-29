"""
Artemis Event Trace - Minimal, append-only, hash-linked event log.

Artemis inspection surface
Read-only
No side effects
Safe in LOCKDOWN
"""

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Any, Dict


@dataclass(frozen=True)
class EventRecord:
    """
    Immutable, hash-linked event record.

    Fields are append-only; hash is computed from event content + prev_hash.
    """
    seq: int
    timestamp: str
    event_type: str
    details: Dict[str, Any]
    prev_hash: str | None
    hash: str


class EventTrace:
    """
    Append-only hash-linked event trace.

    Artemis inspection surface
    Read-only
    No side effects
    Safe in LOCKDOWN
    """

    def __init__(self) -> None:
        self._events: list[EventRecord] = []

    def append(self, event_type: str, details: Dict[str, Any]) -> EventRecord:
        """
        Append an event to the trace.

        This is the ONLY write path for the trace.
        """
        seq = len(self._events) + 1
        timestamp = datetime.now().isoformat()
        prev_hash = self._events[-1].hash if self._events else None
        payload = {
            "seq": seq,
            "timestamp": timestamp,
            "event_type": event_type,
            "details": details,
            "prev_hash": prev_hash,
        }
        digest = self._hash_payload(payload)
        record = EventRecord(
            seq=seq,
            timestamp=timestamp,
            event_type=event_type,
            details=details,
            prev_hash=prev_hash,
            hash=digest,
        )
        self._events.append(record)
        return record

    def snapshot(self, limit: int | None = None) -> tuple[EventRecord, ...]:
        """
        Return a read-only snapshot of events.
        """
        if limit is None or limit <= 0:
            return tuple(self._events)
        return tuple(self._events[-limit:])

    def verify_chain(self) -> bool:
        """
        Verify hash linkage for all events.
        """
        prev_hash = None
        for record in self._events:
            payload = {
                "seq": record.seq,
                "timestamp": record.timestamp,
                "event_type": record.event_type,
                "details": record.details,
                "prev_hash": prev_hash,
            }
            expected = self._hash_payload(payload)
            if record.hash != expected:
                return False
            prev_hash = record.hash
        return True

    @staticmethod
    def _hash_payload(payload: Dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
