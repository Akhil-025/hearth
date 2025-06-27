import time
import os
from hearth.modules.logger import log_note

def main():
    print("✨ Hestia online. How can I help?")
    while True:
        try:
            cmd = input(">>> ").strip()
            if cmd in ("exit", "quit"):
                print("👋 Goodbye!")
                break
            elif cmd.startswith("log note"):
                note = cmd[len("log note"):].strip()
                log_note(note)
            else:
                print("🤖 Unknown command.")
        except KeyboardInterrupt:
            print("\n👋 Exiting.")
            break

if __name__ == "__main__":
    main()
