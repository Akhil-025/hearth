import os
import re
from datetime import datetime
from collections import defaultdict, Counter
from hearth.core.memory_utils import load_memory

def generate_digest(save_to_file=True):
    memory = load_memory()
    notes = [e for e in memory if e.get("type") == "note"]

    if not notes:
        return "No notes found this week."

    # Group notes by date
    grouped = defaultdict(list)
    for note in notes:
        ts = datetime.fromisoformat(note["timestamp"])
        date_str = ts.strftime("%A, %d %B %Y")
        grouped[date_str].append((ts.strftime("%I:%M %p"), note["content"]))

    # Build digest body
    output = ["# Weekly Digest\n"]
    output.append("## Summary\n" + summarize_notes(notes) + "\n")

    for date, entries in sorted(grouped.items()):
        output.append(f"## {date}")
        for time_str, content in entries:
            output.append(f"- *{time_str}* — {content}")
        output.append("")

    digest_text = "\n".join(output)

    if save_to_file:
        folder = os.path.join(os.path.dirname(__file__), "..", "digests")
        os.makedirs(folder, exist_ok=True)
        filename = f"week-of-{datetime.now().strftime('%Y-%m-%d')}.md"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(digest_text)
        print(f"[Hestia] Digest saved to: {filepath}")

    return digest_text

def summarize_notes(notes):
    if not notes:
        return "No notes to summarize."

    texts = [n["content"] for n in notes]
    all_text = " ".join(texts)

    words = re.findall(r"\b\w+\b", all_text.lower())
    stopwords = {"the", "and", "to", "of", "a", "in", "is", "it", "i", "you", "that", "on", "for", "was", "with", "this", "but", "my", "at", "so"}
    keywords = [w for w in words if w not in stopwords and len(w) > 3]
    top_keywords = Counter(keywords).most_common(3)

    quote = max(texts, key=len)

    summary = [
        f"You logged {len(notes)} notes.",
        f"Top themes: {', '.join([kw for kw, _ in top_keywords])}.",
        f"Quote of the week: “{quote}”"
    ]

    return "\n".join(summary)
