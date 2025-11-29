import os
import subprocess
import sys
import json
import shlex
from datetime import datetime
from hearth.gamify.tracker import (add_xp, get_status, decay_stats, get_skills, get_level_status)
from hearth.gamify.quests import (list_quests, complete_quest,reset_quests)
from hearth.gamify.auto_heal import self_heal
from hearth.core.memory_utils import append_note
from hearth.sentience import reflection
from hearth.modules.notifications import speak
from hearth.sentience.digest import generate_digest
from hearth.cli.plutus import daily_ritual, log_wealth
from hearth.gamify.backup import run_backup
from hearth.gamify.backup import run_backup, restore_backup, list_backups, restore_latest, purge_backups_keep, describe_backup
from hearth.modules.notifications import chime_on_success
from hearth.gamify.quests import handle_quest_command
from hearth.mnemo_upgrade import handle_mnemo_command
from hearth.insight.indexer import generate_commands, export_commands_json
from hearth.modules.command_indexer import generate_commands,export_commands_json, load_command_reference, categorize_commands
from hearth.modules import alerts


SOURCE_FILE = os.path.abspath(__file__)
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "modules", "commands_reference.json")
export_commands_json(generate_commands(SOURCE_FILE), OUTPUT_PATH)
COMMANDS = load_command_reference()


MEMORY_FILE = "known_apps.json"

