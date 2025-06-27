import os
import time

DATA_PATH = os.path.expandvars(r"%APPDATA%\.hearth\notes.txt")

def log_note(note):
    if not note:
        print("⚠️ No note provided.")
        return
    with open(DATA_PATH, "a", encoding="utf-8") as f:
        f.write(f"{time.ctime()}: {note}\n")
    print("📝 Logged!")

def notify(message):
    print(f"[NOTIFY] {message}")
