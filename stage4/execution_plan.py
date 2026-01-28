"""
STAGE-4 EXECUTION PLAN

Explicit, user-declared execution plan (immutable after creation).

Stage-4 accepts ONLY these plans (no inference, no defaults).
Plans are validated BEFORE execution.
Plans are IMMUTABLE after construction.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class Stage4ExecutionPlan:
    """
    Immutable execution plan container.
    
    Represents an explicit, user-declared execution plan:
    - user_id: Identifier of the user submitting the plan
    - token_hash: Stage-3 capability token (authorization)
    - trigger_type: How the plan was triggered
    - steps: List of execution steps (non-empty)
    - data_bindings: Optional data flow between steps
    
    All fields are required at construction time (no defaults).
    Immutability is enforced after initialization.
    """
    
    user_id: str
    token_hash: str
    trigger_type: str
    steps: List[Dict[str, Any]]
    data_bindings: Optional[List[Dict[str, Any]]] = None
    
    # Immutability flag (set to True after __post_init__)
    _immutable: bool = field(default=False, init=False, repr=False)
    
    def __post_init__(self):
        """Mark plan as immutable after initialization."""
        object.__setattr__(self, '_immutable', True)
    
    def __setattr__(self, key, value):
        """Enforce immutability (no modifications after creation)."""
        if hasattr(self, '_immutable') and object.__getattribute__(self, '_immutable'):
            raise AttributeError(f"Stage4ExecutionPlan is immutable. Cannot set '{key}'.")
        object.__setattr__(self, key, value)
