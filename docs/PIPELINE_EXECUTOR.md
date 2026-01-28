# Pipeline Executor - Architecture & Design

## Overview

The **Pipeline Executor** is a Stage-2 (Assisted Intelligence) subsystem of the Hearth architecture. This subsystem does NOT introduce autonomy, background execution, planning, or decision-making. It enables **cross-domain orchestration** by allowing users to compose multi-domain pipelines where output from one domain becomes input to the next.

## Architecture

### Pipeline Structure

```
PIPELINE:
  - domain1.method(arg1=val1, arg2=val2)
  - domain2.method(arg3=val3)
  - domain3.method(arg4=val4)
END
```

**Constraints:**
- **Max 3 domains per pipeline** (cognitive load limit)
- **Sequential left-to-right execution** (deterministic ordering)
- **Implicit data chaining** (output of step N → context for step N+1)
- **Fail-fast semantics** (any failure aborts entire pipeline)

### Data Flow

```
Input
  ↓
[Domain1] query → Output1
  ↓
[Domain2] query → Output2 (receives Output1 as context)
  ↓
[Domain3] query → Output3 (receives Output2 as context)
  ↓
Final Output
```

## Pipeline Executor Components

### 1. **PipelineStep**
```python
class PipelineStep:
    """Single step in a pipeline."""
    domain_id: str      # "athena", "hermes", "hephaestus", etc.
    method: str         # e.g., "query", "rewrite", "explain"
    args: Dict[str, str] # Arguments passed to method
```

### 2. **Pipeline**
```python
class Pipeline:
    """Complete pipeline specification."""
    steps: List[PipelineStep]  # Ordered steps
```

### 3. **Parser** (in ContextEngine)
```python
def parse_pipeline(self, pipeline_str: str) -> Optional[Pipeline]:
    """Parse pipeline DSL into Pipeline object."""
```

Validates:
- Syntax (correct PIPELINE/END markers)
- Domain existence
- Method existence on domain
- Argument types
- Max 3 domain constraint

### 4. **Executor** (future implementation)
```python
def execute_pipeline(self, pipeline: Pipeline) -> str:
    """Execute pipeline steps sequentially."""
```

Responsibilities:
- Look up each domain in registry
- Call methods with provided args + context from previous step
- Chain outputs between steps
- Handle errors (abort on failure)
- Return final output

## Usage Examples

### Example 1: Energy Policy Analysis
```
PIPELINE:
  - athena.query(q="carbon capture and storage technology")
  - hermes.rewrite(style="executive summary")
END
```

**Flow:**
1. Athena searches knowledge store for CCS info → detailed response
2. Hermes receives that response and rewrites it as executive summary → brief version
3. Return executive summary to user

### Example 2: Career Decision Support
```
PIPELINE:
  - apollo.analyze_habits(focus="work routine")
  - hermes.synthesize_schedule(duration="3 months")
  - hephaestus.recommend_tech_stack(role="new position")
END
```

**Flow:**
1. Apollo analyzes current work habits → strengths/weaknesses
2. Hermes schedules transition activities based on analysis → weekly plan
3. Hephaestus recommends tech stack for new role with transition plan → learning roadmap
4. Return complete career transition plan

### Example 3: Project Debugging
```
PIPELINE:
  - hephaestus.inspect_code(target="main.py")
  - hephaestus.debug_advise(severity="critical")
END
```

**Flow:**
1. Code inspector scans code → issues identified
2. Debug advisor provides solutions for critical issues → action plan
3. Return prioritized fixes

## Design Decisions

### Why Sequential (Not Parallel)?

**Decision:** Steps execute left-to-right, not in parallel.

**Rationale:**
- **Chaining:** Output of step N must inform step N+1
- **Simplicity:** Easier to reason about execution order
- **Determinism:** Same input always produces same output
- **Debugging:** Step-by-step execution easier to troubleshoot

**Trade-off:** Slightly slower, but guarantees correctness.

### Why Max 3 Domains?

**Decision:** Hard limit of 3 domains per pipeline.

