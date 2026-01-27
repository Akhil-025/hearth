"""
Memory schemas - Strict type definitions for memory system.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from .base import BaseSchema, TimestampMixin


class MemoryType(Enum):
    """Memory type classification."""
    IDENTITY = "identity"
    STRUCTURED = "structured"
    EPISODIC = "episodic"
    BEHAVIORAL = "behavioral"


class MemoryStatus(Enum):
    """Memory lifecycle status."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    EXPIRED = "expired"


class MemoryPriority(Enum):
    """Memory importance priority."""
    CRITICAL = 100
    HIGH = 75
    MEDIUM = 50
    LOW = 25
    TRIVIAL = 1


class IdentityMemory(BaseSchema, TimestampMixin):
    """
    Immutable identity memory.
    
    Never modified, only appended with new versions.
    """
    memory_id: UUID = Field(default_factory=uuid4)
    user_id: str
    version: int = 1
    memory_type: MemoryType = MemoryType.IDENTITY
    
    # Identity fields
    profile: Dict[str, Any] = Field(default_factory=dict)
    constraints: List[str] = Field(default_factory=list)
    system_rules: List[str] = Field(default_factory=list)
    
    # Metadata
    source: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    immutable: bool = True
    
    class Config:
        validate_assignment = True


class StructuredMemory(BaseSchema, TimestampMixin):
    """
    Structured memory stored in SQL.
    
    Preferences, templates, projects, people, facts.
    """
    memory_id: UUID = Field(default_factory=uuid4)
    user_id: str
    memory_type: MemoryType = MemoryType.STRUCTURED
    
    # Classification
    category: str  # preferences, templates, projects, people, facts
    subcategory: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # Content
    key: str  # Unique identifier within category
    value: Any
    schema_version: str = "1.0"
    
    # Relationships
    parent_id: Optional[UUID] = None
    related_ids: List[UUID] = Field(default_factory=list)
    
    # Metadata
    priority: MemoryPriority = MemoryPriority.MEDIUM
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    expires_at: Optional[datetime] = None
    status: MemoryStatus = MemoryStatus.ACTIVE
    
    # Add provenance field
    provenance: ProvenanceInfo = Field(default_factory=ProvenanceInfo)
    
    # Update validator to preserve provenance
    @validator('value')
    def validate_structured_value(cls, v, values):
        """Ensure value is JSON serializable."""
        import json
        try:
            json.dumps(v)
            return v
        except (TypeError, ValueError):
            raise ValueError("Value must be JSON serializable")


