"""
Memory Decay Scheduler - Periodic evaluation and decay of memories.

Deterministic, configurable, non-autonomous memory lifecycle management.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID

from pydantic import BaseModel, Field

from ..core.kernel import IService, ServiceInfo, ServiceStatus
from ..shared.logging.structured_logger import StructuredLogger
from ..shared.schemas.memory import MemoryStatus, MemoryType


class DecayStrategy(Enum):
    """Memory decay strategies."""
    TIME_BASED = "time_based"          # Decay based on age
    ACCESS_BASED = "access_based"      # Decay based on last access
    CONFIDENCE_BASED = "confidence_based" # Decay based on confidence
    HYBRID = "hybrid"                  # Combination of strategies


class DecayAction(Enum):
    """Actions to take on decayed memories."""
    SUMMARIZE = "summarize"      # Create summary and archive
    ARCHIVE = "archive"          # Move to archive storage
    FLAG_REVIEW = "flag_review"  # Flag for human review
    NO_ACTION = "no_action"      # Just update confidence


@dataclass
class DecayRule:
    """Rule for memory decay."""
    memory_type: MemoryType
    strategy: DecayStrategy
    decay_rate: float  # Per day (0.0 - 1.0)
    min_confidence: float = 0.1
    review_threshold: float = 0.3
    action: DecayAction = DecayAction.SUMMARIZE
    enabled: bool = True


class DecayEvent(BaseModel):
    """Event recording memory decay."""
    event_id: UUID = Field(default_factory=UUID)
    memory_id: UUID
    memory_type: MemoryType
    
    # Before/after values
    old_confidence: float
    new_confidence: float
    old_status: MemoryStatus
    new_status: MemoryStatus
    
    # Decay calculation
    decay_amount: float
    decay_reason: str
    
    # Action taken
    action: Optional[DecayAction] = None
    action_result: Optional[str] = None
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    scheduler_run_id: str
    
    class Config:
        use_enum_values = True


class DecayScheduler(IService):
    """
    Periodic memory decay scheduler.
    
    Features:
    - Deterministic decay calculations
    - Configurable decay rules
    - Non-autonomous (requires approval for major actions)
    - Audit trail of all decay events
    """
    
    def __init__(self, config: Optional[Dict[str, any]] = None):
        self.config = config or {}
        self.logger = StructuredLogger(__name__)
        
        # Decay rules
        self.decay_rules: Dict[MemoryType, DecayRule] = {}
        self._initialize_default_rules()
        
        # Scheduler state
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count: int = 0
        self.events: List[DecayEvent] = []
        
        # Service info
        self.service_info = ServiceInfo(
            name="mnemosyne_decay_scheduler",
            version="0.1.0",
            dependencies=["mnemosyne_memory_store"]
        )
        
        # Scheduling configuration
        self.interval_hours = self.config.get("interval_hours", 24)  # Daily by default
        self.batch_size = self.config.get("batch_size", 100)
        
        self.logger.info(
            "Decay scheduler initialized",
            interval_hours=self.interval_hours,
            batch_size=self.batch_size
        )
    
    def _initialize_default_rules(self) -> None:
        """Initialize default decay rules."""
        # Episodic memories decay faster
        self.decay_rules[MemoryType.EPISODIC] = DecayRule(
            memory_type=MemoryType.EPISODIC,
            strategy=DecayStrategy.HYBRID,
            decay_rate=0.05,  # 5% per day
            min_confidence=0.1,
            review_threshold=0.4,
            action=DecayAction.SUMMARIZE,
            enabled=True
        )
        
        # Structured memories decay slower
        self.decay_rules[MemoryType.STRUCTURED] = DecayRule(
            memory_type=MemoryType.STRUCTURED,
            strategy=DecayStrategy.ACCESS_BASED,
            decay_rate=0.02,  # 2% per day
            min_confidence=0.2,
            review_threshold=0.5,
            action=DecayAction.FLAG_REVIEW,
            enabled=True
        )
        
        # Behavioral memories have medium decay
        self.decay_rules[MemoryType.BEHAVIORAL] = DecayRule(
            memory_type=MemoryType.BEHAVIORAL,
            strategy=DecayStrategy.TIME_BASED,
            decay_rate=0.03,  # 3% per day
            min_confidence=0.15,
            review_threshold=0.35,
            action=DecayAction.ARCHIVE,
            enabled=True
        )
        
        # Identity memories never decay
        self.decay_rules[MemoryType.IDENTITY] = DecayRule(
            memory_type=MemoryType.IDENTITY,
            strategy=DecayStrategy.TIME_BASED,
            decay_rate=0.0,  # No decay
            min_confidence=1.0,
            review_threshold=1.0,
            action=DecayAction.NO_ACTION,
            enabled=False  # Identity memories are immutable
        )
    
    async def start(self) -> None:
        """Start the decay scheduler service."""
        self.service_info.status = ServiceStatus.STARTING
        
        # Schedule first run
        self.next_run = datetime.now() + timedelta(hours=self.interval_hours)
        
        self.service_info.status = ServiceStatus.RUNNING
        self.logger.info("Decay scheduler started")
    
    async def stop(self) -> None:
        """Stop the decay scheduler service."""
        self.service_info.status = ServiceStatus.STOPPING
        
        # Clear next run
        self.next_run = None
        
        self.service_info.status = ServiceStatus.STOPPED
        self.logger.info("Decay scheduler stopped")
    
    def get_service_info(self) -> ServiceInfo:
        return self.service_info
    
    async def health_check(self) -> bool:
        """Health check for decay scheduler."""
        return self.service_info.status == ServiceStatus.RUNNING
    
    async def run_decay_cycle(self) -> Dict[str, any]:
        """
        Run a single decay cycle.
        
        Returns:
            Statistics about the decay cycle
        """
        if not self._should_run():
            return {"run": False, "reason": "not_due"}
        
        run_id = f"decay_run_{self.run_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger.info("Starting decay cycle", run_id=run_id)
        
        # Update run tracking
        self.last_run = datetime.now()
        self.next_run = self.last_run + timedelta(hours=self.interval_hours)
        self.run_count += 1
        
        # Get memory store
        memory_store = await self._get_memory_store()
        if not memory_store:
            self.logger.error("Memory store not available")
            return {"run": False, "reason": "memory_store_unavailable"}
        
        # Run decay for each memory type
        statistics = {
            "run_id": run_id,
            "start_time": self.last_run.isoformat(),
            "memory_types": {}
        }
        
        for memory_type, rule in self.decay_rules.items():
            if not rule.enabled:
                continue
            
            type_stats = await self._decay_memory_type(
                memory_store=memory_store,
                memory_type=memory_type,
                rule=rule,
                run_id=run_id
            )
            
            statistics["memory_types"][memory_type.value] = type_stats
        
        statistics["end_time"] = datetime.now().isoformat()
        statistics["total_duration_seconds"] = (
            datetime.now() - self.last_run
        ).total_seconds()
        statistics["total_memories_processed"] = sum(
            stats.get("processed", 0) 
            for stats in statistics["memory_types"].values()
        )
        
        self.logger.info(
            "Decay cycle completed",
            run_id=run_id,
            total_processed=statistics["total_memories_processed"],
            total_duration=statistics["total_duration_seconds"]
        )
        
        return statistics
    
    def _should_run(self) -> bool:
        """Check if decay cycle should run."""
        if not self.next_run:
            return True
        
        now = datetime.now()
        return now >= self.next_run
    
    async def _get_memory_store(self):
        """Get memory store service."""
        # TODO: Get from service registry
        # This is a placeholder - actual implementation would use service registry
        return None
    
    async def _decay_memory_type(
        self,
        memory_store,
        memory_type: MemoryType,
        rule: DecayRule,
        run_id: str
    ) -> Dict[str, any]:
        """Apply decay to memories of a specific type."""
        self.logger.debug(
            "Decaying memory type",
            memory_type=memory_type.value,
            rule=str(rule)
        )
        
        # Get memories to decay
        memories = await self._get_memories_for_decay(
            memory_store,
            memory_type,
            rule
        )
        
        if not memories:
            return {
                "processed": 0,
                "decayed": 0,
                "actions_taken": {},
                "errors": 0
            }
        
        # Apply decay to each memory
        decayed_count = 0
        actions_taken = {}
        errors = 0
        
        for memory in memories[:self.batch_size]:  # Limit batch size
            try:
                result = await self._apply_decay(
                    memory_store=memory_store,
                    memory=memory,
                    rule=rule,
                    run_id=run_id
                )
                
                if result["decayed"]:
                    decayed_count += 1
                
                # Track actions
                action = result.get("action")
                if action:
                    actions_taken[action.value] = actions_taken.get(action.value, 0) + 1
                
            except Exception as e:
                self.logger.error(
                    "Error applying decay to memory",
                    memory_id=str(memory.memory_id)[:8],
                    error=str(e)
                )
                errors += 1
        
        return {
            "processed": len(memories),
            "decayed": decayed_count,
            "actions_taken": actions_taken,
            "errors": errors,
            "batch_limit_reached": len(memories) > self.batch_size
        }
    
    async def _get_memories_for_decay(self, memory_store, memory_type: MemoryType, rule: DecayRule):
        """Get memories eligible for decay."""
        # TODO: Implement memory query
        # This would query memories that are active and haven't been recently decayed
        return []
    
    async def _apply_decay(
        self,
        memory_store,
        memory,
        rule: DecayRule,
        run_id: str
    ) -> Dict[str, any]:
        """Apply decay to a single memory."""
        # Calculate decay amount
        decay_amount = self._calculate_decay_amount(memory, rule)
        
        if decay_amount <= 0:
            return {"decayed": False, "reason": "no_decay_needed"}
        
        # Apply decay to confidence
        new_confidence = max(rule.min_confidence, memory.confidence - decay_amount)
        
        # Determine action based on new confidence
        action = self._determine_decay_action(memory, new_confidence, rule)
        
        # Record event
        event = DecayEvent(
            memory_id=memory.memory_id,
            memory_type=memory.memory_type,
            old_confidence=memory.confidence,
            new_confidence=new_confidence,
            old_status=memory.status,
            new_status=memory.status,  # Status might change based on action
            decay_amount=decay_amount,
            decay_reason=self._get_decay_reason(memory, rule),
            action=action,
            scheduler_run_id=run_id
        )
        
        # Take action if needed
        action_result = None
        if action and action != DecayAction.NO_ACTION:
            action_result = await self._execute_decay_action(
                memory_store, memory, action, new_confidence
            )
            event.action_result = action_result
        
        # Store event
        self.events.append(event)
        
        # Keep only last 1000 events
        if len(self.events) > 1000:
            self.events = self.events[-1000:]
        
        return {
            "decayed": True,
            "decay_amount": decay_amount,
            "new_confidence": new_confidence,
            "action": action,
            "action_result": action_result
        }
    
    def _calculate_decay_amount(self, memory, rule: DecayRule) -> float:
        """Calculate decay amount based on strategy."""
        base_decay = rule.decay_rate / 24.0  # Convert daily rate to hourly
        
        if rule.strategy == DecayStrategy.TIME_BASED:
            # Decay based on age
            age_days = (datetime.now() - memory.created_at).total_seconds() / 86400
            return base_decay * age_days
        
        elif rule.strategy == DecayStrategy.ACCESS_BASED:
            # Decay based on last access
            if hasattr(memory, 'accessed_at'):
                inactive_days = (datetime.now() - memory.accessed_at).total_seconds() / 86400
                return base_decay * inactive_days
            return base_decay
        
        elif rule.strategy == DecayStrategy.CONFIDENCE_BASED:
            # Decay proportional to current confidence
            return base_decay * memory.confidence
        
        elif rule.strategy == DecayStrategy.HYBRID:
            # Combined strategy
            age_decay = base_decay * (datetime.now() - memory.created_at).total_seconds() / 86400
            confidence_decay = base_decay * memory.confidence
            return (age_decay + confidence_decay) / 2.0
        
        return base_decay
    
    def _determine_decay_action(
        self,
        memory,
        new_confidence: float,
        rule: DecayRule
    ) -> Optional[DecayAction]:
        """Determine action to take based on decayed confidence."""
        if new_confidence <= rule.min_confidence:
            # Memory has decayed below minimum
            if rule.action == DecayAction.SUMMARIZE:
                return DecayAction.SUMMARIZE
            elif rule.action == DecayAction.ARCHIVE:
                return DecayAction.ARCHIVE
            elif rule.action == DecayAction.FLAG_REVIEW:
                return DecayAction.FLAG_REVIEW
        
        elif new_confidence <= rule.review_threshold:
            # Memory needs review
            return DecayAction.FLAG_REVIEW
        
        return DecayAction.NO_ACTION
    
    def _get_decay_reason(self, memory, rule: DecayRule) -> str:
        """Get human-readable decay reason."""
        reasons = []
        
        if rule.strategy == DecayStrategy.TIME_BASED:
            age_days = (datetime.now() - memory.created_at).days
            reasons.append(f"age: {age_days} days")
        
        if rule.strategy == DecayStrategy.ACCESS_BASED and hasattr(memory, 'accessed_at'):
            inactive_days = (datetime.now() - memory.accessed_at).days
            reasons.append(f"inactive: {inactive_days} days")
        
        if rule.strategy == DecayStrategy.CONFIDENCE_BASED:
            reasons.append(f"confidence_based: {memory.confidence:.2f}")
        
        if not reasons:
            return f"{rule.strategy.value} decay"
        
        return f"{rule.strategy.value} decay ({', '.join(reasons)})"
    
    async def _execute_decay_action(
        self,
        memory_store,
        memory,
        action: DecayAction,
        new_confidence: float
    ) -> str:
        """Execute decay action on memory."""
        if action == DecayAction.SUMMARIZE:
            # Create summary and archive
            # TODO: Implement summarization
            return "flagged_for_summarization"
        
        elif action == DecayAction.ARCHIVE:
            # Archive memory
            # TODO: Implement archival
            return "flagged_for_archival"
        
        elif action == DecayAction.FLAG_REVIEW:
            # Flag for human review
            # TODO: Implement review flagging
            return "flagged_for_review"
        
        return "no_action_taken"
    
    def get_decay_statistics(self) -> Dict[str, any]:
        """Get decay scheduler statistics."""
        # Calculate confidence distribution from recent events
        confidence_changes = []
        for event in self.events[-100:]:  # Last 100 events
            confidence_changes.append(event.old_confidence - event.new_confidence)
        
        avg_decay = sum(confidence_changes) / max(len(confidence_changes), 1)
        
        return {
            "run_count": self.run_count,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "total_events": len(self.events),
            "recent_avg_decay": avg_decay,
            "rules_active": [
                {
                    "memory_type": rule.memory_type.value,
                    "strategy": rule.strategy.value,
                    "decay_rate": rule.decay_rate,
                    "enabled": rule.enabled
                }
                for rule in self.decay_rules.values()
            ]
        }
    
    def update_decay_rule(
        self,
        memory_type: MemoryType,
        **updates
    ) -> bool:
        """Update decay rule for a memory type."""
        if memory_type not in self.decay_rules:
            return False
        
        rule = self.decay_rules[memory_type]
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        self.logger.info(
            "Decay rule updated",
            memory_type=memory_type.value,
            updates=updates
        )
        
        return True
    
    def get_recent_events(
        self,
        memory_type: Optional[MemoryType] = None,
        limit: int = 50
    ) -> List[DecayEvent]:
        """Get recent decay events."""
        events = self.events
        
        if memory_type:
            events = [e for e in events if e.memory_type == memory_type]
        
        return events[-limit:] if events else []