**Rationale:**
- **Cognitive Load:** More than 3 steps becomes hard for users to predict/debug
- **Composability:** Can always chain pipelines if needed (future feature)
- **Focus:** Forces users to think about domain boundaries
- **Scope:** Prevents "God Pipelines" that try to do everything

### Why Implicit Chaining?

**Decision:** Don't require explicit "output → next_input" specification.

**Rationale:**
- **DRY:** Eliminates boilerplate variable passing
- **Intent:** Obvious that steps are related
- **Simplicity:** Users don't need to name intermediate values
- **Smart Default:** Most use cases want full context chain

**Alternative Considered:** Explicit output bindings
```
PIPELINE:
  - result1 = athena.query(q="...")
  - result2 = hermes.rewrite(input=result1, style="...")
END
```
**Rejected:** Too verbose, adds cognitive burden.

### Why Fail-Fast?

**Decision:** If any step fails, entire pipeline aborts.

**Rationale:**
- **Atomicity:** Pipeline succeeds or fails as a unit
- **Clarity:** No partial results confusing the user
- **Debugging:** Clear which step failed
- **Safety:** Don't want to proceed with broken intermediate state

**Alternative:** Continue with fallback values
**Rejected:** Hides errors, complicates logic.

## Parser Implementation Details

### Tokenization

1. Split on `:` for key-value pairs
2. Parse domain calls: `domain.method(args)`
3. Extract arguments: `arg1="value1", arg2="value2"`

### Validation Rules

1. **Syntax**: Must have PIPELINE and END markers
2. **Domain Existence**: Domain must be registered
3. **Method Existence**: Domain must have method
4. **Argument Count**: Args must match method signature
5. **Max Steps**: ≤ 3 domains per pipeline
6. **No Duplicates**: Each domain appears ≤ once (enforced by design)

### Error Handling

- **ParseError**: Syntax violations
- **ValidationError**: Domain/method doesn't exist
- **ConfigError**: Invalid arguments for method

## Future Extensions

### 1. Pipeline Composition
```
PIPELINE:
  - CALL analysis_pipeline
  - hermes.communicate_results(format="slides")
END
```

Allow pipelines to call other pipelines (tree of pipelines).

### 2. Conditional Branching
```
PIPELINE:
  - athena.query(q="...")
  - IF athena.confidence < 0.5:
      hermes.request_clarification()
    ELSE:
      hermes.finalize_response()
END
```

Branches based on intermediate results.

### 3. Parallel Domains
```
PARALLEL:
  - athena.query(q="...")
  - hermes.gather_context(scope="communication")
  THEN:
  - hephaestus.synthesize_plan()
END
```

Run independent steps in parallel, then combine.

### 4. Memory Integration
```
PIPELINE:
  - LOAD memory(topic="energy")
  - athena.query(q="...")
  - SAVE memory(result=$)
END
```

Integrate with mnemosyne memory system.

## Testing Strategy

### Unit Tests
- Parser correctness (valid/invalid pipelines)
- Token extraction
- Validation logic

### Integration Tests
- Cross-domain execution (once executor implemented)
- Output chaining verification
- Error handling (failed steps, missing domains)

### Performance Tests
- Parser latency (must be <100ms)
- Execution throughput (must complete in reasonable time)

### Regression Tests
- Existing domain functionality unchanged by pipeline system
- Pipeline parser doesn't break on edge cases

## Security Considerations

1. **Input Validation**: All pipeline inputs validated before execution
2. **Domain Isolation**: Domains can't directly access each other's internal state
3. **Rate Limiting**: Pipelines subject to same rate limits as individual queries
4. **Audit Logging**: All pipeline executions logged for compliance

## Performance Characteristics

| Aspect | Target | Notes |
|--------|--------|-------|
| Parse Time | <100ms | Linear in pipeline length |
| Validation | <50ms | O(steps) complexity |
| Execution | Varies | Depends on domain query latency |
| Memory | <1MB | Fixed per pipeline |

---

**Version:** 2.0  
**Status:** Stage 2 Implementation  
**Last Updated:** 2024
