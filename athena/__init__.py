"""
Athena - Knowledge base subsystem for HEARTH.

Explicit, read-only vector search. Intent-gated activation.
No LLM calls, no memory writes, no side effects.
"""

from .service import AthenaService

__all__ = ["AthenaService"]
