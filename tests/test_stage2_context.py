"""
Stage-2 Context Engine Tests (Forbidden Behavior Assertions)

These tests assert that FORBIDDEN behaviors are actually forbidden.
They pass only when the system correctly rejects violations.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from hestia.context_engine import ContextEngine, Pipeline, PipelineStep
from mnemosyne.service import MnemosyneService
from mnemosyne.service_config import MnemosyneConfig


class TestContextEngineForbiddenBehaviors:
    """Assert that Context Engine enforces all constraints."""

    @pytest.fixture
    def context(self):
        """Fresh context engine."""
        return ContextEngine()

    @pytest.fixture
    def memory_service(self, tmp_path):
        """Memory service for isolation tests."""
        config = MnemosyneConfig(enabled=True, db_path=Path(tmp_path) / "test.db")
        return MnemosyneService(config=config)

    # FORBIDDEN: Context cannot write to Mnemosyne
    def test_context_cannot_write_to_mnemosyne(self, context, memory_service):
        """Context MUST NOT be able to write to Mnemosyne."""
        # Context should have NO write method to mnemosyne
        assert not hasattr(context, 'write_to_memory')
        assert not hasattr(context, 'save_to_memory')
        assert not hasattr(context, 'persist')

    # FORBIDDEN: Mnemosyne cannot read from Context
    def test_mnemosyne_cannot_read_from_context(self, context, memory_service):
        """Mnemosyne MUST NOT be able to read from Context."""
        # Memory service should not have context access
        assert not hasattr(memory_service, 'read_from_context')
        assert not hasattr(memory_service, 'context')
        assert not hasattr(memory_service, 'get_context')

    # FORBIDDEN: Sliding expiration
    def test_no_sliding_expiration(self, context):
        """TTL MUST NOT extend on access."""
        context.append("test entry")
        ttl_remaining_1 = context.ttl_seconds_remaining()

        # Access context (read)
        _ = context.snapshot()
        ttl_remaining_2 = context.ttl_seconds_remaining()

        # TTL should NOT have extended (or only by negligible time)
        assert abs(ttl_remaining_1 - ttl_remaining_2) < 1, "TTL extended on read (sliding forbidden)"

    # FORBIDDEN: Auto-extension
    def test_no_auto_extension(self, context):
        """TTL MUST NOT auto-extend beyond max."""
        # Create context with max TTL
        context.set_ttl(1800)  # Max allowed
        max_ttl = context.ttl_seconds_remaining()

        # Try to extend beyond max (if such method existed, it would fail)
        # The fact that this method should NOT exist is the test
        assert not hasattr(context, 'extend_ttl'), "extend_ttl should not exist"

    # FORBIDDEN: Max depth > 3
    def test_pipeline_max_depth_3(self, context):
        """Pipelines MUST fail if depth > 3."""
        pipeline_str = """
PIPELINE:
  - Athena.query("test")
  - Hephaestus.explain(level="advanced")
  - Hermes.rewrite(style="brief")
  - Apollo.analyze(factor="health")
END
"""
        with pytest.raises(ValueError, match="max.*3|depth.*3"):
            context.parse_pipeline(pipeline_str)

    # FORBIDDEN: Duplicate domains
    def test_pipeline_no_duplicate_domains(self, context):
        """Pipelines MUST fail if domain appears twice."""
        pipeline_str = """
PIPELINE:
  - Athena.query("test")
  - Hermes.rewrite(style="brief")
  - Athena.query("test2")
END
"""
        with pytest.raises(ValueError, match="duplicate|Duplicate"):
            context.parse_pipeline(pipeline_str)

    # FORBIDDEN: Conditionals in pipeline
    def test_pipeline_no_conditionals(self, context):
        """Pipelines MUST reject if/then/else."""
        pipeline_str = """
PIPELINE:
  - Athena.query("test")
  - if result.length > 100:
  -   Hermes.summarize()
END
"""
        with pytest.raises(ValueError, match="invalid|conditional|if"):
            context.parse_pipeline(pipeline_str)

    # FORBIDDEN: Loops in pipeline
    def test_pipeline_no_loops(self, context):
        """Pipelines MUST reject loops."""
        pipeline_str = """
PIPELINE:
  - for i in range(3):
  -   Athena.query(f"test {i}")
