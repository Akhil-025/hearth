# HEARTH Documentation Index

Welcome to HEARTH v0.1 – A minimal, deterministic execution spine with optional LLM, memory, and knowledge.

---

## 📖 Quick Navigation

### 🚀 Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** – Installation, running HEARTH, usage examples, troubleshooting

### 📚 For Understanding the System
- **[ARCHITECTURE.md](ARCHITECTURE.md)** – System design, execution flow, 9 core guarantees
- **[FAILURE_MODES.md](FAILURE_MODES.md)** – How system degrades, recovery paths for each failure mode
- **[CONTEXT_BOUNDS_REPORT.md](CONTEXT_BOUNDS_REPORT.md)** – LLM context bounding logic and examples

### ✅ For Project Status
- **[STATUS.md](STATUS.md)** – Executive summary of stabilization completion
- **[STABILIZATION_COMPLETE.md](STABILIZATION_COMPLETE.md)** – Full stabilization checklist and maintenance guide
- **[STATUS_VISUAL.txt](STATUS_VISUAL.txt)** – ASCII art status summary

### 📝 Project Overview
- **[README.md](README.md)** – Project description and features

---

## 🎯 By Use Case

### "I want to run HEARTH"
1. Read [QUICKSTART.md](QUICKSTART.md)
2. Run: `python main.py [--llm] [--memory]`
3. Check [FAILURE_MODES.md](FAILURE_MODES.md) if issues arise

### "I want to understand how it works"
1. Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
2. Read [FAILURE_MODES.md](FAILURE_MODES.md) for degradation behavior
3. Review [CONTEXT_BOUNDS_REPORT.md](CONTEXT_BOUNDS_REPORT.md) for LLM context details

### "I want to extend HEARTH"
1. Read [ARCHITECTURE.md](ARCHITECTURE.md) for guarantees
2. Check [STABILIZATION_COMPLETE.md](STABILIZATION_COMPLETE.md) for maintenance guide
3. Write test first (TDD approach)
4. Update documentation

### "I want to verify stability"
1. Run: `pytest tests/test_v01_stability.py -v`
2. Run: `python validate_v01.py`
3. Check [STABILIZATION_COMPLETE.md](STABILIZATION_COMPLETE.md) for full checklist

### "I want to deploy HEARTH"
1. Run: `python validate_v01.py` (all checks must pass)
2. Run: `pytest tests/test_v01_stability.py -v` (18/18 must pass)
3. Tag release: `git tag v0.1.0`
4. Push to GitHub (CI validates automatically)

---

## 📊 Document Map

```
HEARTH v0.1
├── 🚀 QUICKSTART.md                      (5.9 KB)
│   ├─ Installation
│   ├─ Running HEARTH (4 modes)
│   ├─ Testing
│   ├─ Validation
│   ├─ Key concepts & troubleshooting
│   └─ Support links
│
├── 📐 ARCHITECTURE.md                    (11.2 KB)
│   ├─ System design & execution flow
│   ├─ 9 core guarantees with test refs
│   ├─ Memory model (append-only)
│   ├─ Knowledge model (JSON, keyword search)
│   ├─ LLM gating rules
│   ├─ Bounds enforcement
│   ├─ Failure mode handling
│   └─ Future extensions
│
├── 🛡️ FAILURE_MODES.md                   (13.0 KB)
│   ├─ Memory subsystem offline
│   ├─ LLM subsystem offline
│   ├─ Knowledge subsystem offline
│   ├─ Database corruption
│   ├─ Network timeouts
│   ├─ Graceful fallback examples
│   └─ Recovery procedures
│
├── 📏 CONTEXT_BOUNDS_REPORT.md           (5.3 KB)
│   ├─ Why bounds matter
│   ├─ MAX_* constant values & rationale
│   ├─ Truncation scenarios with examples
│   ├─ User transparency implementation
│   └─ Performance implications
│
├── ✅ STABILIZATION_COMPLETE.md          (11.5 KB)
│   ├─ 13-point stabilization checklist
│   ├─ 18/18 test status breakdown
│   ├─ Runtime verification commands
│   ├─ Core guarantees reference
│   ├─ Documentation map
│   ├─ File structure
│   ├─ Known limitations
│   └─ Maintenance procedures
│
├── 📊 STATUS.md                          (9.7 KB)
│   ├─ What is HEARTH v0.1?
│   ├─ Stabilization phases (8 complete)
│   ├─ Test coverage summary
│   ├─ Running HEARTH (4 modes)
│   ├─ Core guarantees table
│   ├─ Validation results
│   ├─ Production checklist
│   └─ Quick links & next steps
│
├── 📋 STATUS_VISUAL.txt                  (ASCII art status summary)
│   ├─ Visual test results
│   ├─ File list
│   ├─ Guarantee checklist
│   ├─ Quick start commands
│   └─ Performance metrics
│
└── 📝 README.md                          (6.1 KB)
    ├─ Project description
    ├─ Features
    ├─ Quick start
    ├─ Architecture
    └─ Contributing
```

