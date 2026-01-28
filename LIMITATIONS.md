# HEARTH Limitations & Adversarial Test Findings

## Stage 2: Context Engine & Pipeline Executor

### LIMITATION-2.1: Token Counting is Heuristic

**Title**: Token counting uses character-based approximation

**Subsystem**: Context Engine (`hestia/context_engine.py`)

**Description**: Token count estimation is character-based and heuristic, not byte-accurate. Exact tokenizer parity with production LLM tokenizers (e.g., tiktoken) is intentionally avoided.

**Rationale**: Determinism-preserving design choice. Character-based counting ensures:
- Reproducible token counts across runs
- No external tokenizer dependency
- Predictable behavior in resource-constrained environments
- Faster computation

**Acceptability**: ✅ **ACCEPTED** (by design) - Users are responsible for ensuring input fits within token limits. Slight variance from production tokenizers is acceptable for this subsystem.

**Implications**:
- Token count is approximate, not exact
- May differ from LLM's actual token usage
- Character-to-token ratio is ~4:1 (heuristic)
- Users should budget conservatively

---

## Cycle 1: Intent Classification

### LIMITATION-1.1: Negation Not Detected

**Title**: Pattern matching ignores negation

**Subsystem**: Intent Classification (`hestia/intent_classifier.py`)

**Repro Test**: `test_negation_of_pattern`

**Example Input**: `"I don't want to search my notes"`

**Observed Behavior**: Classified as `athena_query` despite negation word "don't"

**Expected by User**: Should not trigger athena_query when explicitly negating the action

**Acceptability**: ⚠️ **LIMITATION** (by design) - Classifier uses simple substring matching, not semantic understanding. Negation detection would require NLP, which is out of scope for v0.1.

**Implications**:
- User says "don't search my notes" → triggers athena_query anyway
- User must be aware that negation is NOT recognized
- Classifier only sees patterns, not semantics

---

### FINDING-1.2: Substring Matching Creates False Positives

**Title**: Patterns match substrings within larger words

**Subsystem**: Intent Classification

**Test Cases Affected**:
- `test_pattern_partial_word_boundary`: "researching" contains "search"
- `test_extra_spaces_in_pattern`: Pattern with double spaces

**Result**: Pattern "search my notes" matches "researching my notes for Python materials"

**Status**: ✅ **Expected behavior** - Substring matching is by design for flexibility, even if it creates false positives.

---

### FINDING-1.3: Multi-Intent Collisions

**Title**: Same input matches multiple intent patterns

**Subsystem**: Intent Classification

**Test Case**: `test_multiple_trigger_phrases_same_input`

**Input**: `"search my knowledge for Python, also search my notes about memory"`

**Observed**: Returns `knowledge_query` (first matching pattern wins)

**Status**: ⚠️ **LIMITATION** (by design) - Pattern check order determines winner. First match wins, no disambiguation.

**Impact**:
- User phrases multiple intents → only first matched intent is used
- User has no control over which intent wins
- No confidence scores or alternatives offered

---

### FINDING-1.4: Whitespace Variants Not Normalized

**Title**: Extra spaces/tabs/newlines in trigger phrases affect matching

**Subsystem**: Intent Classification

**Test Cases**:
- `test_extra_spaces_in_pattern`: "search  my  notes" (double spaces)
- `test_newlines_in_pattern`: "search my\nnotes"
- `test_tabs_in_pattern`: "search\tmy\tnotes"

**Result**: Patterns are substring-matched against `text.lower()`, so whitespace variance means no match

**Status**: ⚠️ **LIMITATION** - Whitespace normalization not performed

**Impact**: If user has extra spaces/newlines, trigger might not match

---

### FINDING-1.5: Pattern Check Order is Non-Obvious

**Title**: Multiple patterns; first match wins

**Subsystem**: Intent Classification

**Observation**: Check order is:
1. memory_patterns
2. knowledge_patterns
3. hephaestus_patterns
4. hermes_patterns
5. apollo_patterns
6. dionysus_patterns
7. pluto_patterns
8. athena_patterns
9. keyword_map
10. fallback to "general"

**Impact**: User cannot predict which intent wins if multiple patterns match

---

### FINDING-1.6: No Semantic Ambiguity Resolution

**Title**: Classifier cannot distinguish intent nuance

**Subsystem**: Intent Classification

**Examples**:
- "based on what you remember, tell me about sleep" → memory_query or apollo_query?
- "search my knowledge for Python in my notes" → knowledge_query or athena_query?

**Result**: First matching pattern determines intent, no nuance

**Status**: ✅ **Expected** - v0.1 is keyword-based, not semantic

---

