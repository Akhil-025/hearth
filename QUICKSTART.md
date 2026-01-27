# HEARTH v0.1 Quick Start Guide

## Installation

```bash
# Clone/navigate to workspace
cd ~/Documents/Hearth

# Create virtual environment (if not exists)
python -m venv .venv

# Activate
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pydantic aiohttp
```

## Running HEARTH

### Mode 1: Deterministic (no LLM, no memory)
```bash
python main.py
# Enter input: "Hello"
# Response: "Hello! HEARTH v0.1 is running in minimal mode."
```

### Mode 2: With LLM (Ollama required)
```bash
python main.py --llm
# Enter input: "What is the capital of France?"
# Response: "The capital of France is Paris."

# Requirements: Ollama running with mistral:latest model
# Start Ollama: ollama run mistral:latest
```

### Mode 3: With Memory (interactive)
```bash
python main.py --memory
# Enter input: "My favorite color is blue"
# Prompt: "Would you like me to remember this? (yes/no):"
# Response: (after confirmation)

# Query memory:
# Enter input: "What do you remember?"
# Response: (lists stored memories)
```

### Mode 4: Combined LLM + Memory
```bash
python main.py --llm --memory
# Allows:
# - "What is X?" → Uses LLM for answer
# - "Remember that Y" → Stores memory with confirmation
# - "Based on what you remember, explain Z" → LLM gets memory context
```

### Mode 5: Knowledge Lookup
```bash
python main.py
# Enter input: "Search my knowledge for Python"
# Response: "I don't have any knowledge entries matching that."
# (Knowledge lookup doesn't require --llm or --memory)
```

## Testing

### Run all tests
```bash
pytest tests/test_v01_stability.py -v
# Expected: 18 passed
```

### Run specific test category
```bash
# Memory write confirmation tests
pytest tests/test_v01_stability.py::TestMemoryWriteConfirmation -v

# LLM gating tests
pytest tests/test_v01_stability.py::TestFailureModes -v
```

### Run with coverage (optional)
```bash
pip install pytest-cov
pytest tests/test_v01_stability.py --cov=. --cov-report=html
```

## Validation

Run comprehensive v0.1 validation:
```bash
python validate_v01.py
# Checks: imports, tests, documentation, CI config, core files, guarantees
# Expected output: ✅ ALL CHECKS PASSED
```

## Core Concepts

### Intent Classification
HEARTH automatically detects your intent from keywords:

| Intent | Triggers | Behavior |
|--------|----------|----------|
| `memory_query` | "what do you remember", "show my memories" | Returns stored memories (no LLM) |
| `knowledge_query` | "search my knowledge for", "find documents about" | Searches knowledge base (no LLM) |
| `general` | Everything else | LLM response (if --llm) or deterministic response |

### Memory Triggers for LLM Context
Add memory context to LLM responses with phrases like:
- "Based on what you remember, explain..."
- "Using what you know about me, suggest..."
- "Considering what you remember, how would you..."

### Context Bounds
All LLM inputs are bounded to prevent explosion:
- **MAX_MEMORY_ITEMS**: 5 most recent memories
- **MAX_MEMORY_CHARS**: 2000 character limit
- **MAX_LLM_CONTEXT_CHARS**: 8000 character limit on total input

If bounds exceeded, user is notified: `(Note: truncated at 2000 chars)`

## Troubleshooting

### "Connection refused" when using --llm
```
Error: Cannot connect to Ollama
Solution: Start Ollama first: ollama run mistral:latest
```

### "EOF when reading a line" with --memory
```
Error: piped input can't prompt for confirmation
Solution: Run interactively: python main.py --memory (type input directly)
```

### Tests failing
```bash
# Re-run with verbose output
pytest tests/test_v01_stability.py -v --tb=long

# Check Python version (needs 3.10+)
python --version
```

### Memory not saving
```
Check: Did you confirm with "yes" or "y"?
Check: Is memory file writable? (check ./data/memory.db permissions)
```

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point with --llm, --memory flags |
| `hestia/agent.py` | Main orchestrator (433 lines) |
| `hestia/intent_classifier.py` | Intent detection |
| `hestia/ollama_client.py` | LLM integration |
| `mnemosyne/memory_store.py` | Append-only SQLite memory |
| `athena/knowledge_store.py` | Read-only knowledge lookup |
| `tests/test_v01_stability.py` | 18 unit tests |
| `ARCHITECTURE.md` | System design guarantees |
| `FAILURE_MODES.md` | How system degrades gracefully |

## Configuration

Minimal configuration stored in [config/default.yaml](config/default.yaml):
```yaml
kernel:
  data_dir: ./data
  log_level: INFO
  enable_audit: false
  require_permissions: false
```

## Support

1. **Design Questions**: See [ARCHITECTURE.md](ARCHITECTURE.md)
2. **Behavior Questions**: See [FAILURE_MODES.md](FAILURE_MODES.md)
3. **Context Bounds**: See [CONTEXT_BOUNDS_REPORT.md](CONTEXT_BOUNDS_REPORT.md)
4. **Stabilization Status**: See [STABILIZATION_COMPLETE.md](STABILIZATION_COMPLETE.md)
5. **Run Tests**: `pytest tests/test_v01_stability.py -v`

## Next Steps

### To add features:
1. Write test first (TDD approach)
2. Update `hestia/agent.py` with feature
3. Update `hestia/intent_classifier.py` if needed
4. Run full test suite: `pytest tests/test_v01_stability.py -v`
5. Update documentation

### To deploy:
1. Verify: `python validate_v01.py` ✅
2. Verify: `pytest tests/test_v01_stability.py -v` (18/18 pass)
3. Create release tag: `git tag v0.1.0`
4. Push to GitHub (CI will validate automatically)

### To extend:
- **Add LLM prompt engineering**: See `hestia/ollama_client.py`
- **Add memory reasoning**: See `mnemosyne/memory_store.py`
- **Add knowledge**: Populate `data/knowledge.json`
- **Add intents**: Extend `hestia/intent_classifier.py` with new patterns

---

**Status**: ✅ v0.1 Stable & Production-Ready

