# HEARTH v0.1 Architecture

**Status**: Minimal execution spine with optional LLM, memory, and knowledge lookup.  
**Date**: 2026-01-27  
**Stability**: ✅ Core guarantees enforced via tests and bounds checking

---

## System Design

```
CLI Input
    ↓
HearthKernel (config holder)
    ↓
HestiaAgent (orchestrator)
    ├─→ IntentClassifier (keyword-based routing)
    ├─→ MemoryStore (append-only SQLite, optional)
    ├─→ OllamaClient (Ollama LLM, optional)
    └─→ AthenaRetriever (JSON knowledge lookup, optional)
```

---

## Core Guarantees (v0.1)

### 1. Memory Write Gating

**Contract**: Memory is saved ONLY after explicit user confirmation.

- CLI asks: `"Would you like me to remember this? (yes/no):"`
- User responds: `yes` or `y`
- `agent.save_memory()` called only after confirmation
- Database state: Append-only (no edits, no deletes)

**Verified by**: `test_memory_write_only_for_substantial_input`

### 2. Memory Read Gating

**Contract**: Memories are shown ONLY when user explicitly requests them.

- Trigger patterns: "what do you remember", "show my memories", etc.
- Intent: Classified as `memory_query` (checked before LLM)
- Behavior: Direct database lookup, no LLM involved
- Fallback: "I don't have any memories saved yet" (graceful)

**Verified by**: `test_memory_query_intent_detection`, `test_memory_query_blocks_llm`

### 3. Memory Context Injection Gating

**Contract**: Past memories are injected into LLM ONLY when user explicitly asks for them.

- Trigger patterns: "based on what you remember", "using my past notes", etc.
- Check: `should_use_memory_for_context()` before LLM call
- Behavior: If no trigger, memory block not constructed or sent to LLM
- Default: User input goes to LLM as-is, no context injection

**Verified by**: `test_memory_context_trigger_detection`, `test_memory_context_not_injected_without_trigger`

### 4. Knowledge Search Gating

**Contract**: Knowledge search is triggered ONLY on explicit user request patterns.

- Trigger patterns: "search my knowledge for", "find documents about", etc.
- Intent: Classified as `knowledge_query` (checked before LLM)
- Behavior: Synchronous read-only lookup, no LLM, no memory injection
- Fallback: "I don't have any knowledge entries matching that" (graceful)

**Verified by**: `test_knowledge_query_intent_detection`, `test_knowledge_search_not_triggered_without_pattern`

### 5. Context Bounds

**Contract**: All context sent to LLM is strictly bounded.

| Component | Limit | Enforced |
|-----------|-------|----------|
| Memory items | 5 | `get_contextual_memory()` |
| Memory characters | 2000 | `get_contextual_memory()` |
| Total LLM context | 8000 | `_generate_llm_response()` |
| Knowledge excerpts | 200 | `knowledge_store.excerpt()` |
| Knowledge results | 5 | `retriever.search(limit=5)` |

**Verified by**: `test_memory_context_truncation_tracking`, `test_max_memory_items_enforced`

### 6. No Autonomous Behavior

**Contract**: System never acts on its own; all actions require explicit user input.

- ❌ Never infers preferences from memories
- ❌ Never ranks or prioritizes automatically
- ❌ Never injects data without user request
- ❌ Never makes decisions without user confirmation
- ✅ Always requires explicit trigger phrases
- ✅ Always asks for user confirmation (memory saves)
- ✅ Always reports when truncation happens

---

## Component Descriptions

### HestiaAgent (`hestia/agent.py`)

**Responsibility**: Route user input → intent → response

**Dispatch Order**:
1. Classify intent (keyword matching)
2. If `memory_query` → `_handle_memory_query()` (no LLM)
3. If `knowledge_query` → `_handle_knowledge_query()` (no LLM)
4. Else if LLM enabled → `_generate_llm_response()` with optional memory context
5. Else → `_generate_deterministic_response()`

**Methods**:
- `process()` - Main entry point
- `should_use_memory_for_context()` - Checks explicit trigger
- `get_contextual_memory()` - Builds bounded memory block with truncation tracking
- `should_offer_memory()` - Decides if input is worth saving
- `save_memory()` - Persists to SQLite after confirmation
- `_handle_memory_query()` - Retrieves and displays memories
- `_handle_knowledge_query()` - Searches knowledge base
- `_generate_llm_response()` - Calls Ollama with bounds enforcement
- `_generate_deterministic_response()` - Fallback text responses

### IntentClassifier (`hestia/intent_classifier.py`)

**Responsibility**: Keyword-based intent routing

**Intents**:
- `memory_query` - Explicit memory request patterns
- `knowledge_query` - Explicit knowledge search patterns
- `greeting` - "hello", "hi", etc.
- `help_request` - "help me", etc.
- `question` - "what", "how", "why", etc.
- `information_request` - "tell me", etc.
- `general` - Default/fallback

**Guarantee**: Patterns are checked in strict order (memory, knowledge, then keywords)

### MemoryStore (`mnemosyne/memory_store.py`)

**Responsibility**: Append-only SQLite storage of user-confirmed memories

**Schema**:
```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    metadata TEXT NOT NULL
)
```

**Operations**:
- `append()` - Write-only
- `get_recent(count)` - Read-only
- `count()` - Read-only
- No edits, no deletes, no decay

**Guarantee**: Never modifies or deletes records; SQLite ensures ACID

### AthenaRetriever (`athena/retriever.py`)

**Responsibility**: Synchronous keyword search over knowledge store

**Operations**:
- `search(query, limit)` - Keyword matching over title + content
- Returns list of `(title, excerpt, timestamp)` tuples
- Excerpts capped at 200 chars
- Limit capped at 5 results

