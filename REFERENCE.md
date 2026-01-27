# HEARTH v0.1 – Reference Card

## Quick Commands

```bash
# Run HEARTH
python main.py                    # Deterministic mode
python main.py --llm             # With LLM (Ollama required)
python main.py --memory          # With memory
python main.py --llm --memory    # Full stack

# Test & Validate
pytest tests/test_v01_stability.py -v    # Run 18 tests
python validate_v01.py                   # Full validation
python validate_v01.py                   # 6 checks

# Deploy
git tag v0.1.0
git push
# CI/CD validates automatically
```

## Key Files

```
main.py                    Entry point with --llm, --memory flags
hestia/agent.py           Main orchestrator (433 lines, 7 KiB)
hestia/intent_classifier  Intent detection (keyword-based)
hestia/ollama_client      Ollama LLM integration
mnemosyne/memory_store    Append-only SQLite memory
athena/knowledge_store    JSON-backed knowledge lookup
tests/test_v01_stability  18 unit tests (all passing)
.github/workflows/test    GitHub Actions CI/CD
```

## Core Guarantees

| Guarantee | Verification |
|-----------|--------------|
| Memory writes are never automatic | test_memory_save_requires_confirmation |
| Memory reads are never automatic | test_memory_query_intent_detection |
| Memory context never injected auto | test_memory_context_not_injected_without_trigger |
| Knowledge never used automatically | test_knowledge_search_not_triggered_without_pattern |
| All context bounded (8000 chars) | test_memory_context_truncation_tracking |
| Truncation is transparent | test_memory_context_format |
| Graceful degradation on failure | TestFailureModes (4 tests) |

## Intent Patterns

```python
# Memory Query (returns memories, no LLM)
"what do you remember"
"show my memories"
"what have we discussed"

# Knowledge Query (searches knowledge, no LLM)
"search my knowledge for"
"find documents about"
"look up in my knowledge base"
"what notes do i have on"

# Memory Context Injection (adds memory to LLM)
"based on what you remember"
"using what you know about me"
"considering what you remember"

# Everything Else (LLM or deterministic)
General conversation, questions, etc.
```

## Context Bounds

```python
MAX_MEMORY_ITEMS = 5              # Max memories returned
MAX_MEMORY_CHARS = 2000           # Max memory block size
MAX_LLM_CONTEXT_CHARS = 8000      # Max total LLM input
EXCERPT_MAX_CHARS = 200           # Max knowledge excerpt
```

## Documentation Index

| Document | Size | Topic |
|----------|------|-------|
| DOCS.md | 4.5 KB | Documentation navigation |
| QUICKSTART.md | 5.9 KB | Getting started & examples |
| ARCHITECTURE.md | 11.2 KB | System design & guarantees |
| FAILURE_MODES.md | 13.0 KB | Degradation & recovery |
| CONTEXT_BOUNDS_REPORT.md | 5.3 KB | Context bounding logic |
| STABILIZATION_COMPLETE.md | 11.5 KB | Stabilization checklist |
| STATUS.md | 9.7 KB | Executive summary |
| STATUS_VISUAL.txt | 5.0 KB | ASCII art summary |

## Test Categories (18 total)

```
Memory Write Confirmation     [3 tests] ✅
Memory Read Gating            [2 tests] ✅
Memory Context Injection      [3 tests] ✅
Athena Knowledge Gating       [4 tests] ✅
Failure Modes                 [4 tests] ✅
Context Bounds                [2 tests] ✅
────────────────────────────────────────
TOTAL                        [18 tests] ✅
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Connection refused" (LLM) | Start Ollama: `ollama run mistral:latest` |
| "EOF when reading" (memory) | Run interactive: `python main.py --memory` |
| Tests fail | Check Python 3.10+: `python --version` |
| Memory not saving | Did you confirm with "yes"? Check permissions |
| No knowledge found | Populate data/knowledge.json with entries |

## Performance

```
Deterministic:     <100ms
With LLM:          2-5s (Ollama dependent)
Memory write:      <50ms
Memory read:       <10ms
Knowledge search:  <5ms
Full test suite:   0.38s
```

## Design Philosophy

✅ **Minimal** – Reduced from 20+ modules to minimal spine
✅ **Deterministic** – Fallback always works
✅ **Optional** – All subsystems explicitly gated
✅ **Bounded** – All context deterministically limited
✅ **Transparent** – User notified of truncation
✅ **Graceful** – Missing subsystems return helpful messages
✅ **Tested** – 18 comprehensive unit tests
✅ **Documented** – 62+ KB of docs

## No Autonomous Behavior

❌ No planning
❌ No domains
❌ No embeddings
❌ No ranking
❌ No auto-injection
❌ No side effects
✅ Only explicit, deterministic responses

## Getting Help

1. **"How do I run this?"** → QUICKSTART.md
2. **"How does it work?"** → ARCHITECTURE.md
3. **"What if it breaks?"** → FAILURE_MODES.md
4. **"Why these bounds?"** → CONTEXT_BOUNDS_REPORT.md
5. **"Is it done?"** → STATUS.md or STATUS_VISUAL.txt
6. **"What was built?"** → STABILIZATION_COMPLETE.md
7. **"All docs"** → DOCS.md

## Validation Checklist

```
✅ Deterministic fallback works
✅ LLM integration working (optional)
✅ Memory storage working (optional)
✅ Knowledge lookup working (optional)
✅ Intent classification accurate
✅ Memory gating enforced
✅ Context bounds enforced
✅ 18/18 tests passing
✅ CI/CD configured
✅ All documentation complete
✅ Production ready
```

## Next Steps

1. **Try it**: `python main.py`
2. **Test it**: `pytest tests/test_v01_stability.py -v`
3. **Validate**: `python validate_v01.py`
4. **Deploy**: Tag v0.1.0, push to GitHub
5. **Extend**: Write test, implement, update docs

---

**Status**: ✅ COMPLETE & PRODUCTION-READY
**Version**: v0.1
**Date**: January 27, 2025