END
"""
        with pytest.raises(ValueError, match="invalid|loop|for"):
            context.parse_pipeline(pipeline_str)

    # FORBIDDEN: Inference/guessing
    def test_pipeline_no_inference_without_explicit_syntax(self, context):
        """Pipeline MUST NOT infer from plain user text."""
        # Plain text that LOOKS like it could be a pipeline, but no PIPELINE: syntax
        plain_text = "Athena should query energy policy, then Hermes summarizes"

        # Should NOT parse as pipeline
        pipeline = context.parse_pipeline(plain_text)
        assert pipeline is None, "Plain text should not be inferred as pipeline"

    # FORBIDDEN: Overflow accepts
    def test_context_overflow_rejects_append(self, context):
        """Context MUST reject append when full, not truncate/accept."""
        # Fill context to max entries (20)
        for i in range(20):
            context.append(f"entry_{i}")

        # Try to append 21st
        with pytest.raises(ValueError, match="overflow|full|max.*entries"):
            context.append("entry_20")

        # Verify context unchanged
        assert context.entry_count() == 20, "Overflow should not modify context"

    # FORBIDDEN: Token overflow accepts
    def test_context_token_overflow_rejects_append(self, context):
        """Context MUST reject append when tokens exceed limit."""
        # Fill context with large entries up to token limit
        # Max per entry is 512 tokens = ~2048 chars
        # Fill 8 entries of max size = ~4096 tokens
        for i in range(8):
            context.append("x" * 2048)  # ~512 tokens each

        total = context.token_count()
        assert total >= 4000, f"Expected >= 4000 tokens, got {total}"

        # Try to append any more - should exceed
        with pytest.raises(ValueError, match="token|overflow|full"):
            context.append("y" * 100)  # Even 100 chars would exceed

    # FORBIDDEN: Context carries across sessions
    def test_context_destroyed_on_process_restart(self, context):
        """Context MUST be volatile (RAM-only), destroyed on restart."""
        # This is a logical assertion - can't actually restart process in test
        # But we can verify no persistence layer exists
        assert not hasattr(context, 'save_to_disk')
        assert not hasattr(context, 'load_from_disk')
        assert not hasattr(context, 'persist')

    # FORBIDDEN: Domains have implicit read access
    def test_domains_receive_read_only_snapshots(self, context):
        """Domains MUST receive read-only snapshots, not live context."""
        context.append("entry1")
        snapshot = context.snapshot()

        # Snapshot should be immutable (tuple, frozen dict, or similar)
        assert hasattr(snapshot, '__hash__') or isinstance(snapshot, (tuple, frozenset)), \
            "Snapshot must be read-only"

    # REQUIRED: Explicit context metadata inspection
    def test_context_metadata_inspection(self, context):
        """User MUST be able to inspect context metadata."""
        context.append("test")

        # Get metadata
        metadata = context.inspect()

        # Must include these keys
        assert 'entry_count' in metadata
        assert 'ttl_remaining_seconds' in metadata
        assert 'state' in metadata  # ACTIVE / EXPIRED
        assert 'contributors' in metadata  # Domains that contributed

    # REQUIRED: Explicit clear command
    def test_context_explicit_clear(self, context):
        """Context MUST support explicit clear()."""
        context.append("entry1")
        context.append("entry2")

        assert context.entry_count() == 2

        context.clear()

        assert context.entry_count() == 0
        assert context.state == "CLEARED"

    # REQUIRED: TTL enforcement
    def test_context_expiration_hard_limit(self, context):
        """Context MUST expire when TTL exceeded."""
        context.set_ttl(900)  # 15 minutes

        context.append("test")
        assert context.state == "ACTIVE"

        # Simulate TTL passage (by directly modifying for test)
        context._created_at = datetime.now() - timedelta(seconds=901)

        # Accessing should trigger expiration
        _ = context.snapshot()
        assert context.state == "EXPIRED"

    # REQUIRED: Max TTL limit
    def test_context_max_ttl_limit(self, context):
        """Context MUST reject TTL > 1800 seconds."""
        with pytest.raises(ValueError, match="max.*1800|exceed"):
            context.set_ttl(1801)

    # REQUIRED: Pipeline parsing strict syntax
    def test_pipeline_requires_exact_syntax(self, context):
        """Pipeline MUST use exact PIPELINE: ... END syntax."""
        # Missing END
        with pytest.raises(ValueError, match="END|syntax|malformed"):
            context.parse_pipeline("PIPELINE:\n  - Athena.query('test')")

        # Missing PIPELINE:
        with pytest.raises(ValueError, match="PIPELINE|syntax|malformed"):
            context.parse_pipeline("  - Athena.query('test')\nEND")

        # Typo in PIPELINE:
        with pytest.raises(ValueError, match="PIPELINE|syntax|malformed"):
            context.parse_pipeline("PIPLINE:\n  - Athena.query('test')\nEND")
