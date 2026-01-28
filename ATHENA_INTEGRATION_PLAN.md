# Athena Integration into HEARTH v0.2

## Proposal: Architecture & File Mapping

### HEARTH Constraints (Non-Negotiable)

1. **No Autonomy:** Athena never runs unless user explicitly asks
2. **No Background Execution:** No watchers, no auto-indexing, no polling
3. **Deterministic:** Same query → same results (within vector DB bounds)
4. **No Side Effects:** Read-only at runtime, explicit user confirmation for ingestion
5. **No Memory Writes:** Never touches Mnemosyne
6. **No LLM Calls:** Returns raw context only; Hestia decides if/how to use it
7. **Intent Gating:** Only activates on explicit phrases: "search my notes", "look up", "from my PDFs", etc.
8. **Testable:** All integrations are isolated and testable

---

## File Mapping: Athena → HEARTH/Athena

### Source (Athena Repo) → Target (HEARTH/Athena)

```
Athena/
├── config/
│   ├── __init__.py          → athena/config.py (single module)
│   ├── config_manager.py    → KEEP (refactor to HEARTH config style)
│   └── paths.py             → KEEP (merge into config.py)
│
├── models/                  → athena/models.py (flatten into single module)
│   ├── source_document.py
│   ├── query_result.py
│   └── search_result.py
│
├── services/
│   ├── query_service.py     → PARTIAL (keep query logic, remove LLM calls)
│   ├── context_assembler.py → athena/context.py
│   └── prompt_builder.py    → REMOVE (HEARTH Hestia handles prompts)
│
├── pdf_processor.py         → athena/ingestor.py (rename, explicit ingestion only)
├── local_rag.py             → athena/retriever.py (vector search logic only)
│
├── llm_wrappers/            → REMOVE (HEARTH's Hestia handles LLM)
├── flask_api_server.py      → REMOVE (HEARTH has CLI/REST at interfaces/)
├── auto_solver.py           → REMOVE (no autonomous execution)
├── frontend/                → REMOVE (HEARTH has CLI, no web UI)
├── handlers/                → REMOVE (HEARTH has its own handlers)
├── factories/               → REMOVE (HEARTH manages service lifecycle)
├── utils/                   → athena/utils.py (keep only text processing)
├── run_*.bat                → REMOVE (no standalone scripts)
├── main.py                  → REMOVE (HEARTH is the entry point)
│
└── Kept as reference:
    ├── requirements.txt     → Merge into HEARTH's requirements.txt
    └── LICENSE              → Keep MIT attribution
```

### Target Structure (HEARTH/Athena)

```
athena/
├── __init__.py              # Exports AthenaService only
├── service.py               # PUBLIC INTERFACE - AthenaService.query()
├── retriever.py             # Vector search (ChromaDB wrapper)
├── ingestor.py              # Manual document ingestion
├── index.py                 # Index management (list, stats)
├── models.py                # Data models (SourceDocument, QueryResult)
├── config.py                # Local-only configuration
├── context.py               # Context formatting
├── utils.py                 # Text processing utilities
└── adapters/
    ├── __init__.py
    ├── pdf_adapter.py       # PDF text extraction (from pdf_processor.py)
    └── chunker.py           # Text chunking logic
```

---

## Public Interface: AthenaService

### Single Entry Point

```python
from athena.service import AthenaService
from athena.models import QueryResult

service = AthenaService(config={...})

# Only method exposed:
result: QueryResult = service.query(
    question: str,
    subject_filter: Optional[str] = None,
    module_filter: Optional[str] = None,
    top_k: int = 5
)

# QueryResult contains:
# - question: str
# - sources: List[SourceDocument]  # Chunks with page numbers, filenames
# - metadata: Dict                 # Stats: vectors_searched, time_ms
# - (NO answer field - Hestia adds LLM answer if desired)
```

### Why This Design

- **Pure Function:** No side effects, no state mutation
- **Deterministic:** Same question + filters → same sources
- **Read-Only:** No writes to index at runtime
- **No LLM:** Returns raw context only
- **Testable:** Mocked ChromaDB for unit tests
- **Intent-Gated:** Only called if user matches intent patterns

---

## Intent Gating in Hestia

### New Patterns (athena_patterns)

```python
athena_patterns = [
    "search my notes",
    "look up in my",
    "search my knowledge",
    "what do my notes say",
    "from my pdfs",
    "search my documents",
    "find in my materials",
    "search my study material",
]
```

