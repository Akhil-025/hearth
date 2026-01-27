"""
Athena Knowledge Store - Minimal, synchronous, read-only lookup.

Design goals for v0.1:
- Plain JSON storage
- No embeddings, no ranking, no inference
- Human-readable and inspectable
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4


@dataclass
class KnowledgeItem:
    id: str
    title: str
    content: str
    source: str = "manual_import"
    timestamp: str = datetime.now().isoformat()


class KnowledgeStore:
    """Minimal read-only knowledge store backed by a JSON file."""

    def __init__(self, store_path: str = "./data/knowledge.json"):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._items: List[KnowledgeItem] = []
        self._load()

    def _load(self) -> None:
        if not self.store_path.exists():
            self._items = []
            return
        try:
            with self.store_path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
                self._items = [KnowledgeItem(**item) for item in raw if self._is_valid_item(item)]
        except Exception:
            # Fail closed: if load fails, operate with empty store
            self._items = []

    @staticmethod
    def _is_valid_item(item: dict) -> bool:
        required_keys = {"id", "title", "content", "source", "timestamp"}
        return isinstance(item, dict) and required_keys.issubset(item.keys())

    def add_item(self, title: str, content: str, source: str = "manual_import") -> KnowledgeItem:
        """Append a new knowledge item to disk (utility for manual population)."""
        item = KnowledgeItem(id=str(uuid4()), title=title, content=content, source=source, timestamp=datetime.now().isoformat())
        self._items.append(item)
        self._persist()
        return item

    def _persist(self) -> None:
        with self.store_path.open("w", encoding="utf-8") as f:
            json.dump([asdict(item) for item in self._items], f, ensure_ascii=True, indent=2)

    def search(self, query: str, limit: int = 5) -> List[KnowledgeItem]:
        """Simple keyword search over title or content (case-insensitive)."""
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        matches = []
        for item in self._items:
            if query_lower in item.title.lower() or query_lower in item.content.lower():
                matches.append(item)
            if len(matches) >= limit:
                break
        return matches

    def excerpt(self, item: KnowledgeItem, query: str, max_length: int = 200) -> str:
        """Return a short excerpt without summarization."""
        content_lower = item.content.lower()
        query_lower = query.lower()
        idx = content_lower.find(query_lower)
        if idx == -1:
            return item.content[:max_length].strip()

        start = max(0, idx - 60)
        end = min(len(item.content), idx + len(query) + 60)
        snippet = item.content[start:end]
        return snippet.replace("\n", " ")[:max_length].strip()