**Guarantee**: Read-only; no ranking, no inference, no LLM involvement

### OllamaClient (`hestia/ollama_client.py`)

**Responsibility**: Pure function wrapper around Ollama HTTP API

**Operations**:
- `generate(prompt, system_prompt)` - Async call to Ollama
- `is_available()` - Health check
- No caching, no learning, no state

**Guarantee**: Pure function; stateless; deterministic (same input → same output if model unchanged)

---

## Failure Modes

### LLM Down

**What happens**:
1. `initialize()` fails with connection error
2. Agent falls back to deterministic responses
3. User sees fallback text: `"Full reasoning is disabled in v0.1."`

**Not a crash**: System continues working (all LLM calls optional)

### Memory Database Corrupt

**What happens**:
1. `_load()` catches exception
2. Operates with empty memory list `[]`
3. User sees: `"I don't have any memories saved yet."`

**Recovery**: User can delete `./data/memory.db` to reset

### Knowledge Store Missing

**What happens**:
1. `KnowledgeStore.__init__()` creates empty store if file missing
2. Search returns `[]`
3. User sees: `"I don't have any knowledge entries matching that."`

**Recovery**: User can manually populate `./data/knowledge.json`

### Context Too Large

**What happens**:
1. Total prompt exceeds `MAX_LLM_CONTEXT_CHARS` (8000)
2. User request truncated to fit
3. Truncation notice appended to LLM response
4. User is informed: `"[Note: Context size (X chars) exceeds safe limit...]"`

**Not a crash**: LLM still gets valid input; user aware of limitation

### Memory Items Too Many

**What happens**:
1. User has 100+ memories
2. `get_contextual_memory()` caps at 5 items AND 2000 chars
3. Older memories excluded
4. Truncation notice shown: `"[Note: Showing 5 of 100 memories due to size limits]"`

**Guarantee**: LLM always gets bounded context

---

## Test Coverage

**File**: `tests/test_v01_stability.py` (18 tests, all passing)

### Memory Write Confirmation (3 tests)
- ✅ Direct `save_memory()` saves to SQLite
- ✅ `should_offer_memory()` filters substantive input
- ✅ Memories persist across agent restarts

### Memory Read Gating (2 tests)
- ✅ Memory query patterns detected (all 8 variants)
- ✅ Memory queries blocked from LLM

### Memory Context Injection (3 tests)
- ✅ Context injection triggers detected (all 7 variants)
- ✅ No injection without explicit trigger
- ✅ Injected context properly formatted with warnings

### Athena Gating (4 tests)
- ✅ Knowledge query patterns detected (all 4 variants)
- ✅ Knowledge queries blocked from LLM
- ✅ No search without trigger pattern
- ✅ Excerpts capped at 200 chars

### Failure Modes (4 tests)
- ✅ Memory disabled → graceful message
- ✅ Knowledge disabled → graceful message
- ✅ Empty memory → helpful message
- ✅ No knowledge match → helpful message

### Context Bounds (2 tests)
- ✅ Truncation tracking returns `bool` flag
- ✅ Memory items capped at `MAX_MEMORY_ITEMS`

---

## CLI Usage

```bash
# Deterministic mode (no LLM, no memory)
$ python main.py

# With LLM reasoning
$ python main.py --llm

# With memory (requires user confirmation)
$ python main.py --memory

# Both LLM and memory
$ python main.py --llm --memory

# Example: Memory query
$ python main.py --memory
> what do you remember?
→ Lists saved memories (no LLM)

# Example: Knowledge search
$ python main.py
> search my knowledge for thermodynamics
→ Finds matching documents (no LLM, no memory)

# Example: LLM with memory context
$ python main.py --llm --memory
> based on what you remember, explain thermodynamics
→ LLM sees memory block + user request
```

---

## Configuration Constants

```python
# hestia/agent.py
MAX_MEMORY_ITEMS = 5           # Max memories per injection
MAX_MEMORY_CHARS = 2000        # Max memory block size
MAX_LLM_CONTEXT_CHARS = 8000   # Max total prompt
EXCERPT_MAX_CHARS = 200        # Max knowledge excerpt
```

These can be adjusted in `hestia/agent.py` without changing behavior.

---

## What v0.1 Is NOT

- ❌ Not a retrieval-augmented generation (RAG) system
- ❌ Not a knowledge graph
- ❌ Not a planner or action executor
- ❌ Not a multi-domain reasoner
- ❌ Not learning from interactions
- ❌ Not encrypted or secure
- ❌ Not distributed or scalable
- ❌ Not a general-purpose knowledge store

---

## What v0.1 IS

- ✅ A minimal execution spine
- ✅ User-controlled optional LLM
- ✅ Explicit memory write/read gating
- ✅ Explicit knowledge lookup gating
- ✅ Strict context bounds with transparency
- ✅ Graceful failure modes
- ✅ Fully tested core guarantees
- ✅ Production-ready for simple interactions

---

## Next Steps (Not Planned for v0.1)

If you want to extend HEARTH:

1. **Memory enhancement**: Add memory decay, summarization, or search
2. **Knowledge enhancement**: Add RAG, embeddings, or semantic search
3. **Domain reasoning**: Implement domain-specific services (apollo, hermes, etc.)
4. **Planning**: Add FSM-based planner for multi-step tasks
5. **Actions**: Add action execution framework
6. **Security**: Add encryption, access control, audit logging

Each requires explicit design review and test additions.

---

**Last Updated**: 2026-01-27  
**Test Status**: ✅ 18/18 passing  
**Stability**: ✅ Verified via CI  
**Documentation**: ✅ Complete
