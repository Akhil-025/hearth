import os
import json
from datetime import datetime, timedelta
from hearth.gamify.tracker import add_xp

STATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "state.json"))
MEMORY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "mnemosyne_memory.json"))
LEGACY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "mnemosyne_legacy.json"))


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def clean_memory():
    """Fix malformed notes in mnemosyne_memory.json and archive the rest."""
    if not os.path.exists(MEMORY_PATH):
        return "❌ No memory to clean."

    with open(MEMORY_PATH, "r") as f:
        try:
            entries = json.load(f)
        except json.JSONDecodeError:
            return "⚠️ Memory file is unreadable."

    valid = []
    legacy = []

    for e in entries:
        if isinstance(e, dict) and "note" in e:
            if "time" not in e:
                e["time"] = datetime.now().isoformat()
            if "source" not in e:
                e["source"] = "unknown"
            valid.append(e)
        else:
            legacy.append(e)

    save_json(MEMORY_PATH, valid)
    if legacy:
        save_json(LEGACY_PATH, legacy)
        return f"✅ Cleaned {len(valid)} entries. Archived {len(legacy)} broken entries."
    else:
        return f"✅ Memory cleaned. {len(valid)} entries valid."


def grant_journal_xp():
    return add_xp("Muse", 2)


def update_streak():
    state = load_json(STATE_PATH)
    today = datetime.now().date()

    last_date_str = state.get("last_journaled")
    streak = state.get("journal_streak", 0)

    if last_date_str:
        last_date = datetime.fromisoformat(last_date_str).date()
        if (today - last_date).days == 1:
            streak += 1
        elif (today - last_date).days > 1:
            streak = 1  # reset
    else:
        streak = 1

    state["last_journaled"] = today.isoformat()
    state["journal_streak"] = streak
    save_json(STATE_PATH, state)

    return f"🔥 Journal streak: {streak} day(s)"


def get_streak():
    state = load_json(STATE_PATH)
    return f"📅 Journal streak: {state.get('journal_streak', 0)} day(s)"


def run_all():
    return [
        clean_memory(),
        grant_journal_xp(),
        update_streak(),
    ]


def handle_mnemo_command(subcmd):
    if subcmd == "clean":
        return clean_memory()
    elif subcmd == "streak":
        return get_streak()
    elif subcmd == "upgrade":
        return "\n".join(run_all())
    else:
        return f"❓ Unknown mnemo command: {subcmd}"  
    


if __name__ == "__main__":
    for line in run_all():
        print(line)
