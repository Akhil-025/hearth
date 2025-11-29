import json
import os
from datetime import datetime

BASE_PATH = os.path.dirname(__file__)
STATS_FILE = os.path.join(BASE_PATH, "stats.json")
LEVELS_FILE = os.path.join(BASE_PATH, "levels.json")
DECAY_FILE = os.path.join(BASE_PATH, "decay_config.json")
QUESTS_FILE = os.path.join(BASE_PATH, "quests.json")


def ensure_json_file(path, default_data):
    if not os.path.exists(path) or os.stat(path).st_size == 0:
        with open(path, "w") as f:
            json.dump(default_data, f, indent=2)

def self_heal():
    ensure_json_file(STATS_FILE, {
        "xp": 0,
        "level": 1,
        "next_level": 120,
        "core": {
            "Vitalis": 20,
            "Fortuna": 15,
            "Sophia": 25,
            "Charis": 18,
            "Daemonia": 22,
            "Arete": 24
        },
        "skills": {
            "Aetherlink": 10,
            "Chronosurge": 12,
            "Argentum Tact": 8,
            "Ignis Stamina": 9,
            "Echocraft": 11,
            "Kyros Gaze": 7,
            "Nyx Veil": 10
        },
        "last_updated": datetime.now().strftime("%Y-%m-%d")
    })

    ensure_json_file(LEVELS_FILE, [
        {
            "level": 1,
            "xp_required": 0,
            "title": "Flameborn Acolyte",
            "perks": ["Habit tracking enabled"],
            "stat_caps": {"Vitalis": 50, "Fortuna": 50, "Sophia": 50, "Charis": 50, "Daemonia": 50, "Arete": 50}
        },
        {
            "level": 2,
            "xp_required": 120,
            "title": "Scribe of Mnemosyne",
            "perks": ["Mood tracking unlocked", "Journaling synergy bonuses"],
            "stat_caps": {"Vitalis": 60, "Fortuna": 60, "Sophia": 60, "Charis": 60, "Daemonia": 60, "Arete": 60}
        },
        {
            "level": 3,
            "xp_required": 280,
            "title": "Initiate of Plutus",
            "perks": ["Wealth quests unlocked", "Argentum Tact XP tracking"],
            "stat_caps": {"Vitalis": 65, "Fortuna": 70, "Sophia": 70, "Charis": 65, "Daemonia": 65, "Arete": 70}
        },
        {
            "level": 4,
            "xp_required": 500,
            "title": "Disciple of Chronos",
            "perks": ["Time rituals unlocked", "Chronosurge XP tracking"],
            "stat_caps": {"Vitalis": 70, "Fortuna": 75, "Sophia": 75, "Charis": 70, "Daemonia": 75, "Arete": 75}
        },
        {
            "level": 5,
            "xp_required": 800,
            "title": "Seeker of Aetherion",
            "perks": ["Skill synergy unlocked", "Combo XP blending"],
            "stat_caps": {"Vitalis": 80, "Fortuna": 80, "Sophia": 85, "Charis": 75, "Daemonia": 85, "Arete": 85}
        }
    ])

    ensure_json_file(DECAY_FILE, {
        "core": {
            "Vitalis": 0.5,
            "Fortuna": 0.3,
            "Sophia": 0.7,
            "Charis": 0.4,
            "Daemonia": 0.6,
            "Arete": 0.5
        },
        "skills": {
            "Aetherlink": 0.8,
            "Chronosurge": 1.0,
            "Argentum Tact": 0.6,
            "Ignis Stamina": 1.2,
            "Echocraft": 0.9,
            "Kyros Gaze": 0.5,
            "Nyx Veil": 0.7
        }
    })

    ensure_json_file(QUESTS_FILE, {
        "daily": [
            {"name": "Drink 2L Water", "xp": 5, "stat": "Vitalis", "done": False},
            {"name": "Read 10 Pages", "xp": 7, "stat": "Sophia", "done": False},
            {"name": "Log Mood", "xp": 4, "stat": "Daemonia", "done": False}
        ],
        "weekly": [
            {"name": "Invest in Market", "xp": 15, "stat": "Fortuna", "done": False},
            {"name": "Write Reflection", "xp": 10, "stat": "Echocraft", "done": False},
            {"name": "Workout 3 Times", "xp": 12, "stat": "Ignis Stamina", "done": False}
        ]
    })
