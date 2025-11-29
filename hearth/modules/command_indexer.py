# hearth/modules/command_indexer.py — enhanced with lower().startswith() detection and override fallback

import os
import json
import re
from datetime import datetime

COMMANDS_PATH = os.path.join(os.path.dirname(__file__), "commands_reference.json")
CHANGELOG_PATH = os.path.join(os.path.dirname(__file__), "command_changelog.json")
OVERRIDES_PATH = os.path.join(os.path.dirname(__file__), "desc_overrides.json")

CATEGORY_KEYWORDS = {
    "📝 Journaling": ["log note", "digest", "weekly", "introspect", "mnemo"],
    "🎮 Life Tracking": ["track", "decay", "level", "status", "skills", "daily ritual"],
    "🎯 Quests": ["quest", "complete quest", "reset quests", "show quests"],
    "💰 Wealth": ["log wealth", "plutus"],
    "📦 Backup & Restore": ["backup"],
    "🧠 System & Meta": ["help", "launch", "teach", "forget", "rename", "exit", "echo"]
}

def extract_commands_with_comments(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    lines = code.split("\n")
    commands = []
    comment_buffer = ""

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            comment_buffer = stripped.lstrip("# ")
            continue

        match_start = re.search(r'(cmd(\.lower\(\))?)\.startswith\(["\'](.+?)["\']\)', stripped)
        if match_start:
            command = match_start.group(3) + "..."
            commands.append({"command": command, "description": comment_buffer or "[dynamic subcommand]"})
            comment_buffer = ""
            continue

        match_eq = re.search(r'cmd\s*==\s*["\'](.+?)["\']', stripped)
        if match_eq:
            command = match_eq.group(1)
            commands.append({"command": command, "description": comment_buffer or "TODO: Add description."})
            comment_buffer = ""
            continue

    unique = {c['command']: c for c in commands}.values()
    return sorted(unique, key=lambda x: x["command"])

def inject_override_descriptions(commands):
    if os.path.exists(OVERRIDES_PATH):
        with open(OVERRIDES_PATH, "r") as f:
            overrides = json.load(f)
        for c in commands:
            if c["command"] in overrides:
                c["description"] = overrides[c["command"]]
    return commands



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
    raw = extract_commands_with_comments(hestia_py_path)
    enriched = inject_override_descriptions(raw)
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
