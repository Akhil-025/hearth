"""
Memory Consistency Checker - Detects conflicting structured memories.

Flags contradictions instead of overwriting.
Generates review tasks for Hestia.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ..shared.logging.structured_logger import StructuredLogger
from ..shared.schemas.memory import MemoryType, StructuredMemory


class ContradictionType(Enum):
    """Types of contradictions."""
    DIRECT_CONFLICT = "direct_conflict"      # Same key, different values
    LOGICAL_CONFLICT = "logical_conflict"    # Values imply contradiction
    TEMPORAL_CONFLICT = "temporal_conflict"  # Time-based contradiction
    CATEGORY_CONFLICT = "category_conflict"  # Same item in different categories
    CONFIDENCE_CONFLICT = "confidence_conflict" # High confidence conflicts


class ContradictionSeverity(Enum):
    """Contradiction severity levels."""
    INFO = "info"           # Minor inconsistency, likely intentional
    WARNING = "warning"     # Significant inconsistency
    CRITICAL = "critical"   # Critical contradiction requiring resolution
    BLOCKING = "blocking"   # Contradiction that blocks operations


class ContradictionDetection(BaseModel):
    """Detection of a specific contradiction."""
    detection_id: UUID = Field(default_factory=uuid4)
    contradiction_type: ContradictionType
    severity: ContradictionSeverity
    
    # Conflicting memories
    memory_ids: List[UUID]
    category: str
    key: str
    
    # Details
    conflicting_values: List[any]
    confidence_scores: List[float]
    detection_method: str
    detection_confidence: float = Field(ge=0.0, le=1.0)
    
    # Resolution
    auto_resolvable: bool = False
    resolution_suggestions: List[str] = Field(default_factory=list)
    requires_human_review: bool = True
    
    # Metadata
    detected_at: datetime = Field(default_factory=datetime.now)
    last_checked: datetime = Field(default_factory=datetime.now)
    check_count: int = 1
    
    class Config:
        use_enum_values = True


class ResolutionProposal(BaseModel):
    """Proposal for resolving a contradiction."""
    proposal_id: UUID = Field(default_factory=uuid4)
    detection_id: UUID
    proposed_action: str
    justification: str
    expected_outcome: str
    
    # Impact assessment
    confidence_impact: float = Field(ge=0.0, le=1.0, default=0.0)
    memory_preservation: float = Field(ge=0.0, le=1.0, default=1.0)
    requires_approval: bool = True
    
    # Metadata
    generated_by: str = "consistency_checker"
    generated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class ConsistencyChecker:
    """
    Detects conflicting structured memories.
    
    Compares keys, categories, confidence.
    Flags conflicts instead of overwriting.
    Generates review tasks for Hestia.
    """
    
    def __init__(self, config: Optional[Dict[str, any]] = None):
        self.config = config or {}
        self.logger = StructuredLogger(__name__)
        
        # Contradiction storage
        self.detections: Dict[UUID, ContradictionDetection] = {}
        self.resolution_proposals: Dict[UUID, List[ResolutionProposal]] = {}
        
        # Detection rules
        self.detection_rules = self._initialize_detection_rules()
        
        # Statistics
        self.stats = {
            "total_checks": 0,
            "contradictions_found": 0,
            "auto_resolved": 0,
            "pending_review": 0
        }
        
        self.logger.info("Consistency checker initialized")
    
    def _initialize_detection_rules(self) -> Dict[ContradictionType, Dict[str, any]]:
        """Initialize contradiction detection rules."""
        return {
            ContradictionType.DIRECT_CONFLICT: {
                "description": "Same key has different values",
                "severity": ContradictionSeverity.CRITICAL,
                "confidence_threshold": 0.7,
                "auto_resolve": False
            },
            ContradictionType.LOGICAL_CONFLICT: {
                "description": "Values imply logical contradiction",
                "severity": ContradictionSeverity.WARNING,
                "confidence_threshold": 0.8,
                "auto_resolve": False
            },
            ContradictionType.TEMPORAL_CONFLICT: {
                "description": "Time-based contradiction",
                "severity": ContradictionSeverity.INFO,
                "confidence_threshold": 0.6,
                "auto_resolve": True
            },
            ContradictionType.CATEGORY_CONFLICT: {
                "description": "Same item in different categories",
                "severity": ContradictionSeverity.WARNING,
                "confidence_threshold": 0.7,
                "auto_resolve": False
            },
            ContradictionType.CONFIDENCE_CONFLICT: {
                "description": "High confidence conflicts",
                "severity": ContradictionSeverity.BLOCKING,
                "confidence_threshold": 0.9,
                "auto_resolve": False
            }
        }
    
    def check_memory_consistency(
        self,
        memories: List[StructuredMemory],
        check_types: Optional[List[ContradictionType]] = None
    ) -> List[ContradictionDetection]:
        """
        Check consistency among a set of memories.
        
        Args:
            memories: Memories to check
            check_types: Specific contradiction types to check
        
        Returns:
            List of contradiction detections
        """
        self.stats["total_checks"] += 1
        
        if not memories or len(memories) < 2:
            return []
        
        # Group memories by category and key
        memory_groups = self._group_memories(memories)
        
        # Check each group for contradictions
        detections = []
        
        for (category, key), group_memories in memory_groups.items():
            if len(group_memories) > 1:
                # Check for contradictions within group
                group_detections = self._check_memory_group(
                    category=category,
                    key=key,
                    memories=group_memories,
                    check_types=check_types
                )
                detections.extend(group_detections)
        
        # Update statistics
        new_detections = len(detections)
        self.stats["contradictions_found"] += new_detections
        
        if new_detections > 0:
            self.logger.info(
                "Contradictions detected",
                count=new_detections,
                categories=len(set(d.category for d in detections))
            )
        
        return detections
    
    def _group_memories(
        self,
        memories: List[StructuredMemory]
    ) -> Dict[Tuple[str, str], List[StructuredMemory]]:
        """Group memories by category and key."""
        groups = {}
        
        for memory in memories:
            if memory.memory_type != MemoryType.STRUCTURED:
                continue
            
            group_key = (memory.category, memory.key)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(memory)
        
        return groups
    
    def _check_memory_group(
        self,
        category: str,
        key: str,
        memories: List[StructuredMemory],
        check_types: Optional[List[ContradictionType]] = None
    ) -> List[ContradictionDetection]:
        """Check a group of memories for contradictions."""
        detections = []
        
        # Get check types
        types_to_check = check_types or list(self.detection_rules.keys())
        
        for check_type in types_to_check:
            detection = self._check_for_contradiction_type(
                check_type=check_type,
                category=category,
                key=key,
                memories=memories
            )
            
            if detection:
                detections.append(detection)
        
        return detections
    
    def _check_for_contradiction_type(
        self,
        check_type: ContradictionType,
        category: str,
        key: str,
        memories: List[StructuredMemory]
    ) -> Optional[ContradictionDetection]:
        """Check for a specific type of contradiction."""
        check_method = getattr(self, f"_check_{check_type.value}", None)
        
        if not check_method:
            self.logger.warning(
                "No check method for contradiction type",
                check_type=check_type.value
            )
            return None
        
        result = check_method(memories)
        
        if result["detected"]:
            rule_config = self.detection_rules[check_type]
            
            # Check if meets confidence threshold
            if result["confidence"] >= rule_config["confidence_threshold"]:
                return self._create_detection(
                    contradiction_type=check_type,
                    severity=rule_config["severity"],
                    category=category,
                    key=key,
                    memories=memories,
                    detection_details=result
                )
        
        return None
    
    def _check_direct_conflict(self, memories: List[StructuredMemory]) -> Dict[str, any]:
        """Check for direct value conflicts."""
        unique_values = {}
        confidence_sum = 0.0
        
        for memory in memories:
            value_hash = self._hash_value(memory.value)
            if value_hash not in unique_values:
                unique_values[value_hash] = {
                    "value": memory.value,
                    "memory_ids": [],
                    "confidence_sum": 0.0
                }
            
            unique_values[value_hash]["memory_ids"].append(memory.memory_id)
            unique_values[value_hash]["confidence_sum"] += memory.confidence
            confidence_sum += memory.confidence
        
        if len(unique_values) > 1:
            # Calculate detection confidence based on confidence differences
            confidence_values = [v["confidence_sum"] for v in unique_values.values()]
            max_confidence = max(confidence_values)
            total_confidence = sum(confidence_values)
            
            detection_confidence = (max_confidence / total_confidence) if total_confidence > 0 else 0.5
            
            return {
                "detected": True,
                "confidence": detection_confidence,
                "unique_value_count": len(unique_values),
                "conflicting_values": [v["value"] for v in unique_values.values()],
                "memory_groups": {h: v["memory_ids"] for h, v in unique_values.items()}
            }
        
        return {"detected": False}
    
    def _check_logical_conflict(self, memories: List[StructuredMemory]) -> Dict[str, any]:
        """Check for logical contradictions."""
        # This is a simplified implementation
        # In production, this would use more sophisticated logic checking
        
        values = [memory.value for memory in memories]
        
        # Check for boolean contradictions
        if all(isinstance(v, bool) for v in values):
            if True in values and False in values:
                true_count = sum(1 for v in values if v)
                false_count = len(values) - true_count
                confidence = max(true_count, false_count) / len(values)
                
                return {
                    "detected": True,
                    "confidence": confidence,
                    "conflict_type": "boolean_contradiction"
                }
        
        # Check for numeric range contradictions
        if all(isinstance(v, (int, float)) for v in values):
            min_val = min(values)
            max_val = max(values)
            
            if max_val - min_val > 10:  # Arbitrary threshold
                # Calculate confidence based on spread
                spread = max_val - min_val
                avg = sum(values) / len(values)
                confidence = min(1.0, spread / (avg + 1))
                
                return {
                    "detected": True,
                    "confidence": confidence,
                    "conflict_type": "numeric_range",
                    "range": (min_val, max_val)
                }
        
        return {"detected": False}
    
    def _check_temporal_conflict(self, memories: List[StructuredMemory]) -> Dict[str, any]:
        """Check for temporal contradictions."""
        # Check creation times vs values
        if len(memories) < 2:
            return {"detected": False}
        
        # Sort by creation time
        sorted_memories = sorted(memories, key=lambda m: m.created_at)
        
        # Check if newer memories contradict older ones
        contradictions = []
        
        for i in range(1, len(sorted_memories)):
            current = sorted_memories[i]
            previous = sorted_memories[i - 1]
            
            if self._values_conflict(current.value, previous.value):
                contradictions.append((previous.memory_id, current.memory_id))
        
        if contradictions:
            # Confidence based on recency and confidence
            newest_memory = sorted_memories[-1]
            confidence = newest_memory.confidence
            
            return {
                "detected": True,
                "confidence": confidence,
                "contradiction_count": len(contradictions),
                "contradiction_pairs": contradictions
            }
        
        return {"detected": False}
    
    def _check_category_conflict(self, memories: List[StructuredMemory]) -> Dict[str, any]:
        """Check for category assignment conflicts."""
        # Actually, memories in the same group already have same category
        # This check would need memories from different categories with same semantic meaning
        # Simplified for now
        
        return {"detected": False}
    
    def _check_confidence_conflict(self, memories: List[StructuredMemory]) -> Dict[str, any]:
        """Check for high-confidence conflicts."""
        # Look for memories with high confidence but conflicting values
        high_confidence_memories = [
            m for m in memories 
            if m.confidence >= 0.8
        ]
        
        if len(high_confidence_memories) >= 2:
            # Check if high confidence memories conflict
            values = [m.value for m in high_confidence_memories]
            if len(set(self._hash_value(v) for v in values)) > 1:
                # Calculate average confidence of conflicting memories
                avg_confidence = sum(m.confidence for m in high_confidence_memories) / len(high_confidence_memories)
                
                return {
                    "detected": True,
                    "confidence": avg_confidence,
                    "high_confidence_count": len(high_confidence_memories),
                    "conflict_type": "high_confidence_direct"
                }
        
        return {"detected": False}
    
    def _hash_value(self, value: any) -> str:
        """Create hash of a value for comparison."""
        import json
        import hashlib
        
        try:
            value_str = json.dumps(value, sort_keys=True)
            return hashlib.sha256(value_str.encode()).hexdigest()
        except (TypeError, ValueError):
            return str(value)
    
    def _values_conflict(self, value1: any, value2: any) -> bool:
        """Check if two values conflict."""
        if value1 == value2:
            return False
        
        # Type mismatch is a conflict
        if type(value1) != type(value2):
            return True
        
        # For booleans, True vs False is a conflict
        if isinstance(value1, bool) and isinstance(value2, bool):
            return value1 != value2
        
        # For numbers, significant difference might be a conflict
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            # 10% difference threshold
            if value1 == 0 or value2 == 0:
                return abs(value1 - value2) > 0.1
            return abs(value1 - value2) / max(abs(value1), abs(value2)) > 0.1
        
        # For strings, check if they're significantly different
        if isinstance(value1, str) and isinstance(value2, str):
            # Simple Levenshtein distance threshold
            distance = self._levenshtein_distance(value1, value2)
            max_len = max(len(value1), len(value2))
            return distance / max_len > 0.3
        
        # Default: different values are considered conflicting
        return True
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _create_detection(
        self,
        contradiction_type: ContradictionType,
        severity: ContradictionSeverity,
        category: str,
        key: str,
        memories: List[StructuredMemory],
        detection_details: Dict[str, any]
    ) -> ContradictionDetection:
        """Create a contradiction detection."""
        rule_config = self.detection_rules[contradiction_type]
        
        detection = ContradictionDetection(
            contradiction_type=contradiction_type,
            severity=severity,
            memory_ids=[m.memory_id for m in memories],
            category=category,
            key=key,
            conflicting_values=detection_details.get("conflicting_values", []),
            confidence_scores=[m.confidence for m in memories],
            detection_method=contradiction_type.value,
            detection_confidence=detection_details.get("confidence", 0.5),
            auto_resolvable=rule_config.get("auto_resolve", False),
            requires_human_review=not rule_config.get("auto_resolve", False)
        )
        
        # Generate resolution suggestions
        detection.resolution_suggestions = self._generate_resolution_suggestions(
            detection, memories
        )
        
        # Store detection
        self.detections[detection.detection_id] = detection
        
        # Generate proposals if auto-resolvable
        if detection.auto_resolvable:
            self._generate_resolution_proposals(detection, memories)
            self.stats["auto_resolved"] += 1
        else:
            self.stats["pending_review"] += 1
        
        return detection
    
    def _generate_resolution_suggestions(
        self,
        detection: ContradictionDetection,
        memories: List[StructuredMemory]
    ) -> List[str]:
        """Generate suggestions for resolving the contradiction."""
        suggestions = []
        
        if detection.contradiction_type == ContradictionType.DIRECT_CONFLICT:
            # Find highest confidence memory
            highest_conf_memory = max(memories, key=lambda m: m.confidence)
            
            suggestions.append(
                f"Use value from highest confidence memory (confidence: {highest_conf_memory.confidence:.2f})"
            )
            suggestions.append(
                "Request user clarification on correct value"
            )
            suggestions.append(
                "Archive older memories and keep most recent"
            )
        
        elif detection.contradiction_type == ContradictionType.TEMPORAL_CONFLICT:
            suggestions.append(
                "Keep most recent value as current state"
            )
            suggestions.append(
                "Document value changes over time"
            )
        
        elif detection.contradiction_type == ContradictionType.CONFIDENCE_CONFLICT:
            suggestions.append(
                "Flag for urgent review due to high-confidence conflict"
            )
            suggestions.append(
                "Temporarily disable affected memories until resolved"
            )
        
        return suggestions
    
    def _generate_resolution_proposals(
        self,
        detection: ContradictionDetection,
        memories: List[StructuredMemory]
    ) -> List[ResolutionProposal]:
        """Generate resolution proposals for auto-resolvable contradictions."""
        proposals = []
        
        if detection.contradiction_type == ContradictionType.TEMPORAL_CONFLICT:
            # Propose keeping most recent
            most_recent = max(memories, key=lambda m: m.created_at)
            
            proposal = ResolutionProposal(
                detection_id=detection.detection_id,
                proposed_action="keep_most_recent",
                justification=f"Memory {most_recent.memory_id} is most recent ({most_recent.created_at})",
                expected_outcome="Use most recent value, archive others",
                confidence_impact=most_recent.confidence,
                memory_preservation=0.5  # Some memories will be archived
            )
            proposals.append(proposal)
        
        # Store proposals
        self.resolution_proposals[detection.detection_id] = proposals
        
        return proposals
    
    def get_detection(self, detection_id: UUID) -> Optional[ContradictionDetection]:
        """Get a specific contradiction detection."""
        detection = self.detections.get(detection_id)
        
        if detection:
            # Update last checked
            detection.last_checked = datetime.now()
            detection.check_count += 1
        
        return detection
    
    def get_detections(
        self,
        category: Optional[str] = None,
        severity: Optional[ContradictionSeverity] = None,
        unresolved_only: bool = False
    ) -> List[ContradictionDetection]:
        """Get contradiction detections with filtering."""
        detections = list(self.detections.values())
        
        # Apply filters
        if category:
            detections = [d for d in detections if d.category == category]
        
        if severity:
            detections = [d for d in detections if d.severity == severity]
        
        if unresolved_only:
            detections = [d for d in detections if d.requires_human_review]
        
        # Sort by detection confidence (highest first)
        detections.sort(key=lambda d: d.detection_confidence, reverse=True)
        
        return detections
    
    def mark_resolved(
        self,
        detection_id: UUID,
        resolution_method: str,
        resolution_notes: str
    ) -> bool:
        """Mark a contradiction as resolved."""
        if detection_id not in self.detections:
            return False
        
        # Remove from detections (considered resolved)
        del self.detections[detection_id]
        
        # Update statistics
        self.stats["pending_review"] = max(0, self.stats["pending_review"] - 1)
        
        self.logger.info(
            "Contradiction marked as resolved",
            detection_id=str(detection_id)[:8],
            resolution_method=resolution_method
        )
        
        return True
    
    def get_statistics(self) -> Dict[str, any]:
        """Get consistency checker statistics."""
        # Calculate severity distribution
        severity_dist = {}
        for detection in self.detections.values():
            severity = detection.severity.value
            severity_dist[severity] = severity_dist.get(severity, 0) + 1
        
        # Calculate type distribution
        type_dist = {}
        for detection in self.detections.values():
            ctype = detection.contradiction_type.value
            type_dist[ctype] = type_dist.get(ctype, 0) + 1
        
        return {
            **self.stats,
            "active_detections": len(self.detections),
            "severity_distribution": severity_dist,
            "type_distribution": type_dist,
            "avg_detection_confidence": (
                sum(d.detection_confidence for d in self.detections.values()) / 
                max(len(self.detections), 1)
            ) if self.detections else 0.0
        }