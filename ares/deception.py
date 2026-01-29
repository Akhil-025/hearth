# ARES — Active Defense & Deterrence
# Phase 0: Detection, Deception, Reporting
# No execution authority
# No persistence
# No autonomy
# Reports to Artemis only

"""
Deceptive responses and tarpitting logic.

Allowed:
- Artificial latency
- Benign dummy responses
- No-op execution paths

Not allowed:
- Infinite loops
- Deadlocks
- Resource exhaustion
- Crashes

Goal: Slow + observe, not punish.

Does:
- Add latency
- Return dummy responses
- Record deception interaction
- Emit signals

Does NOT:
- Crash system
- Block indefinitely
- Exhaust resources
- Persist
- Execute
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import time
import hashlib

from .signals import Signal, SignalType, ConfidenceLevel


@dataclass(frozen=True)
class DeceptionRecord:
    """
    Record of deception interaction (immutable).
    
    Does:
    - Records when deception was employed
    - Captures context
    - Frozen (immutable)
    
    Does NOT:
    - Persist
    - Execute
    - Escalate
    """
    
    record_id: str
    deception_type: str
    timestamp: datetime
    target_subsystem: str
    latency_ms: int
    context: Dict[str, Any]
    
    @staticmethod
    def create(
        deception_type: str,
        target_subsystem: str,
        latency_ms: int,
        context: Dict[str, Any] = None,
    ) -> "DeceptionRecord":
        """
        Create deception record.
        
        Does:
        - Records deception with timestamp
        - Freezes context
        
        Does NOT:
        - Execute
        - Persist
        - Escalate
        """
        timestamp = datetime.utcnow()
        id_str = f"{deception_type}_{target_subsystem}_{timestamp.isoformat()}"
        record_id = f"dec-{hashlib.sha256(id_str.encode()).hexdigest()[:12]}"
        
        return DeceptionRecord(
            record_id=record_id,
            deception_type=deception_type,
            timestamp=timestamp,
            target_subsystem=target_subsystem,
            latency_ms=latency_ms,
            context=dict(context) if context else {},
        )


class DeceptionEngine:
    """
    Deceptive response engine.
    
    Does:
    - Add artificial latency (bounded)
    - Return dummy responses
    - Record deception
    - Emit signals
    
    Does NOT:
    - Crash system
    - Block indefinitely
    - Exhaust resources
    - Persist
    - Execute real operations
    """
    
    # Maximum latencies (prevent resource exhaustion)
    MAX_LATENCY_MS = 5000  # 5 seconds max
    MAX_ITERATIONS = 100  # Max loops
    
    def __init__(self):
        """Initialize engine (does NOT execute on import)."""
        pass
    
    def add_bounded_latency(
        self,
        base_latency_ms: int,
        target_subsystem: str,
    ) -> tuple:
        """
        Add artificial latency (bounded, safe).
        
        Args:
        - base_latency_ms: Requested latency
        - target_subsystem: What's being delayed
        
        Returns:
        - (actual_latency_ms, DeceptionRecord, Optional[Signal])
        
        Does:
        - Sleeps for bounded time
        - Records deception
        - Emits signal if suspicious
        
        Does NOT:
        - Sleep indefinitely
        - Crash
        - Persist
        - Execute
        """
        # Bound latency (never > MAX_LATENCY_MS)
        actual_latency_ms = min(base_latency_ms, self.MAX_LATENCY_MS)
        
        # Sleep (safe, bounded)
        time.sleep(actual_latency_ms / 1000.0)
        
        # Record deception
        record = DeceptionRecord.create(
            deception_type="artificial_latency",
            target_subsystem=target_subsystem,
            latency_ms=actual_latency_ms,
            context={"requested": base_latency_ms, "actual": actual_latency_ms},
        )
        
        # Emit signal if excessive latency requested
        signal = None
        if base_latency_ms > 1000:
            signal = Signal.create(
                signal_type=SignalType.SUSPICIOUS_TIMING,
                source_subsystem=target_subsystem,
                confidence=ConfidenceLevel.MEDIUM,
                description=f"Excessive latency requested: {base_latency_ms}ms",
                evidence_reference="deception_latency",
                context=f"Capped at {actual_latency_ms}ms",
            )
        
        return actual_latency_ms, record, signal
    
    def benign_dummy_response(
        self,
        response_type: str,
        target_subsystem: str,
    ) -> tuple:
        """
        Return benign dummy response.
        
        Args:
        - response_type: "list", "dict", "string", "number"
        - target_subsystem: What requested response
        
        Returns:
        - (dummy_response, DeceptionRecord, Optional[Signal])
        
        Does:
        - Returns dummy data
        - Records deception
        
        Does NOT:
        - Return real data
        - Persist
        - Execute
        """
        # Create benign dummy response
        if response_type == "list":
            dummy = ["dummy_item_1", "dummy_item_2", "dummy_item_3"]
        elif response_type == "dict":
            dummy = {
                "status": "dummy_response",
                "version": "0.0.0",
                "data": "benign",
            }
        elif response_type == "string":
            dummy = "benign_dummy_response"
        elif response_type == "number":
            dummy = 42
        else:
            dummy = None
        
        record = DeceptionRecord.create(
            deception_type="dummy_response",
            target_subsystem=target_subsystem,
            latency_ms=0,
            context={"response_type": response_type},
        )
        
        return dummy, record, None
    
    def no_op_execution_path(
        self,
        operation_name: str,
        target_subsystem: str,
    ) -> tuple:
        """
        Execute no-op (does nothing, returns success).
        
        Args:
        - operation_name: Name of operation
        - target_subsystem: What requested operation
        
        Returns:
        - (no_op_result, DeceptionRecord, Optional[Signal])
        
        Does:
        - Executes no-op
        - Records deception
        - Returns success response
        
        Does NOT:
        - Execute real operation
        - Modify state
        - Persist
        """
        # Execute no-op (safe, does nothing)
        no_op_result = {
            "status": "success",
            "operation": operation_name,
            "type": "no_op",
            "affected": 0,
        }
        
        record = DeceptionRecord.create(
            deception_type="no_op_path",
            target_subsystem=target_subsystem,
            latency_ms=0,
            context={"operation": operation_name},
        )
        
        return no_op_result, record, None
    
    def repeated_no_op_loop(
        self,
        iteration_count: int,
        target_subsystem: str,
    ) -> tuple:
        """
        Execute repeated no-ops (bounded).
        
        Args:
        - iteration_count: Requested iterations
        - target_subsystem: What requested
        
        Returns:
        - (results, DeceptionRecord, Optional[Signal])
        
        Does:
        - Executes bounded no-op loop
        - Records deception
        - Emits signal if suspicious
        
        Does NOT:
        - Loop indefinitely
        - Crash
        - Exhaust resources
        - Persist
        """
        # Bound iterations (never > MAX_ITERATIONS)
        actual_iterations = min(iteration_count, self.MAX_ITERATIONS)
        
        results = []
        for i in range(actual_iterations):
            results.append({"iteration": i, "status": "noop"})
        
        record = DeceptionRecord.create(
            deception_type="repeated_no_op",
            target_subsystem=target_subsystem,
            latency_ms=0,
            context={
                "requested_iterations": iteration_count,
                "actual_iterations": actual_iterations,
            },
        )
        
        # Emit signal if excessive iterations requested
        signal = None
        if iteration_count > self.MAX_ITERATIONS:
            signal = Signal.create(
                signal_type=SignalType.SUSPICIOUS_TIMING,
                source_subsystem=target_subsystem,
                confidence=ConfidenceLevel.MEDIUM,
                description=f"Excessive iterations requested: {iteration_count}",
                evidence_reference="deception_loop",
                context=f"Capped at {actual_iterations}",
            )
        
        return results, record, signal


# Global deception engine (does NOT execute on import)
_engine = None


def get_engine() -> DeceptionEngine:
    """
    Get deception engine.
    
    Does:
    - Returns engine (creates if needed)
    
    Does NOT:
    - Execute
    - Persist
    """
    global _engine
    if _engine is None:
        _engine = DeceptionEngine()
    return _engine
