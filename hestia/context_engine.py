"""
Stage-2 Context Engine v1

RAM-only, volatile, deterministic context for cross-domain pipelines.
- TTL: 900-1800 seconds
- Size: 1 context per process, max 20 entries, 4096 tokens total
- No persistence, no sliding expiration, fail-closed on errors
- Domains receive read-only snapshots only
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ContextState(str, Enum):
    """Context lifecycle states."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CLEARED = "CLEARED"
    DESTROYED = "DESTROYED"


@dataclass(frozen=True)
class PipelineStep:
    """Single step in a pipeline."""
    domain_id: str      # e.g., "athena", "hermes", "hephaestus"
    method: str         # e.g., "query", "rewrite", "explain"
    args: Dict[str, Any]  # Arguments to method

    def validate(self) -> bool:
        """Validate step syntax."""
        if not self.domain_id or not isinstance(self.domain_id, str):
            raise ValueError("domain_id must be non-empty string")
        if not self.method or not isinstance(self.method, str):
            raise ValueError("method must be non-empty string")
        if not isinstance(self.args, dict):
            raise ValueError("args must be dict")
        return True


@dataclass(frozen=True)
class Pipeline:
    """Immutable pipeline definition."""
    steps: Tuple[PipelineStep, ...]

    def validate(self) -> bool:
        """Validate entire pipeline."""
        # Max 3 steps
        if len(self.steps) > 3:
            raise ValueError(f"Pipeline max depth is 3, got {len(self.steps)}")

        # No duplicate domains
        domains = [step.domain_id for step in self.steps]
        if len(domains) != len(set(domains)):
            raise ValueError(f"Duplicate domain in pipeline")

        # All steps valid
        for i, step in enumerate(self.steps):
            try:
                step.validate()
            except ValueError as e:
                raise ValueError(f"Step {i}: {e}")

        return True


@dataclass(frozen=True)
class ContextEntry:
    """Single entry in context (immutable)."""
    content: str
    source_domain: str
    timestamp: str  # ISO format
    tokens: int     # Estimated token count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return asdict(self)


