"""
STAGE-4 AUDIT EVENTS

Minimal, immutable audit event logging (separate from Stage-3 audit).

Stage-4 maintains its own audit log:
- Does NOT modify Stage-3 audit
- Does NOT depend on Stage-3 audit
- Tracks Stage-4-level events only
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class Stage4AuditEvent:
    """
    Stage-4 audit event (immutable).
    
    Tracks Stage-4-level execution events:
    - plan_received: User submitted a plan
    - execution_started: Stage-4 beginning execution
    - execution_completed: Stage-4 execution succeeded
    - execution_failed: Stage-4 execution failed
    
    Separate from Stage-3 audit log (Stage-3 owns its own audit).
    """
    
    timestamp: datetime
    user_id: str
    event_type: str  # "plan_received", "execution_started", "execution_completed", "execution_failed"
    plan_id: str
    details: Dict[str, Any]
