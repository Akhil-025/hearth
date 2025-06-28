from hearth.core.memory_utils import load_memory
from datetime import datetime

def introspect():
    memory = load_memory()
    notes = [e for e in memory if e.get("type") == "note"]

    if not notes:
        return "You’ve been quiet. No notes formed yet."

    last = notes[-1]  # ✅ Grab the last logged note

    ts = datetime.fromisoformat(last["timestamp"])  # 👈 Your line goes right here
    readable_time = ts.strftime("%A, %d %B at %I:%M %p")

    return f"On {readable_time}, you said: “{last['content']}”. Want to reflect more deeply?"
