# ARES — Active Defense & Deterrence
# Phase 0: Detection, Deception, Reporting
# No execution authority
# No persistence
# No autonomy
# Reports to Artemis only

"""
Honeypots: Fake endpoints and fake secrets.

Honeypots:
- Fake credentials
- Fake capabilities
- Fake domain adapters
- Never real
- Never leak real structure
- Only record interaction

Does:
- Record access
- Emit signals
- Provide deceptive responses

Does NOT:
- Escalate automatically
- Persist
- Execute
- Leak real data
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib

from .signals import Signal, SignalType, ConfidenceLevel


@dataclass(frozen=True)
class HoneypotRecord:
    """
    Record of honeypot interaction (immutable).
    
    Does:
    - Records when honeypot was accessed
    - Captures context
    - Frozen (immutable)
    
    Does NOT:
    - Persist
    - Execute
    - Escalate
    """
    
    record_id: str
    honeypot_id: str
    honeypot_type: str  # "credential", "capability", "adapter"
    timestamp: datetime
    accessed_by: str  # subsystem that accessed
    access_context: str
    context: Dict[str, Any]
    
    @staticmethod
    def create(
        honeypot_id: str,
        honeypot_type: str,
        accessed_by: str,
        access_context: str,
        context: Dict[str, Any] = None,
    ) -> "HoneypotRecord":
        """
        Create honeypot interaction record.
        
        Does:
        - Records access with timestamp
        - Freezes context
        
        Does NOT:
        - Execute
        - Persist
        - Escalate
        """
        timestamp = datetime.utcnow()
        id_str = f"{honeypot_id}_{timestamp.isoformat()}_{accessed_by}"
        record_id = f"hp-{hashlib.sha256(id_str.encode()).hexdigest()[:12]}"
        
        return HoneypotRecord(
            record_id=record_id,
            honeypot_id=honeypot_id,
            honeypot_type=honeypot_type,
            timestamp=timestamp,
            accessed_by=accessed_by,
            access_context=access_context,
            context=dict(context) if context else {},
        )


class Honeypot:
    """
    Base honeypot (fake endpoint).
    
    Does:
    - Provides fake data
    - Records access
    - Emits signal
    
    Does NOT:
    - Use real credentials
    - Leak real structure
    - Persist
    - Execute
    - Escalate automatically
    """
    
    def __init__(self, honeypot_id: str, honeypot_type: str):
        """Initialize honeypot (does NOT execute on import)."""
        self.honeypot_id = honeypot_id
        self.honeypot_type = honeypot_type
        self._access_count = 0
    
    def record_access(
        self,
        accessed_by: str,
        access_context: str,
    ) -> tuple:
        """
        Record access to honeypot.
        
        Returns:
        - (HoneypotRecord, Signal)
        
        Does:
        - Records access
        - Creates signal if multiple accesses
        - Returns immutable records
        
        Does NOT:
        - Persist
        - Execute
        - Escalate automatically
        """
        self._access_count += 1
        
        record = HoneypotRecord.create(
            honeypot_id=self.honeypot_id,
            honeypot_type=self.honeypot_type,
            accessed_by=accessed_by,
            access_context=access_context,
            context={"access_number": self._access_count},
        )
        
        signal = None
        if self._access_count >= 3:
            signal = Signal.create(
                signal_type=SignalType.HONEYPOT_TRIGGER,
                source_subsystem=accessed_by,
                confidence=ConfidenceLevel.HIGH,
                description=f"Honeypot accessed multiple times: {self.honeypot_type}",
                evidence_reference=self.honeypot_id,
                context=f"Access count: {self._access_count}",
            )
        
        return record, signal


class FakeCredential(Honeypot):
    """
    Fake credential (honeypot).
    
    Does:
    - Provides dummy credentials
    - Records access
    - Emits signal
    
    Does NOT:
    - Use real credentials
    - Grant real access
    - Persist
    - Execute
    """
    
    def get_credential(self, accessed_by: str) -> tuple:
        """
        Get fake credential.
        
        Returns:
        - (credential_dict, HoneypotRecord, Optional[Signal])
        
        Does:
        - Returns dummy credential
        - Records access
        - Emits signal if suspicious
        
        Does NOT:
        - Return real credential
        - Persist
        - Execute
        """
        record, signal = self.record_access(
            accessed_by=accessed_by,
            access_context="credential_request",
        )
        
        # Return fake credential (never real)
        fake_credential = {
            "username": "admin_honeypot_user",
            "password": "fake_password_not_real",
            "token": "fake_token_xyz123",
            "type": "honeypot",
        }
        
        return fake_credential, record, signal


class FakeCapability(Honeypot):
    """
    Fake capability (honeypot).
    
    Does:
    - Provides dummy capability
    - Records access
    - Emits signal
    
    Does NOT:
    - Provide real capability
    - Persist
    - Execute
    """
    
    def get_capability(self, accessed_by: str) -> tuple:
        """
        Get fake capability.
        
        Returns:
        - (capability_dict, HoneypotRecord, Optional[Signal])
        
        Does:
        - Returns dummy capability
        - Records access
        - Emits signal if suspicious
        
        Does NOT:
        - Return real capability
        - Persist
        - Execute
        """
        record, signal = self.record_access(
            accessed_by=accessed_by,
            access_context="capability_request",
        )
        
        # Return fake capability (never real)
        fake_capability = {
            "name": "fake_admin_capability",
            "permissions": ["read:honeypot"],
            "tier": "honeypot",
            "real": False,
        }
        
        return fake_capability, record, signal


class FakeAdapter(Honeypot):
    """
    Fake domain adapter (honeypot).
    
    Does:
    - Provides dummy adapter interface
    - Records access
    - Emits signal
    
    Does NOT:
    - Provide real adapter
    - Leak real adapter structure
    - Persist
    - Execute
    """
    
    def get_adapter(self, accessed_by: str) -> tuple:
        """
        Get fake adapter.
        
        Returns:
        - (adapter_dict, HoneypotRecord, Optional[Signal])
        
        Does:
        - Returns dummy adapter
        - Records access
        - Emits signal if suspicious
        
        Does NOT:
        - Return real adapter
        - Persist
        - Execute
        """
        record, signal = self.record_access(
            accessed_by=accessed_by,
            access_context="adapter_request",
        )
        
        # Return fake adapter (never real structure)
        fake_adapter = {
            "name": "fake_domain_adapter",
            "domain": "honeypot_domain",
            "version": "0.0.0",
            "methods": ["fake_method_1", "fake_method_2"],
            "real": False,
        }
        
        return fake_adapter, record, signal


class HoneypotFactory:
    """
    Factory for creating honeypots.
    
    Does:
    - Creates honeypot instances
    - Tracks honeypots
    
    Does NOT:
    - Execute
    - Persist
    - Escalate
    """
    
    def __init__(self):
        """Initialize factory (does NOT execute on import)."""
        self.honeypots: Dict[str, Honeypot] = {}
    
    def create_fake_credential(self, honeypot_id: str) -> FakeCredential:
        """
        Create fake credential honeypot.
        
        Does:
        - Creates honeypot instance
        - Registers in factory
        
        Does NOT:
        - Persist
        - Execute
        """
        honeypot = FakeCredential(honeypot_id, "credential")
        self.honeypots[honeypot_id] = honeypot
        return honeypot
    
    def create_fake_capability(self, honeypot_id: str) -> FakeCapability:
        """
        Create fake capability honeypot.
        
        Does:
        - Creates honeypot instance
        - Registers in factory
        
        Does NOT:
        - Persist
        - Execute
        """
        honeypot = FakeCapability(honeypot_id, "capability")
        self.honeypots[honeypot_id] = honeypot
        return honeypot
    
    def create_fake_adapter(self, honeypot_id: str) -> FakeAdapter:
        """
        Create fake adapter honeypot.
        
        Does:
        - Creates honeypot instance
        - Registers in factory
        
        Does NOT:
        - Persist
        - Execute
        """
        honeypot = FakeAdapter(honeypot_id, "adapter")
        self.honeypots[honeypot_id] = honeypot
        return honeypot


# Global honeypot factory (does NOT execute on import)
_factory = None


def get_factory() -> HoneypotFactory:
    """
    Get honeypot factory.
    
    Does:
    - Returns factory (creates if needed)
    
    Does NOT:
    - Execute
    - Persist
    """
    global _factory
    if _factory is None:
        _factory = HoneypotFactory()
    return _factory
