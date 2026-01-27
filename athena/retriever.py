"""
Athena retriever - synchronous, explicit lookups only.
"""
from __future__ import annotations

from typing import List, Dict

from .knowledge_store import KnowledgeStore, KnowledgeItem


class AthenaRetriever:
	"""Simple keyword-based retriever over the knowledge store."""

	def __init__(self, store: KnowledgeStore | None = None):
		self.store = store or KnowledgeStore()

	def search(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
		items = self.store.search(query, limit=limit)
		results: List[Dict[str, str]] = []
		for item in items:
			excerpt = self.store.excerpt(item, query)
			results.append({
				"id": item.id,
				"title": item.title,
				"excerpt": excerpt,
				"source": item.source,
				"timestamp": item.timestamp
			})
		return results
