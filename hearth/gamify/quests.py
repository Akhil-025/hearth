import os
import json
from hearth.modules.notifications import speak, chime_on_success

QUEST_FILE = os.path.join(os.path.dirname(__file__), "quests.json")

def load_quests():
    if not os.path.exists(QUEST_FILE):
        return {"daily": [], "weekly": []}
    with open(QUEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_quests(data):
    with open(QUEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def list_quests():
    data = load_quests()
    lines = ["📜 Quest Log:"]
    for qtype in ["daily", "weekly"]:
        quests = data.get(qtype, [])
        lines.append(f"\n✨ {qtype.capitalize()} Quests:")
        if quests:
            for q in quests:
                status = "✅" if q.get("done") else "🔸"
                lines.append(f"{status} {q['name']} (+{q['xp']} XP → {q['stat']})")
        else:
            lines.append("(none)")
    return "\n".join(lines)

def complete_quest(name):
    data = load_quests()
    found = False
    for group in data.values():
        for q in group:
            if q["name"].lower() == name.lower():
                if q.get("done"):
                    return f"⚠️ Quest already completed: {name}"
                q["done"] = True
                found = True
                save_quests(data)
                speak(f"Quest '{q['name']}' completed. Glory to {q['stat']}.", mode="introspect")
                chime_on_success()
                return f"✅ Marked as done: {q['name']} (+{q['xp']} XP to {q['stat']})"
    return f"❌ Quest not found: {name}"

def reset_quests():
    data = load_quests()
    for group in data.values():
        for q in group:
            q["done"] = False
    save_quests(data)
    speak("All quests have been reset.", mode="introspect")
    return "🔄 All quests reset. Ready for a new cycle."

def quest_help():
    return """
📘 QUEST COMMANDS

🔹 quest: list
    → View all active quests.

🔹 quest: complete "Quest Name"
    → Mark a quest as completed and gain XP.

🔹 quest: reset
    → Reset all quest completion statuses.

🔹 quest: help
    → Show this help message.
"""

def handle_quest_command(cmd):
    if cmd == "list":
        msg = list_quests()
        speak("Here are your current divine tasks.", mode="introspect")
        return msg
    elif cmd.startswith("complete "):
        name = cmd[len("complete "):].strip('" ')
        return complete_quest(name)
    elif cmd == "reset":
        return reset_quests()
    elif cmd == "help":
        return quest_help()
    else:
        return f"❓ Unknown quest command: {cmd}"


def trigger_price_alert_quest(triggered_alerts):
    for cat, symbol in triggered_alerts:
        print(f"🎯 Quest progress: Alert triggered for {cat}:{symbol}")