def main():
    speak("Hello, Akhil. I'm listening.", mode="introspect")
    print("✨ Hestia online. How can I help?")

    while True:
        try:
            cmd = input(">>> ").strip()

            if cmd.lower() in ("exit", "quit"):
                now = datetime.now().hour
                if now < 5:
                    farewell = "Rest well, night owl. I'll be here when the sun's up."
                elif now < 12:
                    farewell = "Goodbye, Akhil. Have a peaceful morning ahead."
                elif now < 17:
                    farewell = "Goodbye, Akhil. Let the afternoon treat you kindly."
                elif now < 21:
                    farewell = "Goodbye, Akhil. Take time to reflect this evening."
                else:
                    farewell = "Good night, Akhil. Sleep easy, I'll remember everything."

                try:
                    speak(farewell, mode="introspect")
                except Exception as e:
                    print(f"(Couldn’t speak farewell: {e})")
                print("👋 " + farewell)
                break

            
            elif cmd.lower().startswith("launch "):
                parts = shlex.split(cmd)
                app = parts[1].lower()
                target = parts[2] if len(parts) > 2 else None

                print(f"[DEBUG] known_apps.json path: {os.path.abspath(MEMORY_FILE)}")
                with open(MEMORY_FILE, "r") as f:
                    known_apps = json.load(f)

                print(f"[DEBUG] known_apps keys: {list(known_apps.keys())}")
                print(f"[DEBUG] looking for: '{app}'")

                entry = known_apps.get(app)
                if entry:
                    mode = entry.get("mode", "path")
                    path = entry.get("path")
                    args = entry.get("args", [])[:]

                    if target:
                        if not target.startswith("http"):
                            target = "https://" + target
                        args.append(target)

                    try:
                        if mode == "path":
                            cwd_path = os.path.dirname(path)
                            cwd = cwd_path if cwd_path and os.path.exists(cwd_path) else None

                            print(f"[DEBUG] Launching: {[path, *args]}")
                            print(f"[DEBUG] cwd: {cwd}")

                            if not os.path.exists(path):
                                speak(f"The file path for {app} doesn’t seem to exist.", mode="alert")
                                print(f"🚫 File not found: {path}")
                                continue

                            subprocess.Popen([path, *args], cwd=cwd)

                        elif mode == "shell":
                            subprocess.Popen([path, *args], shell=True)
                        else:
                            raise ValueError(f"Unknown launch mode: {mode}")

                        # Log timestamp and memory note
                        entry["last_launched"] = datetime.now().isoformat()
                        append_note(f"Launched {app}{' with ' + target if target else ''}")
                        known_apps[app] = entry
                        with open(MEMORY_FILE, "w") as f:
                            json.dump(known_apps, f, indent=2)

                        speak(f"Launching {app}{' with ' + target if target else ''}.", mode="introspect")

                    except Exception as e:
                        speak(f"Something went wrong while launching {app}.", mode="alert")
                        print(f"🚨 Launch error: {e}")
                else:
                    speak("🙅 I don’t know that app yet.", mode="introspect")
                    print("🙅 I don’t know that app yet. You can teach me by updating known_apps.")


            elif cmd.lower().startswith("teach launch "):
                try:
                    parts = shlex.split(cmd)

                    if len(parts) < 5:
                        speak("That teach command is missing some information.", mode="alert")
                        print("⚠️ Usage: teach launch <name> <mode> <path or AppID or URL>")
                        continue

                    _, _, name, mode = parts[:4]
                    rest = parts[4:]

                    if mode.lower() == "path":
                        path = rest[0]
                        args = rest[1:]
                    elif mode.lower() == "shell":
                        path = "cmd"
                        args = ["/c", "start", "", f"shell:AppsFolder\\{' '.join(rest)}"]
                    elif mode.lower() == "url":
                        path = "cmd"
                        args = ["/c", "start", "", ' '.join(rest)]
                    else:
                        speak(f"Sorry, I don't recognize mode '{mode}'.", mode="alert")
                        continue

                    if not os.path.exists(MEMORY_FILE):
                        with open(MEMORY_FILE, "w") as f:
                            json.dump({}, f)

                    print(f"[DEBUG] saving known_apps.json to: {os.path.abspath(MEMORY_FILE)}")
                    with open(MEMORY_FILE, "r") as f:
                        known_apps = json.load(f)

                    known_apps[name.lower()] = {
                        "mode": mode.lower(),
                        "path": path,
                        "args": args
                    }

                    with open(MEMORY_FILE, "w") as f:
                        json.dump(known_apps, f, indent=2)

                    speak(f"I’ve learned how to launch {name}.", mode="introspect")
                    print(f"✅ Hestia can now launch '{name}' using mode '{mode}'.")

                except Exception as e:
                    speak("Sorry, I couldn’t learn that command.", mode="alert")
                    print(f"🚨 Teach error: {e}")

            elif cmd.lower().startswith("show "):
                app = cmd.split(maxsplit=1)[1].lower()
                if app == "skills":
                    print(get_skills())
                    speak("Displaying skill stats.", mode="introspect")
                    continue  # ✅ prevents further app handling

                elif app == "quests":
                    print(list_quests())
                    speak("Here are your current quests.", mode="introspect")
                    continue

                elif app == "status":
                    print(get_status())
                    speak("Here’s your current life status.", mode="introspect")
                    continue

                print(f"[DEBUG] known_apps.json path: {os.path.abspath(MEMORY_FILE)}")
                with open(MEMORY_FILE, "r") as f:
                    known_apps = json.load(f)
                if app in known_apps:
                    print(f"\n🔎 {app} config:")
                    print(json.dumps(known_apps[app], indent=2))
                else:
                    print(f"🙅 Hestia doesn't know an app named '{app}'.")

            elif cmd.lower() == "list apps":
                print(f"[DEBUG] known_apps.json path: {os.path.abspath(MEMORY_FILE)}")
                with open(MEMORY_FILE, "r") as f:
                    known_apps = json.load(f)
                print("\n🧠 Hestia knows how to launch:")
                for name in sorted(known_apps.keys()):
                    print(f"• {name}")

            elif cmd.lower().startswith("forget "):
                app = cmd.split(maxsplit=1)[1].lower()
                with open(MEMORY_FILE, "r") as f:
                    known_apps = json.load(f)
                if app in known_apps:
                    del known_apps[app]
                    with open(MEMORY_FILE, "w") as f:
                        json.dump(known_apps, f, indent=2)
                    speak(f"I've forgotten how to launch {app}.", mode="introspect")
                    print(f"❌ Hestia no longer remembers '{app}'.")
                else:
                    print(f"🙅 Hestia doesn't know an app named '{app}'.")

            elif cmd.lower().startswith("rename "):
                try:
                    parts = cmd.lower().split()
                    if len(parts) == 4 and parts[2] == "to":
                        old_name = parts[1]
                        new_name = parts[3]
                        with open(MEMORY_FILE, "r") as f:
                            known_apps = json.load(f)
                        if old_name in known_apps:
                            if new_name in known_apps:
                                print(f"⚠️ An app named '{new_name}' already exists.")
                            else:
                                known_apps[new_name] = known_apps.pop(old_name)
                                with open(MEMORY_FILE, "w") as f:
                                    json.dump(known_apps, f, indent=2)
                                speak(f"I’ve renamed {old_name} to {new_name}.", mode="introspect")
                                print(f"✏️ Renamed '{old_name}' → '{new_name}'.")
                        else:
                            print(f"🙅 I don’t know any app called '{old_name}'.")
                    else:
                        print("⚠️ Usage: rename <old_name> to <new_name>")
                except Exception as e:
                    speak("Sorry, I couldn’t rename that.", mode="alert")
                    print(f"🚨 Rename error: {e}")

            elif cmd.startswith("log note "):
                content = cmd[len("log note "):].strip()
                append_note(content)
                speak("Got it. I’ve saved that note.", mode="introspect")

            elif cmd == "introspect":
                msg = reflection.introspect()
                speak(msg, mode="introspect")

            elif cmd.lower() == "digest":
                print("🧠 Generating reflection digest...")
                try:
                    summary = generate_digest()
                    print("\n📘 Reflection Digest:\n" + summary)
                    speak("Here’s your current", mode="introspect") 
                except Exception as e: print(f"🚨 Digest error: {e}") 
                speak("Sorry, I couldn't generate the reflection digest.", mode="alert")

            elif cmd.lower() == "weekly": 
                print("📆 Gathering this week's activity...") 
                try:
                    summary = generate_digest() 
                    print("\n🗓️ Weekly Reflection:\n" + summary) 
                    speak("Here's a summary of our past week together.", mode="introspect")                     
                except Exception as e: print(f"🚨 Weekly digest error: {e}") 
                speak("Sorry, I couldn't generate the weekly reflection.", mode="alert")

            elif cmd.lower() == "help":
                print("\n📘 HESTIA COMMAND REFERENCE\n")

                try:
                        from hearth.modules.command_indexer import load_command_reference, categorize_commands
                        commands = load_command_reference()
                        categorized, uncategorized = categorize_commands(commands)

                        for cat, cmds in categorized.items():
                            if cmds:
                                print(f"{cat}")
                                for c in cmds:
                                    print(f"🔹 {c['command']}\n    → {c['description']}\n")
                        if uncategorized:
                            print("📂 Uncategorized")
                            for c in uncategorized:
                                print(f"🔹 {c['command']}\n    → {c['description']}\n")

                except Exception as e:
                    print("⚠️ Help system failed:", e)


            elif cmd.startswith("track "):
                try:
                    _, stat, change = cmd.split()
                    value = int(change)
                    result = add_xp(stat, value)
                    print(result)
                    speak(f"{stat} increased by {value} XP.", mode="introspect")
                except Exception as e:
                    print(f"⚠️ Couldn't track XP: {e}")

            elif cmd.startswith("track: "):
                track_cmd = cmd[len("track: "):].strip().lower()

                if track_cmd == "status":
                    print(get_status())
                elif track_cmd == "skills":
                    print(get_skills())
                elif track_cmd == "decay":
                    print(decay_stats())
                elif "+" in track_cmd:
                    try:
                        stat, amount = track_cmd.split("+")
                        stat = stat.strip().capitalize()
                        amount = int(amount.strip())
                        print(add_xp(stat, amount))
                    except Exception as e:
                        print(f"⚠️ Invalid track command: {e}")
                else:
                    print("⚠️ Unknown track command. Use 'track: status', 'track: skills', 'track: [stat] +N', or 'track: decay'")


            elif cmd == "level up?":
                print(get_level_status())

            elif cmd == "decay now":
                print(decay_stats())
                speak("Decay applied.", mode="introspect")

            elif cmd == "show quests":
                print(list_quests())
                speak("Here are your current quests.", mode="introspect")

            elif cmd.startswith("complete quest "):
                name = cmd[len("complete quest "):].strip()
                result = complete_quest(name)
                print(result)
                speak("Quest processed.", mode="introspect")

            elif cmd.startswith("reset quests "):
                typ = cmd[len("reset quests "):].strip()
                result = reset_quests(typ)
                print(result)
                speak("Quest board refreshed.", mode="introspect")

            elif cmd.startswith("log wealth "):
                try:
                    amt = float(cmd.split(" ")[2])
                    print(log_wealth(amt))
                    speak("Wealth recorded.", mode="introspect")
                except Exception as e:
                    print(f"⚠️ Error logging wealth: {e}")
            
            elif cmd == "daily ritual":
                print(daily_ritual())
                speak("Daily sync complete.", mode="introspect")
            
            elif cmd.lower() == "help: refresh":
                export_commands_json(generate_commands(SOURCE_FILE), OUTPUT_PATH)
                print("✅ Command reference refreshed.")
                speak("Help system refreshed.", mode="introspect")



