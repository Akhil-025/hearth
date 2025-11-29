import json
import os
from datetime import datetime, timedelta

BASE_PATH = os.path.join(os.path.dirname(__file__))
STATS_FILE = os.path.join(BASE_PATH, "stats.json")
LEVELS_FILE = os.path.join(BASE_PATH, "levels.json")
DECAY_FILE = os.path.join(BASE_PATH, "decay_config.json")

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_level_config(xp):
    levels = load_json(LEVELS_FILE)
    for lvl in reversed(levels):
        if xp >= lvl["xp_required"]:
            return lvl
    return levels[0]

def get_level_status():
    stats = load_json(STATS_FILE)
    level_info = get_level_config(stats["xp"])
    return f"🧙 You are at Level {level_info['level']} — {level_info['title']}\nXP: {stats['xp']} / {stats['next_level']}\nPerks: {', '.join(level_info['perks'])}"

def apply_stat_caps(stats, level_info):
    for stat, cap in level_info["stat_caps"].items():
        stats["core"][stat] = min(stats["core"].get(stat, 0), cap)
    return stats

def add_xp(stat, amount):
    stats = load_json(STATS_FILE)
    levels = load_json(LEVELS_FILE)

    # Update stat
    if stat in stats["core"]:
        stats["core"][stat] = stats["core"].get(stat, 0) + amount
    elif stat in stats["skills"]:
        stats["skills"][stat] = stats["skills"].get(stat, 0) + amount
    else:
        return f"⚠️ Unknown stat: {stat}"

    stats["xp"] += amount

    # Level Up Check
    for lvl in levels:
        if stats["xp"] < lvl["xp_required"]:
            break
        stats["level"] = lvl["level"]
        stats["next_level"] = lvl["xp_required"]

    # Cap enforcement
    stats = apply_stat_caps(stats, get_level_config(stats["xp"]))

    stats["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    save_json(STATS_FILE, stats)

    return f"✅ Added {amount} XP to {stat}. New value: {stats['core'].get(stat, stats['skills'].get(stat, 0))}"

def decay_stats():
    stats = load_json(STATS_FILE)
    decay = load_json(DECAY_FILE)
    today = datetime.now().date()
    last = datetime.strptime(stats["last_updated"], "%Y-%m-%d").date()
    days_passed = (today - last).days

    if days_passed <= 0:
        return "No decay needed today."

    for stat, rate in decay["core"].items():
        stats["core"][stat] = max(0, stats["core"][stat] - rate * days_passed)

    for skill, rate in decay["skills"].items():
        stats["skills"][skill] = max(0, stats["skills"][skill] - rate * days_passed)

    stats["last_updated"] = today.strftime("%Y-%m-%d")
    save_json(STATS_FILE, stats)
    return f"🌒 Decayed over {days_passed} day(s). Stay sharp."

def get_status():
    stats = load_json(STATS_FILE)
    level = get_level_config(stats["xp"])
    bar = lambda val, cap: "█" * int(val / cap * 10) + "-" * (10 - int(val / cap * 10))
    out = f"🎮 Level {level['level']} — {level['title']}\nXP: {stats['xp']} / {stats['next_level']}\n\n"
    out += "📊 Core Stats:\n"
    for stat, val in stats["core"].items():
        cap = level["stat_caps"].get(stat, 100)
        out += f"• {stat:<10}: [{bar(val, cap)}] {int(val)}/{cap}\n"
    return out

def get_skills():
    stats = load_json(STATS_FILE)
    out = "🧪 Skill Stats:\n"
    for skill, val in stats["skills"].items():
        out += f"• {skill:<14}: {int(val)} XP\n"
    return out

def get_core_stats():
    return load_json(STATS_FILE)["core"]

def get_last_decay():
    stats = load_json(STATS_FILE)
    return stats.get("last_updated", "unknown")

def get_stat_value(stat):
    stats = load_json(STATS_FILE)
    if stat in stats["core"]:
        return stats["core"][stat]
    if stat in stats["skills"]:
        return stats["skills"][stat]
    return None

def track_help():
    return (
        "📜 Track Commands:\n"
        "• track: [StatName] +N     → Add XP to stat\n"
        "• track: status            → Show core stats + level\n"
        "• track: skills            → Show skill XP\n"
        "• track: decay             → Apply daily XP decay\n"
        "• track: help              → Show this help message\n"
        "\n🔮 Stats are capped by level. XP decays daily unless earned.\n"
        "✨ Use ‘Arete’, ‘Vitalis’, ‘Nyx Veil’, etc. for Greek-flavored glory!"
    )