class ContextEngine:
    """
    Stage-2 Context Engine v1: RAM-only, volatile, deterministic.

    - Single context per process (class variable)
    - TTL: 900-1800 seconds (no sliding, no auto-extend)
    - Sizes: max 20 entries, 4096 total tokens, 512 per entry
    - Fail-closed: overflow rejects, expiration destroys
    - No persistence, no implicit writes
    """

    _instance: Optional['ContextEngine'] = None  # Singleton

    # Hard constants
    DEFAULT_TTL_SECONDS = 900      # 15 minutes
    MAX_TTL_SECONDS = 1800         # 30 minutes
    MAX_ENTRIES = 20
    MAX_TOTAL_TOKENS = 4096
    MAX_ENTRY_TOKENS = 512

    def __init__(self):
        """Initialize context engine."""
        self._entries: List[ContextEntry] = []
        self._created_at: datetime = datetime.now()
        self._ttl_seconds: int = self.DEFAULT_TTL_SECONDS
        self._state: ContextState = ContextState.ACTIVE

        logger.info(json.dumps({
            "event": "context_created",
            "timestamp": self._created_at.isoformat(),
            "ttl_seconds": self._ttl_seconds,
        }))

    @classmethod
    def get_instance(cls) -> 'ContextEngine':
        """Get or create singleton context."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Destroy singleton (for testing)."""
        if cls._instance is not None:
            cls._instance._state = ContextState.DESTROYED
            cls._instance = None

    # ========== TTL & Expiration ==========

    def set_ttl(self, seconds: int) -> None:
        """Set TTL (no extension allowed)."""
        if self._state != ContextState.ACTIVE:
            raise ValueError(f"Cannot set TTL on {self._state} context")

        if seconds < 1 or seconds > self.MAX_TTL_SECONDS:
            raise ValueError(f"TTL must not exceed {self.MAX_TTL_SECONDS} seconds")

        self._ttl_seconds = seconds
        logger.info(json.dumps({
            "event": "context_ttl_set",
            "ttl_seconds": seconds,
        }))

    def ttl_seconds_remaining(self) -> float:
        """Get remaining TTL in seconds."""
        self._check_expiration()
        if self._state != ContextState.ACTIVE:
            return 0.0

        elapsed = (datetime.now() - self._created_at).total_seconds()
        remaining = self._ttl_seconds - elapsed
        return max(0.0, remaining)

    def _check_expiration(self) -> None:
        """Check if context has expired. If so, destroy it (fail-closed)."""
        if self._state != ContextState.ACTIVE:
            return

        elapsed = (datetime.now() - self._created_at).total_seconds()
        if elapsed > self._ttl_seconds:
            self._state = ContextState.EXPIRED
            logger.info(json.dumps({
                "event": "context_expired",
                "elapsed_seconds": elapsed,
                "ttl_seconds": self._ttl_seconds,
                "entry_count": len(self._entries),
            }))

    # ========== Entry Management ==========

    def append(self, content: str, source_domain: str = "user") -> None:
        """
        Append entry to context.

        Rejects if:
        - Context is not ACTIVE
        - Max entries exceeded
        - Max tokens exceeded (total or per-entry)
        - Content is empty
        """
        self._check_expiration()

        if self._state != ContextState.ACTIVE:
            raise ValueError(f"Cannot append to {self._state} context")

        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        # Estimate tokens (rough: 1 token per 4 characters)
        entry_tokens = max(1, len(content) // 4)

        if entry_tokens > self.MAX_ENTRY_TOKENS:
            raise ValueError(f"Entry exceeds max {self.MAX_ENTRY_TOKENS} tokens")

        if len(self._entries) >= self.MAX_ENTRIES:
            logger.error(json.dumps({
                "event": "context_append_rejected",
                "reason": "max_entries_exceeded",
                "max_entries": self.MAX_ENTRIES,
                "current_entries": len(self._entries),
            }))
            raise ValueError(f"Context full: max {self.MAX_ENTRIES} entries")

        total_tokens = self._total_tokens() + entry_tokens
        if total_tokens > self.MAX_TOTAL_TOKENS:
            logger.error(json.dumps({
                "event": "context_append_rejected",
                "reason": "token_overflow",
                "max_tokens": self.MAX_TOTAL_TOKENS,
                "requested_total": total_tokens,
            }))
            raise ValueError(f"Context full: max {self.MAX_TOTAL_TOKENS} tokens")

        # Create entry
        entry = ContextEntry(
            content=content,
            source_domain=source_domain,
            timestamp=datetime.now().isoformat(),
            tokens=entry_tokens,
        )

        self._entries.append(entry)

        logger.info(json.dumps({
            "event": "context_append_attempt",
            "success": True,
            "source_domain": source_domain,
            "entry_tokens": entry_tokens,
            "total_tokens": total_tokens,
            "entry_count": len(self._entries),
        }))

    def _total_tokens(self) -> int:
        """Get total token count."""
        return sum(e.tokens for e in self._entries)

    def entry_count(self) -> int:
        """Get number of entries."""
        self._check_expiration()
        return len(self._entries) if self._state == ContextState.ACTIVE else 0

    def token_count(self) -> int:
        """Get total token count."""
        self._check_expiration()
        return self._total_tokens() if self._state == ContextState.ACTIVE else 0

    # ========== Snapshots (Read-Only) ==========

    def snapshot(self) -> Tuple[ContextEntry, ...]:
        """
        Get read-only snapshot of context entries.

        Returns immutable tuple. Domains receive snapshots, never live access.
        """
        self._check_expiration()

        if self._state != ContextState.ACTIVE:
            logger.info(json.dumps({
                "event": "context_snapshot_issued",
                "state": self._state,
                "entry_count": 0,
            }))
            return tuple()

        logger.info(json.dumps({
            "event": "context_snapshot_issued",
            "state": self._state,
            "entry_count": len(self._entries),
            "total_tokens": self._total_tokens(),
        }))

        return tuple(self._entries)

    # ========== Inspection (User-Facing Metadata) ==========

    def inspect(self) -> Dict[str, Any]:
        """
        Inspect context metadata (no content shown).

        User may call 'show context' to get this.
        """
        self._check_expiration()

        contributors = set(e.source_domain for e in self._entries) if self._state == ContextState.ACTIVE else set()

        metadata = {
            "state": self._state.value,
            "entry_count": len(self._entries) if self._state == ContextState.ACTIVE else 0,
            "ttl_remaining_seconds": self.ttl_seconds_remaining(),
            "max_entries": self.MAX_ENTRIES,
            "max_tokens": self.MAX_TOTAL_TOKENS,
            "current_tokens": self._total_tokens() if self._state == ContextState.ACTIVE else 0,
            "contributors": sorted(list(contributors)),
            "created_at": self._created_at.isoformat(),
        }

        logger.info(json.dumps({
            "event": "context_inspected",
            **metadata,
        }))

        return metadata

    @property
    def state(self) -> str:
        """Get current state."""
        self._check_expiration()
        return self._state.value

    # ========== Clear ==========

    def clear(self) -> None:
        """Explicitly clear context."""
        self._entries.clear()
        self._state = ContextState.CLEARED

        logger.info(json.dumps({
            "event": "context_destroyed",
            "reason": "user_clear",
        }))

    # ========== Pipeline Parsing ==========

    def parse_pipeline(self, text: str) -> Optional[Pipeline]:
        """
        Parse pipeline from text.

        STRICT syntax: PIPELINE: ... END

        Rejects:
        - Missing PIPELINE: or END
        - Conditionals, loops, branching
        - Duplicates, depth > 3
        - Inference from plain text
        """
        if "PIPELINE:" not in text or "END" not in text:
            # Plain text, not a pipeline
            # But if they tried to write a pipeline syntax and failed, raise error
            if "PIPELINE" in text or "END" in text:
                # Partial attempt at pipeline syntax
                raise ValueError("Malformed pipeline: missing PIPELINE: or END marker")
            return None

        # Extract pipeline block
        try:
            start_idx = text.index("PIPELINE:")
            end_idx = text.index("END", start_idx)
            pipeline_block = text[start_idx:end_idx].strip()
        except ValueError:
            raise ValueError("Malformed pipeline: missing PIPELINE: or END")

        lines = pipeline_block.split("\n")
        if lines[0].strip() != "PIPELINE:":
            raise ValueError("Pipeline must start with 'PIPELINE:'")

        # Parse steps
        steps = []
        for i, line in enumerate(lines[1:], 1):
            line = line.strip()
            if not line or line == "END":
                continue

            # Check for forbidden constructs
            if line.startswith("if ") or " if " in line:
                raise ValueError(f"Line {i}: Invalid pipeline: if/conditional forbidden")
            if line.startswith("for ") or " for " in line:
                raise ValueError(f"Line {i}: Loops forbidden")
            if line.startswith("while "):
                raise ValueError(f"Line {i}: Loops forbidden")

            # Parse step: "- Domain.method(args)"
            if not line.startswith("- "):
                raise ValueError(f"Line {i}: Invalid step syntax (must start with '- ')")

            step_str = line[2:].strip()  # Remove "- "

            try:
                step = self._parse_step(step_str)
                steps.append(step)
            except ValueError as e:
                raise ValueError(f"Line {i}: {e}")

        if not steps:
            raise ValueError("Pipeline must have at least 1 step")

        pipeline = Pipeline(steps=tuple(steps))
        pipeline.validate()

        logger.info(json.dumps({
            "event": "pipeline_declared",
            "step_count": len(steps),
            "domains": [s.domain_id for s in steps],
        }))

        return pipeline

    def _parse_step(self, step_str: str) -> PipelineStep:
        """Parse single step: 'Domain.method(args)'"""
        if "." not in step_str or "(" not in step_str or ")" not in step_str:
            raise ValueError("Step must be 'domain.method(args)'")

        # Split domain.method
        domain_method = step_str.split("(")[0]
        if "." not in domain_method:
            raise ValueError("Step must be 'domain.method(args)'")

        domain_id, method = domain_method.split(".", 1)
        domain_id = domain_id.strip()
        method = method.strip()

        # Extract args (simple: key="value" or key=value)
        args_str = step_str.split("(", 1)[1].rsplit(")", 1)[0]
        args = self._parse_args(args_str)

        return PipelineStep(domain_id=domain_id, method=method, args=args)

    def _parse_args(self, args_str: str) -> Dict[str, Any]:
        """Parse args from 'key1="value1", key2="value2"'"""
        args = {}
        if not args_str.strip():
            return args

        # Simple CSV-like parsing for key="value" pairs
        for arg_pair in args_str.split(","):
            arg_pair = arg_pair.strip()
            if "=" not in arg_pair:
                continue

            key, val = arg_pair.split("=", 1)
            key = key.strip()
            val = val.strip()

            # Remove quotes if present
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]

            args[key] = val

        return args