---

## 🔑 Key Concepts

### Execution Modes
| Mode | Command | Features |
|------|---------|----------|
| **Deterministic** | `python main.py` | Always works, no LLM, no memory |
| **With LLM** | `python main.py --llm` | Reasoning via Ollama, no memory |
| **With Memory** | `python main.py --memory` | Store & query memories, no LLM |
| **Full Stack** | `python main.py --llm --memory` | All features enabled |

### Intent Classification
- **memory_query**: "what do you remember" → Returns memories (no LLM)
- **knowledge_query**: "search my knowledge for" → Searches knowledge (no LLM)
- **general**: Everything else → LLM response (if enabled) or deterministic response

### Context Bounds
- **MAX_MEMORY_ITEMS**: 5 most recent memories
- **MAX_MEMORY_CHARS**: 2000 character limit on memory block
- **MAX_LLM_CONTEXT_CHARS**: 8000 character limit on total LLM input

### Design Guarantees
1. Memory writes never automatic (require explicit "yes")
2. Memory reads never automatic (explicit "what do you remember" pattern)
3. Memory context never injected automatically (explicit "based on what you remember" pattern)
4. Knowledge never used automatically (explicit "search my knowledge for" pattern)
5. All LLM context bounded (deterministic limits)
6. Truncation transparent to user (notified when bounds exceeded)
7. Graceful degradation (missing subsystems return helpful messages)

---

## 🧪 Testing & Validation

### Run Tests
```bash
# All tests
pytest tests/test_v01_stability.py -v

# Specific test
pytest tests/test_v01_stability.py::TestMemoryWriteConfirmation -v

# With coverage
pytest tests/test_v01_stability.py --cov=. --cov-report=html
```

### Validate System
```bash
python validate_v01.py
# Checks: imports, tests, docs, CI config, core files, guarantees
```

### Test Categories
- **Memory Write Confirmation** (3 tests)
- **Memory Read Gating** (2 tests)
- **Memory Context Injection** (3 tests)
- **Athena Knowledge Gating** (4 tests)
- **Failure Modes** (4 tests)
- **Context Bounds** (2 tests)
- **Total**: 18 tests, all passing ✅

---

## 📦 What's Included

✅ Minimal execution spine (~500 lines)  
✅ Intent classifier (keyword-based routing)  
✅ Optional Ollama LLM integration  
✅ Optional append-only memory (SQLite)  
✅ Optional knowledge lookup (JSON)  
✅ Context bounds enforcement  
✅ Graceful failure modes  
✅ 18 unit tests (all passing)  
✅ GitHub Actions CI/CD  
✅ 62+ KB of documentation  

---

## ❌ What's Intentionally Excluded

❌ Planning or agent orchestration  
❌ Domain-specific modules  
❌ Embeddings or vector search  
❌ Multi-turn conversation history  
❌ Autonomous behavior  
❌ Event bus or service registry  
❌ Audit logging or permission system  

---

## 🎯 Next Steps

1. **To run**: `python main.py [--llm] [--memory]`
2. **To test**: `pytest tests/test_v01_stability.py -v`
3. **To validate**: `python validate_v01.py`
4. **To extend**: Write test first, implement feature, update docs
5. **To deploy**: Tag release, push to GitHub, wait for CI

---

## 📞 Support

| Question | Document |
|----------|----------|
| How do I get started? | [QUICKSTART.md](QUICKSTART.md) |
| How does the system work? | [ARCHITECTURE.md](ARCHITECTURE.md) |
| What happens if something fails? | [FAILURE_MODES.md](FAILURE_MODES.md) |
| Why are there context bounds? | [CONTEXT_BOUNDS_REPORT.md](CONTEXT_BOUNDS_REPORT.md) |
| Is it production-ready? | [STATUS.md](STATUS.md) |
| What was stabilized? | [STABILIZATION_COMPLETE.md](STABILIZATION_COMPLETE.md) |

---

**Status**: ✅ v0.1 Complete & Production-Ready  
**Date**: January 27, 2025  
**Last Updated**: See individual documents for details

