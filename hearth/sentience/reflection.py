from hearth.core.memory_utils import load_memory

def introspect():
    memory = load_memory()
    print(f"[DEBUG] Loaded memory: {memory}")

    notes = [e for e in memory if e.get("type") == "note"]
    print(f"[DEBUG] Filtered notes: {notes}")

    if not notes:
        return "You’ve been quiet. No notes formed yet."

    last_note = notes[-1]["content"]
    return f"Your last thought was: “{last_note}”. Want to reflect more deeply?"
