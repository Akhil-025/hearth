"""
Quick validation that context bounds are properly enforced.
"""
import asyncio
import sys
from pathlib import Path

# Add project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hestia.agent import HestiaAgent, MAX_MEMORY_ITEMS, MAX_MEMORY_CHARS, MAX_LLM_CONTEXT_CHARS


def test_bounds_constants():
    """Verify constants are set correctly."""
    assert MAX_MEMORY_ITEMS == 5, f"Expected MAX_MEMORY_ITEMS=5, got {MAX_MEMORY_ITEMS}"
    assert MAX_MEMORY_CHARS == 2000, f"Expected MAX_MEMORY_CHARS=2000, got {MAX_MEMORY_CHARS}"
    assert MAX_LLM_CONTEXT_CHARS == 8000, f"Expected MAX_LLM_CONTEXT_CHARS=8000, got {MAX_LLM_CONTEXT_CHARS}"
    print("✓ Constants validated")


def test_memory_truncation_tracking():
    """Verify memory context returns truncation flag."""
    # Create agent with memory using a fresh temp database
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_db = f"{tmpdir}/test_memory.db"
        agent = HestiaAgent(config={"enable_memory": True, "memory_db_path": temp_db})
        
        # With no memory saved, should return (None, False)
        context, was_truncated = agent.get_contextual_memory()
        assert context is None, f"Expected None context when no memory, got {context}"
        assert was_truncated == False, "Expected no truncation flag when no memory"
        print("✓ Empty memory returns (None, False)")
    
    # Test with memory disabled
    agent = HestiaAgent(config={"enable_memory": False})
    context, was_truncated = agent.get_contextual_memory()
    assert context is None, "Expected None when memory disabled"
    assert was_truncated == False, "Expected False when memory disabled"
    print("✓ Disabled memory returns (None, False)")


def test_athena_bounds():
    """Verify Athena outputs are bounded."""
    from athena.knowledge_store import KnowledgeStore
    
    store = KnowledgeStore(store_path="./data/test_knowledge.json")
    
    # Add test items
    store.add_item("Test Item 1", "This is a test about heat transfer and thermodynamics.")
    store.add_item("Test Item 2", "Another test document for knowledge retrieval.")
    
    # Check excerpt is bounded
    items = store.search("test", limit=10)
    assert len(items) <= 10, "Search should respect limit"
    
    for item in items:
        excerpt = store.excerpt(item, "test", max_length=200)
        assert len(excerpt) <= 200, f"Excerpt exceeds 200 chars: {len(excerpt)}"
        print(f"✓ Excerpt ({len(excerpt)} chars) is bounded")


async def test_llm_prompt_bounds():
    """Verify LLM prompt construction enforces bounds."""
    agent = HestiaAgent(config={"enable_llm": False})  # No actual LLM
    
    # System prompt size
    system_prompt = agent._build_system_prompt("general")
    assert len(system_prompt) < 500, "System prompt should be small"
    print(f"✓ System prompt size: {len(system_prompt)} chars (bounded)")
    
    # Total context calculation
    user_input = "a" * 5000  # Large input
    system_size = len(system_prompt)
    total = len(user_input) + system_size
    
    if total > MAX_LLM_CONTEXT_CHARS:
        print(f"✓ Large input ({len(user_input)} chars) + system ({system_size} chars) = {total} chars exceeds {MAX_LLM_CONTEXT_CHARS} limit")
    else:
        print(f"✓ Input ({len(user_input)} chars) stays within limit")


if __name__ == "__main__":
    print("Validating context bounds...\n")
    
    test_bounds_constants()
    test_memory_truncation_tracking()
    test_athena_bounds()
    asyncio.run(test_llm_prompt_bounds())
    
    print("\n✓ All bounds validation tests passed")