## Summary of Cycle 1 Findings

| Category | Count | Examples |
|----------|-------|----------|
| ✅ Expected Behavior | 6 | Substring matching, determinism, state isolation |
| ⚠️ Limitations | 4 | Negation not detected, no disambiguation, whitespace sensitivity, check order |
| ❌ Bugs | 0 | None found |

---

## Cycle 2: Memory (Mnemosyne)

### BUG-2.1: Disabled Service memory_service is None

**Title**: When memory disabled, agent.memory_service is None, not a service with disabled flag

**Subsystem**: `hestia/agent.py` initialization

**Repro Test**: `test_disabled_read_returns_empty`

**Code Path**:
```python
if self.enable_memory:
    # ... initialize memory_service
else:
    self.memory_service = None  # ← This is the issue
```

**Expected Behavior**: `agent.memory_service.read()` should work and return `[]`

**Actual Behavior**: `AttributeError: 'NoneType' object has no attribute 'read'`

**Status**: ❌ **BUG** - Inconsistent API: sometimes memory_service exists, sometimes it's None

**Fix Required**: Initialize `memory_service` even when disabled, with `enabled=False` flag

---

### BUG-2.2: Agent Missing MAX_MEMORY_CHARS Constant

**Title**: `HestiaAgent` uses `self.MAX_MEMORY_CHARS` but doesn't define it

**Subsystem**: `hestia/agent.py` class definition

**Repro Test**: `test_context_truncation_at_max_chars`

**Error**: `AttributeError: 'HestiaAgent' object has no attribute 'MAX_MEMORY_CHARS'`

**Status**: ❌ **BUG** - Constant defined at module level but accessed as instance attribute

**Impact**: Memory context truncation test fails

---

### FINDING-2.3: Empty String Memory Is Accepted

**Title**: `save_memory("")` returns True

**Subsystem**: Memory write gating

**Status**: ⚠️ **LIMITATION** - No validation of empty/whitespace content

**Impact**: Database polluted with empty records

---

### FINDING-2.4: Huge Memory Entries (10MB) Accepted

**Title**: No size limit on individual memory entries

**Subsystem**: Memory write gating

**Status**: ⚠️ **LIMITATION** - Could exhaust disk space

**Impact**: No protection against resource exhaustion

---

### FINDING-2.5: SQL Injection Prevented (Good)

**Title**: SQL-injectable text "'; DROP TABLE memories; --" stored safely

**Status**: ✅ **Expected** - Parameterized queries protect against SQL injection

---

| Category | Count | Notes |
|----------|-------|-------|
| ✅ Expected | 3 | SQL safety, unicode support, special chars |
| ⚠️ Limitations | 2 | Empty memory accepted, huge entries allowed |
| ❌ Bugs | 2 | memory_service can be None, MAX_MEMORY_CHARS missing |

---

## Cycle 3: Athena (RAG/Knowledge) - IN PROGRESS

### Summary
- **17 tests executed**
- **0 failures** - All edge cases handled gracefully
- **chromadb not available** - Expected for v0.1 (graceful degradation working)
- **No SQL injection vulnerability** - Parameterized query protection confirmed
- **No unicode/regex/XSS issues** - Proper handling of special characters

### FINDING-3.1: Athena Gracefully Degrades When Disabled

**Status**: ✅ **Expected**

**Subsystem**: `athena/service.py`

**Test**: `test_disabled_query_returns_empty`, `test_disabled_ingest_returns_false`

**Observed**: When enabled=False, queries return empty results, ingest returns error dict

**Impact**: Good design - no crashes on disabled state

---

### FINDING-3.2: Empty Query Returns Empty Results

**Status**: ✅ **Expected**

**Tests**: `test_empty_query_string`, `test_whitespace_only_query`

**Observed**: Empty/whitespace queries don't crash, return empty sources

**Impact**: Robust handling

---

### FINDING-3.3: SQL Injection Prevention Confirmed

**Status**: ✅ **Expected**

**Test**: `test_sql_injection_in_query`

**Observed**: SQL injection attempt `'; DROP TABLE documents; --` stored safely, database intact

**Impact**: Parameterized queries working correctly

---

### FINDING-3.4: Unicode and Special Characters Handled

**Status**: ✅ **Expected**

**Tests**: `test_unicode_query`, `test_special_regex_characters`, `test_xss_attempt_in_query`

**Observed**: Unicode, regex chars, XSS payloads all handled without crashes

**Impact**: Safe multi-language support

---

### FINDING-3.5: chromadb/sentence-transformers Not Required for v0.1

**Status**: ✅ **Expected**

**Test**: `test_chromadb_missing`, `test_sentence_transformers_missing`