# ── 🧠 Backup & Restore Commands ─────────────────────────

            elif cmd.startswith("backup: "):
                parts = cmd[len("backup: "):].strip().split(" ", 1)
                action = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if action == "now":
                    msg = run_backup()
                    print(msg)
                    speak("Scrolls backed up successfully.", mode="introspect")
                    chime_on_success()

                elif action == "encrypted":
                    msg = run_backup(encrypted=True)
                    print(msg)
                    speak("Encrypted backup sealed with divine flame.", mode="introspect")
                    chime_on_success()

                elif action == "tag":
                    tag = arg.strip('" ')
                    msg = run_backup(tag=tag)
                    print(msg)
                    speak(f"Backup inscribed as {tag}.", mode="introspect")
                    chime_on_success()

                elif action == "restore":
                    date = arg.strip()
                    msg = restore_backup(date)
                    print(msg)
                    speak(f"Restored memory from {date}.", mode="introspect")
                    chime_on_success()

                elif action == "latest":
                    msg = restore_latest()
                    print(msg)
                    speak("The most recent backup has been summoned.", mode="introspect")
                    chime_on_success()

                elif action == "list":
                    msg = list_backups()
                    print(msg)
                    speak("Here are all stored seals of time.", mode="introspect")
                    chime_on_success()

                elif action == "describe":
                    date = arg.strip()
                    msg = describe_backup(date)
                    print(msg)
                    speak(f"Exploring the scrolls of {date}.", mode="introspect")
                    chime_on_success()

                elif action == "purge":
                    try:
                        n = int(arg.strip())
                        msg = purge_backups_keep(n)
                        print(msg)
                        speak(f"All but the latest {n} seals have been burned.", mode="introspect")
                        chime_on_success()
                    except ValueError:
                        print("⚠️ Invalid number.")
                        speak("That wasn't a valid number.", mode="alert")

                elif action == "help":
                    msg = """
                        📦 BACKUP COMMANDS

                        🔹 backup: now
                            → Create a normal backup in today's folder.

                        🔹 backup: encrypted
                            → Create a password-encrypted zipped backup.

                        🔹 backup: tag "label"
                            → Create a named backup. Example: backup: tag "before exams"

                        🔹 backup: restore [date]
                            → Restore from a specific folder. Example: backup: restore 2025-07-14

                        🔹 backup: latest
                            → Restore the most recent backup.

                        🔹 backup: list
                            → View all stored backups.

                        🔹 backup: describe [date]
                            → See the contents of a backup folder.

                        🔹 backup: purge N
                            → Delete all but the most recent N backups.
                        """
                    print(msg)
                    speak("Here are all backup rituals I know.", mode="introspect")
                    chime_on_success()


                else:
                    print(f"❓ Unknown backup command: {action}")
                    speak("I do not recognize that backup ritual.", mode="alert")

