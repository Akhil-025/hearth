import os
import json
from datetime import datetime
from hearth.modules.logger import notify
from hearth.modules.notifications import speak


MEMORY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mnemosyne_memory.json"))


def append_note(text, source="manual"):
    """Add a memory note with timestamp and optional source."""
    if not os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "w") as f:
            json.dump([], f)

    with open(MEMORY_PATH, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []

    timestamp = datetime.now().isoformat()
    entry = {
        "time": timestamp,
        "note": text,
        "source": source
    }
    data.append(entry)

    with open(MEMORY_PATH, "w") as f:
        json.dump(data, f, indent=2)

    return f"📝 Memory logged at {timestamp}"


def query_notes(limit=5):
    """Retrieve the most recent memory notes."""
    if not os.path.exists(MEMORY_PATH):
        return "No memory entries found."

    with open(MEMORY_PATH, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return "⚠️ Corrupt memory file."

    if not data:
        return "No memory entries yet."

    output = "🧠 Your Recent Memories:\n"
    valid = 0

    for entry in reversed(data):
        if "time" in entry and "note" in entry:
            output += f"[{entry['time']}] → {entry['note']}\n"
            valid += 1
        if valid >= limit:
            break

    if valid == 0:
        return "⚠️ No valid memory entries found."

    return output



def summarize_today():
    today = datetime.now().date()
    summary = []

    if not os.path.exists(MEMORY_PATH):
        return "No reflections recorded today."

    with open(MEMORY_PATH, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return "⚠️ Corrupt memory file."

    for entry in data:
        if "time" in entry and "note" in entry:
            try:
                ts = datetime.fromisoformat(entry["time"]).date()
                if ts == today:
                    summary.append(f"• {entry['note']}")
            except Exception:
                continue

    if not summary:
        return "No reflections recorded today."

    return "📘 Today's Reflections:\n" + "\n".join(summary)


def remind_to_reflect():
    notify("🧘 Time to reflect. What are you feeling right now?")


def main():
    print("🧠 Mnemosyne, Keeper of Memory. Type a note or 'recent' to review. Type 'exit' to quit.\n")
    speak("Mnemosyne, Keeper of Memory. Type a note or 'recent' to review. Type 'exit' to quit.", mode="introspect")
    while True:
        try:
            text = input("note> ").strip()
            if text.lower() in ("exit", "quit"):
                break
            elif text.lower() == "recent":
                print(query_notes())
            elif text.lower() == "today":
                print(summarize_today())
            else:
                print(append_note(text))
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
