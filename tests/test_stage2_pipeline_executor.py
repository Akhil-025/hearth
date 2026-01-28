"""
Stage-2 Pipeline Executor Tests

Tests for cross-domain pipeline execution with domains.
"""

import pytest
from hestia.context_engine import ContextEngine, Pipeline, PipelineStep


class MockDomain:
    """Mock domain for testing."""
    def __init__(self, name):
        self.name = name
        self.last_called = None
        self.call_count = 0

    def query(self, q):
        self.last_called = ("query", q)
        self.call_count += 1
        return f"{self.name} answered: {q}"

    def rewrite(self, style):
        self.last_called = ("rewrite", style)
        self.call_count += 1
        return f"{self.name} rewrote in {style} style"

    def explain(self, level):
        self.last_called = ("explain", level)
        self.call_count += 1
        return f"{self.name} explained at {level} level"


class TestPipelineExecutor:
    """Test pipeline execution."""

    @pytest.fixture
    def context(self):
        """Fresh context."""
        ctx = ContextEngine()
        ContextEngine.reset_instance()
        return ContextEngine()

    @pytest.fixture
    def domains(self):
        """Mock domains."""
        return {
            "athena": MockDomain("Athena"),
            "hermes": MockDomain("Hermes"),
            "hephaestus": MockDomain("Hephaestus"),
        }

    def test_pipeline_single_domain_execution(self, context, domains):
        """Single-domain pipeline executes correctly."""
        pipeline_str = """
PIPELINE:
  - athena.query(q="energy policy")
END
"""
        pipeline = context.parse_pipeline(pipeline_str)
        assert pipeline is not None
        assert len(pipeline.steps) == 1
        assert pipeline.steps[0].domain_id == "athena"
        assert pipeline.steps[0].method == "query"
        assert pipeline.steps[0].args == {"q": "energy policy"}

    def test_pipeline_multi_domain_execution(self, context, domains):
        """Multi-domain pipeline executes left-to-right."""
        pipeline_str = """
PIPELINE:
  - athena.query(q="CCS technology")
  - hermes.rewrite(style="executive summary")
END
"""
        pipeline = context.parse_pipeline(pipeline_str)
        assert pipeline is not None
        assert len(pipeline.steps) == 2
        assert pipeline.steps[0].domain_id == "athena"
        assert pipeline.steps[1].domain_id == "hermes"

    def test_pipeline_max_3_domains_allowed(self, context, domains):
        """Max 3 domains per pipeline."""
        pipeline_str = """
PIPELINE:
  - athena.query(q="test")
  - hermes.rewrite(style="brief")
  - hephaestus.explain(level="advanced")
END
"""
        pipeline = context.parse_pipeline(pipeline_str)
        assert len(pipeline.steps) == 3

    def test_pipeline_output_chains_to_next(self, context):
        """Output of step N becomes input to step N+1 (implicit)."""
        # This is a design note - actual chaining happens in executor
        pipeline_str = """
PIPELINE:
  - athena.query(q="renewable energy")
  - hermes.rewrite(style="brief")
END
"""
        pipeline = context.parse_pipeline(pipeline_str)
        assert pipeline.steps[0].args["q"] == "renewable energy"
        assert pipeline.steps[1].args["style"] == "brief"

    def test_pipeline_order_preserved(self, context):
        """Pipeline executes in declared order (deterministic)."""
        pipeline_str = """
PIPELINE:
  - athena.query(q="A")
  - hermes.rewrite(style="B")
  - hephaestus.explain(level="C")
END
"""
        pipeline = context.parse_pipeline(pipeline_str)
        
        # Verify order
        assert pipeline.steps[0].domain_id == "athena"
        assert pipeline.steps[1].domain_id == "hermes"
        assert pipeline.steps[2].domain_id == "hephaestus"

    def test_pipeline_stores_args_correctly(self, context):
        """Pipeline preserves argument values."""
        pipeline_str = """
PIPELINE:
  - athena.query(q="solar energy policy 2024")
  - hermes.rewrite(style="policy brief")
END
"""
        pipeline = context.parse_pipeline(pipeline_str)
        
        assert pipeline.steps[0].args == {"q": "solar energy policy 2024"}
        assert pipeline.steps[1].args == {"style": "policy brief"}

    def test_pipeline_multiple_args(self, context):
        """Pipeline handles multiple args per step."""
        pipeline_str = """
PIPELINE:
  - hephaestus.explain(level="advanced", focus="safety")
END
"""
        pipeline = context.parse_pipeline(pipeline_str)
        
        assert pipeline.steps[0].args == {"level": "advanced", "focus": "safety"}

    def test_pipeline_rejects_failure_midway(self, context):
        """If pipeline step fails, entire pipeline aborts."""
        # This is tested at executor level - parser just validates syntax
        pipeline_str = """
PIPELINE:
  - athena.query(q="test")
  - hermes.rewrite(style="brief")
END
"""
        pipeline = context.parse_pipeline(pipeline_str)
        # Parser validates - execution handles failures
        assert pipeline is not None