# ── 🧠 Backup & Restore Commands ─────────────────────────
                

            elif cmd.startswith("quest: "):
                sub = cmd[len("quest: "):].strip()
                print(handle_quest_command(sub))

            elif cmd.startswith("mnemo: "):
                subcmd = cmd[len("mnemo: "):].strip()
                print(handle_mnemo_command(subcmd))

            elif cmd == "echo test":
                print("Yayayayaya")
            
            elif cmd == "alerts: check":
                alerts.check_price_alerts()

            elif cmd.startswith("alerts: add"):
                parts = cmd.split()
                if len(parts) == 5:
                    _, _, category, symbol, threshold_str = parts
                    try:
                        threshold = float(threshold_str)
                        alerts.add_alert(category, symbol, threshold)
                    except ValueError:
                        print("❌ Threshold must be a number.")
                else:
                    print("Usage: alerts: add [crypto|stocks] [symbol] [threshold]")

            elif cmd == "alerts: list":
                alerts.list_alerts()

            elif cmd == "alerts: clear":
                alerts.clear_alerts()

            elif cmd == "alerts: show-prices":
                 alerts.show_prices()


            else: print("🤖 Unknown command.")

            

        except KeyboardInterrupt: 
            print("\n👋 Exiting.") 
            break

if __name__ == "__main__":
    main()
