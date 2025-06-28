import os
import json
from datetime import datetime

MEMORY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mnemosyne_memory.json"))

def load_memory():
    print(f"[DEBUG] Looking for memory here: {MEMORY_FILE}")
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except json.JSONDecodeError:
        print("[Hestia] Warning: memory file is unreadable.")
    return []

def append_note(content):
    entry = {
        "type": "note",
        "content": content,
        "timestamp": datetime.now().isoformat()
    }

    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump([entry], f, indent=2)
    else:
        with open(MEMORY_FILE, "r+", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
