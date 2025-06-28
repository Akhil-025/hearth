import os
from hearth.core.memory_utils import append_note
from hearth.sentience import reflection
from hearth.modules.notifications import speak

def main():
    speak("Hello, Akhil. I'm listening.", mode="introspect")
    print("✨ Hestia online. How can I help?")

    while True:
        try:
            cmd = input(">>> ").strip()

            if cmd in ("exit", "quit"):
                print("👋 Goodbye!")
                break

            elif cmd.startswith("log note "):
                content = cmd[len("log note "):].strip()
                append_note(content)
                speak("Got it. I’ve saved that note.", mode="introspect")

            elif cmd == "introspect":
                msg = reflection.introspect()
                speak(msg, mode="introspect")

            else:
                print("🤖 Unknown command.")

        except KeyboardInterrupt:
            print("\n👋 Exiting.")
            break

if __name__ == "__main__":
    main()
