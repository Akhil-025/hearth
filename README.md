# HEARTH - Personal Cognitive OS (v0.1)

> **Recovery Status**: ✅ Execution spine operational as of 2026-01-27

Hearth is an experimental, local-first cognitive system prototype.
It is a research and engineering scaffold, not a finished assistant.

This repository explores how a governed personal cognitive system *could* be built, with explicit separation between:

* orchestration (Hearth)
* interaction (Hestia)
* memory (Mnemosyne)
* knowledge (Athena)
* finance (Pluto)
* domain reasoning modules (Hermes, Hephaestus, Apollo, Dionysus)

---

## Project Status (v0.1 - Minimal Execution Spine)

### ✅ What Works NOW (v0.1)

* ✅ **Runnable**: `python main.py` executes without crashing
* ✅ **CLI Input/Output**: Accepts one line of input, produces deterministic response
* ✅ **Intent Classification**: Keyword-based classification (greeting, help, question, etc.)
* ✅ **Clean Exit**: No hung processes or async conflicts
* ✅ **No External Dependencies**: Offline, no LLM/network/database required for basic execution

### ❌ What Does NOT Work (Disabled in v0.1)

* ❌ LLM reasoning (ollama_client disabled)
* ❌ Memory persistence (mnemosyne disabled)
* ❌ Domain intelligence (apollo/dionysus/hephaestus/hermes disabled)
* ❌ Knowledge retrieval (athena disabled)
* ❌ Financial tracking (pluto disabled)
* ❌ Security/encryption (explicitly disabled with warning)
* ❌ Action execution (action_router disabled)
* ❌ Context building (context_builder disabled)
* ❌ Planning FSM (planner_fsm disabled)
* ❌ Service lifecycle management (kernel simplified)

### ⚠️ Important Warnings

* **Security is EXPLICITLY DISABLED**: No encryption, auth, permissions, or audit
* **Not production-ready**: Development/testing only
* **Single-shot execution**: No persistent state or multi-turn conversations
* **Naive intent classification**: Keyword matching only, no semantic understanding

---

## Quick Start

### Prerequisites
- Python 3.10+
- Virtual environment recommended

### Running (v0.1)

```bash
# Activate your virtual environment (if applicable)
source .venv/bin/activate  # Unix
.venv\Scripts\Activate.ps1  # Windows

# Run the minimal execution spine
python main.py

# Or pipe input directly
echo "hello" | python main.py
```

### Expected Behavior

```
HEARTH v0.1 - Minimal Execution Spine
Enter input: hello
Response: Hello! HEARTH v0.1 is running in minimal mode.
```

See [EXECUTION_SPINE_REPORT.md](EXECUTION_SPINE_REPORT.md) for detailed validation results.

---

## High-Level Architecture

```
Hearth (runtime / orchestration)
│
├── Hestia      – user-facing agent (intent, planning, responses)
├── Mnemosyne  – memory engine (structured + episodic)
├── Athena     – knowledge & document reasoning
├── Pluto      – financial analysis (advisory only)
└── Domains
    ├── Hermes      – communication & social reasoning
    ├── Hephaestus – engineering & technical reasoning
    ├── Apollo     – health & wellbeing (non-medical)
    └── Dionysus   – creativity, music, leisure
```

Each component is intended to be:

* independently testable
* permission-bounded
* auditable

These guarantees are not yet enforced in code.

---

## What HEARTH Is Not

HEARTH is not:

* a chatbot
* an autonomous agent
* a task-executing AI
* a secure personal assistant
* a replacement for cloud assistants
* a production system

Any claims of autonomy, safety, or encryption should be considered future goals, not current features.

---

## Execution Reality (Honest Disclosure)

As of now:

* Configuration files are present but not fully wired
* Encryption utilities exist in name only
* Permission and invariant systems are defined but not consistently enforced
* Some modules contain TODOs or empty implementations
* Not all services are correctly registered or invoked at runtime

If you try to run this as-is, expect failures.

This is intentional during early architectural exploration.

---

## Development Philosophy

HEARTH is built around the idea that:

> Long-term personal AI systems must prioritize governance, auditability, and correctness over speed or autonomy.

Design principles:

* Explicit over implicit
* Refusal over hallucination
* Memory governance over convenience
* Deterministic behavior over “agent magic”
* Local-first and privacy-respecting by design

---

## Roadmap (High Level)

### Phase 0 — Stabilization (Current)

* Make the system start reliably
* Establish a single working execution path
* Remove false claims from code and docs
* Replace stubs with minimal implementations or remove them

### Phase 1 — Core Spine

* One CLI → Hestia → response loop
* Basic intent classification
* Explicit refusal paths
* Minimal memory persistence

### Phase 2 — Governance Enforcement

* Enforce invariants at choke points
* Wire permission checks
* Add real audit logging
* Introduce safe modes

### Phase 3 — Capability Expansion

* Reintroduce domain modules
* Harden memory lifecycle
* Add knowledge versioning
* Introduce bounded financial reasoning

---

## Security & Privacy Notice

⚠️ DO NOT USE THIS SYSTEM FOR REAL PERSONAL DATA.

* Data is currently stored in plaintext
* Encryption is not implemented
* Authentication is incomplete
* Safety claims are aspirational

This repository is for learning, experimentation, and system design, not real-world deployment.

---

## Intended Audience

This project is intended for:

* systems engineers
* AI safety researchers
* advanced students
* personal AI experimenters
* people interested in governed cognitive systems

It is not intended for casual users.

---

## License

This project is currently experimental.
License and usage terms may change as the system stabilizes.

---

## Final Note

This repository values honesty over hype.

If a feature is not implemented, it should be treated as nonexistent.
If a guarantee is not enforced in code, it should be treated as untrue.

That discipline is what will eventually make HEARTH worth using.