### Routing Logic

```python
# In HestiaAgent.process():
if intent == "athena_query":
    # Explicit user query to knowledge base
    sources = self.athena.query(user_input)
    
    # Format sources for display
    response_text = self._format_athena_response(sources)
    
    # If user asks for LLM answer, call Ollama:
    # "search my notes and answer"  → retrieve + LLM
    # "search my notes"             → retrieve only
    
    return AgentResponse(
        text=response_text,
        intent="athena_query",
        sources=sources
    )
```

---

## Implementation Plan (Incremental)

### Phase 1: Core Data Models & Config

1. Create `athena/models.py` with SourceDocument, QueryResult
2. Create `athena/config.py` with AthenaConfig, data_dir, index_path
3. Add to `pyproject.toml`: chromadb, sentence-transformers, PyPDF2, rank-bm25

### Phase 2: Ingestion & Retrieval

1. Create `athena/adapters/pdf_adapter.py` (extract from pdf_processor.py)
2. Create `athena/adapters/chunker.py` (text splitting logic)
3. Create `athena/ingestor.py` with explicit ingestion (no auto-watching)
4. Create `athena/retriever.py` (ChromaDB vector search)
5. Create `athena/index.py` (list, stats)

### Phase 3: Service Layer

1. Create `athena/service.py` with AthenaService.query()
2. Create `athena/context.py` (format sources for display)
3. Create `athena/utils.py` (text helpers)
4. Create `athena/__init__.py` (export AthenaService only)

### Phase 4: Integration with Hestia

1. Update `hestia/intent_classifier.py`: add athena_patterns
2. Update `hestia/agent.py`: import AthenaService, add routing
3. Add `_handle_athena_query()` method

### Phase 5: Testing

1. Create `tests/test_athena/` directory
2. Add tests:
   - `test_intent_detection.py` - Athena intent patterns
   - `test_service.py` - Query, retrieval, formatting
   - `test_constraints.py` - No LLM, no memory, no side effects
   - `test_integration.py` - Agent routing, response format

---

## Hard Constraints (Enforced by Tests)

- ❌ NO LLM calls in Athena (mocked and verified)
- ❌ NO memory writes or reads
- ❌ NO background indexing (manual ingestion only)
- ❌ NO automatic retrieval
- ❌ NO cloud features enabled
- ✅ Deterministic responses (same input → same sources)
- ✅ Intent-gated activation only
- ✅ Read-only at runtime
- ✅ Pure function: query() with no side effects
- ✅ Explicit user confirmation for ingestion

---

## Configuration (Default: Disabled)

```python
# athena/config.py
class AthenaConfig:
    enabled: bool = False                          # Default: OFF
    data_dir: Path = Path("./data/notes")          # Where PDFs live
    index_dir: Path = Path("./.athena_index")      # Where vectors stored
    chunk_size: int = 512
    chunk_overlap: int = 50
    embedding_model: str = "all-MiniLM-L6-v2"     # Local, offline
    top_k: int = 5                                 # Default sources per query
```

### Enabling Athena

```python
# In main.py or config:
agent = HestiaAgent(config={
    "enable_athena": True,  # User choice
    "athena_config": {
        "data_dir": "./data/notes",
        "index_dir": "./.athena_index"
    }
})
```

---

## No Changes to HEARTH Core

- ✅ Hestia remains the sole orchestrator
- ✅ Memory, LLM, domains all unchanged
- ✅ All v0.2 tests remain passing
- ✅ Athena is purely additive (new intent path)
- ✅ Can be disabled entirely with `enable_athena: False`

---

## Next Steps

1. Confirm this architecture aligns with your vision
2. Implement Phase 1-2 (data models, config, adapters)
3. Implement Phase 3 (service layer)
4. Wire into Hestia (Phase 4)
5. Comprehensive testing (Phase 5)
6. Update README with Athena domain docs

---

## Why This Works

| Constraint | How Satisfied |
|-----------|---|
| No Autonomy | Explicit intent gating only, never auto-triggers |
| Deterministic | Vector search is deterministic (same query → same results) |
| No LLM | Returns raw context only |
| No Memory | Zero interaction with Mnemosyne |
| Read-Only | Retrieval only; ingestion requires explicit command |
| No Side Effects | Pure function: query() returns data, no mutations |
| Testable | Mocked ChromaDB, no external deps, isolated tests |
| Backward Compatible | All v0.2 tests pass; Athena is additive |

