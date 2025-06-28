from hearth.sentience.digest import generate_digest
from hearth.core.memory_utils import load_memory
from hearth.sentience.digest import summarize_notes  # ✅ Now safe to import

if __name__ == "__main__":
    print("[Hestia] Generating weekly digest...")

    notes = [e for e in load_memory() if e.get("type") == "note"]  # ✅ Define notes here
    summary_text = summarize_notes(notes)
    print(summary_text)

    generate_digest(save_to_file=True)
