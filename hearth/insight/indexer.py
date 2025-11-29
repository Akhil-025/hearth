import os
import json
import re
from datetime import datetime

COMMANDS_PATH = os.path.join(os.path.dirname(__file__), "commands_reference.json")
CHANGELOG_PATH = os.path.join(os.path.dirname(__file__), "command_changelog.json")

CATEGORY_KEYWORDS = {
    "📝 Journaling": ["log note", "digest", "weekly", "introspect", "mnemo"],
    "🎮 Life Tracking": ["track", "decay", "level", "status", "skills", "daily ritual"],
    "🎯 Quests": ["quest", "complete quest", "reset quests", "show quests"],
    "💰 Wealth": ["log wealth", "plutus"],
    "📦 Backup & Restore": ["backup"],
    "🧠 System & Meta": ["help", "launch", "teach", "forget", "rename", "exit", "echo"]
}

DESC_MAP = {
    "log note": "Save a memory entry to Mnemosyne.",
    "digest": "Daily reflection digest.",
    "weekly": "Weekly journaling summary.",
    "introspect": "AI reflection based on memory logs.",
    "track:": "Add XP to skills or stats, or view status.",
    "decay now": "Apply XP/stat decay based on time.",
    "level up?": "Show current level, XP, and perks.",
    "status": "Show current XP and stat bars.",
    "skills": "List XP of all skill stats.",
    "daily ritual": "Run decay + quests for the day.",
    "quest:": "Manage your quests (view, reset, complete).",
    "complete quest": "Finish a quest and earn XP.",
    "reset quests": "Reset all daily or weekly quests.",
    "show quests": "List all current quests.",
    "log wealth": "Log income and gain XP.",
    "backup:": "Manage backups (tag, restore, encrypt).",
    "help": "Show all available commands.",
    "launch": "Launch an app or website.",
    "teach": "Teach Hestia how to launch something.",
    "forget": "Forget a previously known app.",
    "rename": "Rename an app memory.",
    "exit": "Exit the Hestia assistant.",
    "echo": "Debug command."
}

def extract_commands_with_regex(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    pattern_startswith = re.findall(r'cmd\.startswith\(["\'](.+?)["\']\)', code)
    pattern_equals = re.findall(r'cmd\s*==\s*["\'](.+?)["\']', code)

    commands = []

    for cmd in pattern_startswith:
        commands.append({"command": cmd + "...", "description": "[dynamic subcommand]"})

    for cmd in pattern_equals:
        commands.append({"command": cmd, "description": "TODO: Add description."})

    unique = {c['command']: c for c in commands}.values()
    return sorted(unique, key=lambda x: x["command"])

def inject_descriptions(commands):
    updated = []
    for cmd in commands:
        for key in DESC_MAP:
            if cmd["command"].startswith(key):
                cmd["description"] = DESC_MAP[key]
                break
        else:
            cmd["description"] = "Miscellaneous or user-defined command."
        updated.append(cmd)
    return updated

def categorize_commands(commands):
    categorized = {k: [] for k in CATEGORY_KEYWORDS}
    uncategorized = []
    for cmd in commands:
        found = False
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(cmd["command"].startswith(k) for k in keywords):
                categorized[cat].append(cmd)
                found = True
                break
        if not found:
            uncategorized.append(cmd)
    return categorized, uncategorized

def save_changelog(new_commands):
    existing = []
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r") as f:
            existing = json.load(f)
    known = {entry["command"] for entry in existing}
    now = datetime.now().strftime("%Y-%m-%d")
    for cmd in new_commands:
        if cmd["command"] not in known:
            existing.append({"command": cmd["command"], "date": now, "type": "added", "desc": cmd["description"]})
    with open(CHANGELOG_PATH, "w") as f:
        json.dump(existing, f, indent=2)

def generate_commands(hestia_py_path):
    raw = extract_commands_with_regex(hestia_py_path)
    enriched = inject_descriptions(raw)
    save_changelog(enriched)
    return enriched

def export_commands_json(commands, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(commands, f, indent=2)

def load_command_reference():
    if os.path.exists(COMMANDS_PATH):
        with open(COMMANDS_PATH, "r") as f:
            return json.load(f)
    return []

def load_changelog():
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r") as f:
            return json.load(f)
    return []
