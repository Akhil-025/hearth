import os
import subprocess
import sys
import json
import shlex
from datetime import datetime

from hearth.core.memory_utils import append_note
from hearth.sentience import reflection
from hearth.modules.notifications import speak
from hearth.sentience.digest import generate_digest

MEMORY_FILE = "known_apps.json"

COMMANDS = [
    {"command": "exit / quit", "description": "Exit the Hestia assistant."},
    {"command": "log note [text]", "description": "Save a memory note."},
    {"command": "digest", "description": "Get current day's reflection digest."},
    {"command": "weekly", "description": "Generate past week's summary."},
    {"command": "introspect", "description": "Self-reflect based on past notes."},
    {"command": "launch [app] [target]", "description": "Launch app or open link."},
    {"command": "teach launch [name] path/url/shell [value]", "description": "Teach Hestia how to launch a new app or site."},
    {"command": "show [app]", "description": "View saved details of an app."},
    {"command": "list apps", "description": "List all known apps."},
    {"command": "forget [app]", "description": "Forget how to launch a specific app."},
    {"command": "rename [old] to [new]", "description": "Rename an app in memory."},
    {"command": "help", "description": "Show all available commands."},
]


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
                for cmd_info in COMMANDS:
                    print(f"🔹 {cmd_info['command']}\n    → {cmd_info['description']}\n")
                speak("Here’s everything I can do, neatly listed.", mode="introspect")


            else: print("🤖 Unknown command.")

            

        except KeyboardInterrupt: 
            print("\n👋 Exiting.") 
            break

if __name__ == "__main__":
    main()