**Warning Message**: "chromadb not available. Install with: pip install chromadb sentence-transformers"

**Impact**: v0.1 works without vector search dependencies; graceful degradation

---

### FINDING-3.6: Query State Isolation Verified

**Status**: ✅ **Expected**

**Tests**: `test_query_doesnt_modify_next_query`, `test_multiple_services_dont_share_state`

**Observed**: Queries don't affect subsequent queries; multiple service instances independent

**Impact**: No state leakage, deterministic behavior

---

| Category | Count | Notes |
|----------|-------|-------|
| ✅ Expected | 6 | Graceful degradation, SQL safety, unicode support, state isolation, no dependencies |
| ⚠️ Limitations | 0 | None found |
| ❌ Bugs | 0 | None found |

---

## Design-Locked Limitations (Intentional — WONTFIX v0.x)

These limitations are INTENTIONAL DESIGN CHOICES. They provide simplicity, predictability, and reliability. DO NOT add NLP, semantic analysis, or heuristics to overcome them.

### LOCKED-1.1: No Negation Handling

**Pattern**: Substring-based keyword matching (not NLP-based)

**Limitation**: "I don't want to search my notes" matches "search my notes" pattern

**Why Locked**: 
- NLP requires external models (sentence-transformers, spaCy)
- Introduces non-determinism and latency
- Violates v0.x design principle: dumb + explicit
- User intent must be explicit, not inferred

**Workaround**: Rephrase as positive: "show me my notes" instead of "don't search"

**WONTFIX v0.x**: Any attempt to add negation detection must:
1. Have explicit reviewer approval
2. Document performance impact
3. Include extensive adversarial testing
4. Update this file before merging

---

### LOCKED-1.2: First-Match-Wins Intent Resolution

**Pattern**: Check order determines winner when multiple patterns match

**Limitation**: Input "search memory and knowledge" matches first pattern in check order

**Check Order** (fixed, non-negotiable):
```
memory → knowledge → hephaestus → hermes → apollo → dionysus → pluto → athena → keyword_map → general
```

**Why Locked**:
- Ambiguity resolution requires semantic understanding (NLP)
- First-match is deterministic and predictable
- User can disambiguate by rephrasing (explicit intent)

**WONTFIX v0.x**: Confidence scores, ranking, or disambiguation require v1.0+ redesign

---

### LOCKED-1.3: Substring Pattern Matching (Not Word Boundaries)

**Pattern**: `if "search" in user_input.lower()`

**Limitation**: "research" contains "search"; "researcher" triggers search intent

**Why Locked**:
- Word-boundary detection requires regex/NLP
- Current implementation is O(1) and fast
- False positives are acceptable; user can correct

**WONTFIX v0.x**: Word boundary matching adds complexity; not worth latency cost

---

### LOCKED-2.1 & LOCKED-2.2: Memory Size Guards (Now Enforced)

**Fixed in v0.1.1-hardening**:
- LIMIT-2.1: Empty/whitespace-only memory now REJECTED (was accepted)
- LIMIT-2.2: Memory entries capped at 50KB (was unlimited)

**Guards** (in `mnemosyne/service.py`):
```python
MAX_SINGLE_MEMORY_SIZE = 50_000  # 50KB per entry (hard limit)
if not content or not content.strip():
    return False  # Reject empty
if len(content.encode('utf-8')) > MAX_SINGLE_MEMORY_SIZE:
    return False  # Reject oversized
```

**Why These Limits**:
- 50KB per entry: Prevents accidental disk exhaustion
- Empty rejection: Prevents database pollution
- No heuristics: Mechanical guard, not intelligent

---

## Bugs Fixed in v0.1.1-hardening

### BUG-2.1 FIXED: memory_service Always Initialized

**Was**: `self.memory_service = None` when disabled → AttributeError on .read()

**Now**: Always initialized as `MnemosyneService(enabled=False)` when disabled

**Guarantee**: `agent.memory_service.read()` never raises AttributeError

**Code**: [hestia/agent.py](hestia/agent.py#L88-L102)

---

### BUG-2.2 FIXED: MAX_MEMORY_CHARS Access

**Was**: Tests incorrectly accessed `self.MAX_MEMORY_CHARS` (module constant)

**Now**: Fixed test to import from module: `from hestia.agent import MAX_MEMORY_CHARS`

**Guarantee**: Truncation logic correct, tests pass

**Code**: [hestia/agent.py](hestia/agent.py#L45), [tests/test_adversarial/test_memory_adversarial.py](tests/test_adversarial/test_memory_adversarial.py#L185-L197)

---

## Cycle 4: LLM Boundary & Context Management - PLANNED