class EpisodicMemory(BaseSchema, TimestampMixin):
    """
    Episodic memory stored in vector DB.
    
    Conversations, decisions, events, reflections.
    """
    memory_id: UUID = Field(default_factory=uuid4)
    user_id: str
    memory_type: MemoryType = MemoryType.EPISODIC
    
    # Temporal context
    occurred_at: datetime
    duration_seconds: Optional[float] = None
    
    # Content
    title: str
    description: str
    raw_content: Optional[str] = None  # Original unprocessed content
    summary: Optional[str] = None
    embedding: Optional[List[float]] = None  # Vector embedding
    
    # Classification
    event_type: str  # conversation, decision, event, reflection
    emotional_tone: Optional[Dict[str, float]] = None  # sentiment analysis
    participants: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    
    # Metadata
    priority: MemoryPriority = MemoryPriority.MEDIUM
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    source: str
    privacy_level: int = Field(ge=1, le=10, default=5)
    
    # Relationships
    related_memory_ids: List[UUID] = Field(default_factory=list)
    conversation_id: Optional[UUID] = None  # For grouping related episodes

    provenance: ProvenanceInfo = Field(default_factory=ProvenanceInfo)
    
    @validator('embedding')
    def validate_embedding(cls, v):
        """Validate embedding dimensions."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("Embedding must be a list")
            if len(v) not in [384, 768, 1536]:  # Common embedding dimensions
                raise ValueError(f"Embedding dimension {len(v)} not supported")
        return v


class BehavioralMemory(BaseSchema, TimestampMixin):
    """
    Behavioral memory based on patterns and rules.
    
    Time patterns, usage frequency, habit inference.
    """
    memory_id: UUID = Field(default_factory=uuid4)
    user_id: str
    memory_type: MemoryType = MemoryType.BEHAVIORAL
    
    # Pattern definition
    pattern_type: str  # time_pattern, frequency, habit
    pattern_data: Dict[str, Any]
    
    # Statistical data
    occurrences: int = 0
    first_observed: datetime
    last_observed: datetime
    average_interval_seconds: Optional[float] = None
    standard_deviation: Optional[float] = None
    
    # Inference
    confidence: float = Field(ge=0.0, le=1.0, default=0.6)
    stability_score: float = Field(ge=0.0, le=1.0, default=0.5)  # How stable is the pattern
    
    # Metadata
    triggers: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    context_requirements: Dict[str, Any] = Field(default_factory=dict)

    provenance: ProvenanceInfo = Field(default_factory=ProvenanceInfo)
    
    @validator('pattern_data')
    def validate_pattern_data(cls, v):
        """Validate pattern data structure."""
        if not isinstance(v, dict):
            raise ValueError("Pattern data must be a dictionary")
        return v


class MemoryProposal(BaseSchema):
    """
    Memory write proposal for explicit governance.
    
    All memory writes must go through proposals.
    """
    proposal_id: UUID = Field(default_factory=uuid4)
    requester: str  # Service making the proposal
    operation: str  # CREATE, UPDATE, DELETE, ARCHIVE
    
    # Target memory
    memory_type: MemoryType
    existing_memory_id: Optional[UUID] = None  # For updates/deletes
    
    # New memory data
    new_memory: Optional[Dict[str, Any]] = None
    
    # Justification
    reason: str
    context: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    # Review
    requires_approval: bool = True
    approved: Optional[bool] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # Status
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "pending"  # pending, approved, rejected, executed
    
    @validator('new_memory')
    def validate_new_memory(cls, v, values):
        """Validate new memory matches operation."""
        operation = values.get('operation')
        memory_type = values.get('memory_type')
        
        if operation == 'CREATE' and not v:
            raise ValueError("New memory required for CREATE operation")
        
        if operation in ['UPDATE', 'CREATE'] and v:
            # Validate memory structure based on type
            if memory_type == MemoryType.IDENTITY:
                required_fields = ['user_id', 'profile', 'source']
            elif memory_type == MemoryType.STRUCTURED:
                required_fields = ['user_id', 'category', 'key', 'value']
            elif memory_type == MemoryType.EPISODIC:
                required_fields = ['user_id', 'occurred_at', 'title', 'description']
            
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Missing required field: {field}")
        
        return v
    
class InferenceMethod(Enum):
    """Methods used for memory inference."""
    DIRECT_OBSERVATION = "direct_observation"
    USER_PROVIDED = "user_provided"
    LLM_INFERENCE = "llm_inference"
    PATTERN_DETECTION = "pattern_detection"
    LOGICAL_DEDUCTION = "logical_deduction"
    EXTERNAL_SOURCE = "external_source"


class ProvenanceInfo(BaseModel):
    """Provenance information for memory items."""
    derived_from: List[UUID] = Field(default_factory=list)
    inferred_by: Optional[str] = None  # Service/module that made inference
    inference_method: Optional[InferenceMethod] = None
    inference_confidence: Optional[float] = None
    source_checksum: Optional[str] = None  # Checksum of source data
    transformation_history: List[Dict[str, any]] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class MemoryLineage(BaseModel):
    """Tracks lineage from source memories to summaries."""
    lineage_id: UUID = Field(default_factory=uuid4)
    summary_memory_id: UUID
    source_memory_ids: List[UUID] = Field(default_factory=list)
    summarization_method: str
    summarization_confidence: float = Field(ge=0.0, le=1.0)
    preserved_elements: List[str] = Field(default_factory=list)
    lost_elements: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


# Helper functions for provenance tracking

def create_provenance(
    derived_from: List[UUID] = None,
    inferred_by: Optional[str] = None,
    inference_method: Optional[InferenceMethod] = None,
    inference_confidence: Optional[float] = None,
    source_checksum: Optional[str] = None
) -> ProvenanceInfo:
    """Helper to create provenance information."""
    return ProvenanceInfo(
        derived_from=derived_from or [],
        inferred_by=inferred_by,
        inference_method=inference_method,
        inference_confidence=inference_confidence,
        source_checksum=source_checksum
    )


def update_provenance_for_summary(
    source_memories: List[Union[StructuredMemory, EpisodicMemory, BehavioralMemory]],
    summary_memory: Union[StructuredMemory, EpisodicMemory, BehavioralMemory],
    summarization_method: str,
    summarization_confidence: float
) -> MemoryLineage:
    """
    Create provenance lineage for a summarized memory.
    
    Returns:
        MemoryLineage tracking the summarization
    """
    # Update summary memory's provenance
    summary_memory.provenance = ProvenanceInfo(
        derived_from=[m.memory_id for m in source_memories],
        inferred_by="summarizer",
        inference_method=InferenceMethod.PATTERN_DETECTION,
        inference_confidence=summarization_confidence
    )
    
    # Create lineage record
    lineage = MemoryLineage(
        summary_memory_id=summary_memory.memory_id,
        source_memory_ids=[m.memory_id for m in source_memories],
        summarization_method=summarization_method,
        summarization_confidence=summarization_confidence
    )
    
    return lineage


def preserve_provenance_on_update(
    original_memory: Union[StructuredMemory, EpisodicMemory, BehavioralMemory],
    updated_memory: Union[StructuredMemory, EpisodicMemory, BehavioralMemory]
) -> None:
    """Preserve provenance when updating a memory."""
    # Copy original provenance
    updated_memory.provenance = original_memory.provenance
    
    # Add update to transformation history
    updated_memory.provenance.transformation_history.append({
        "timestamp": datetime.now().isoformat(),
        "operation": "update",
        "original_value_hash": _hash_value(original_memory),
        "new_value_hash": _hash_value(updated_memory),
        "changed_fields": _get_changed_fields(original_memory, updated_memory)
    })


def _hash_value(memory: any) -> str:
    """Create hash of memory value."""
    import hashlib
    import json
    
    try:
        # Exclude provenance from hash to avoid circular issues
        memory_dict = memory.dict(exclude={"provenance"})
        memory_str = json.dumps(memory_dict, sort_keys=True)
        return hashlib.sha256(memory_str.encode()).hexdigest()
    except (TypeError, ValueError):
        return str(memory)


def _get_changed_fields(original: any, updated: any) -> List[str]:
    """Get list of changed fields between two memory objects."""
    changed = []
    
    original_dict = original.dict(exclude={"provenance", "updated_at"})
    updated_dict = updated.dict(exclude={"provenance", "updated_at"})
    
    for key in original_dict:
        if key in updated_dict and original_dict[key] != updated_dict[key]:
            changed.append(key)
    
    return changed