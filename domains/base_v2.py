"""
HEARTH Domain Interface (v0.2)

Minimal, read-only reasoning modules.

Interface:
    domain.handle(query: str) -> str

Constraints:
    - Return strings only (no side effects)
    - Never write memory
    - Never call other domains
    - Never plan or execute actions
    - Deterministic responses
"""

from abc import ABC, abstractmethod


class Domain(ABC):
    """Abstract base class for HEARTH domains.
    
    Domains are read-only reasoning modules that:
    - Take a query string
    - Return a string response
    - Perform no side effects
    - Cannot access memory, knowledge, or other domains
    - Cannot plan or execute actions
    """

    @abstractmethod
    def handle(self, query: str) -> str:
        """Process a query and return a reasoning response.
        
        Args:
            query: User query or request string
            
        Returns:
            str: Domain response (reasoning, suggestions, insights)
            
        Constraints:
            - Must return string only
            - Must be deterministic (same input → same output)
            - Must not write memory
            - Must not call other domains
            - Must not have side effects
        """
        pass
