"""
HEARTH Intent Classifier - Minimal Stub (v0.1)

DISABLED IN v0.1:
- LLM-based classification
- Complex intent parsing
- Confidence scoring
"""
from typing import Dict, Any


class IntentClassifier:
    """
    Minimal intent classifier using keyword matching.
    
    FUTURE: Will use LLM for semantic understanding.
    """
    
    def __init__(self):
        # Simple keyword → intent mapping
        self.keyword_map = {
            "hello": "greeting",
            "hi": "greeting",
            "help": "help_request",
            "what": "question",
            "how": "question",
            "why": "question",
            "tell": "information_request",
        }
        
        # Memory query patterns (explicit user requests)
        self.memory_patterns = [
            "what do you remember",
            "show my memories",
            "show memories",
            "what have i told you",
            "list memories",
            "my memories",
            "remember about me",
            "show my recent memories",
            "recent memories"
        ]

        # Knowledge query patterns (explicit user requests)
        self.knowledge_patterns = [
            "search my knowledge for",
            "look up in my knowledge base",
            "find documents about",
            "what notes do i have on",
            "search my knowledge base",
            "search knowledge for",
            "search knowledge base",
            "find knowledge about"
        ]
        
        # Hephaestus domain patterns (code reasoning, debugging, design)
        self.hephaestus_patterns = [
            "debug",
            "design",
            "refactor",
            "review",
            "code",
            "architecture",
            "error",
            "crash",
            "improve",
            "clean",
            "best practice",
        ]
        
        # Hermes domain patterns (text transformation, communication)
        self.hermes_patterns = [
            "rewrite",
            "rephrase",
            "summarize",
            "simplify",
            "clearer",
            "make this clear",
            "make it clear",
        ]
        
        # Apollo domain patterns (health/fitness/wellness information)
        self.apollo_patterns = [
            "health",
            "fitness",
            "exercise",
            "nutrition",
            "sleep",
            "wellbeing",
            "body",
            "physiology",
        ]
        
        # Dionysus domain patterns (music/art/culture/entertainment information)
        self.dionysus_patterns = [
            "music",
            "song",
            "genre",
            "art",
            "culture",
            "party",
            "fun",
            "vibe",
            "entertainment",
        ]
        
        # Pluto domain patterns (financial/economic concepts information)
        self.pluto_patterns = [
            "money",
            "finance",
            "financial",
            "economics",
            "economy",
            "wealth",
            "asset",
            "liability",
            "budget",
            "risk",
        ]
    
    def classify(self, text: str) -> str:
        """
        Classify intent using simple keyword matching.
        
        Returns:
            str: Intent name (memory_query, knowledge_query, hephaestus_query, general, etc.)
        """
        text_lower = text.lower().strip()
        
        # Check for explicit memory query patterns FIRST
        for pattern in self.memory_patterns:
            if pattern in text_lower:
                return "memory_query"

        # Check for explicit knowledge search patterns
        for pattern in self.knowledge_patterns:
            if pattern in text_lower:
                return "knowledge_query"
        
        # Check for Hephaestus domain patterns (code reasoning)
        for pattern in self.hephaestus_patterns:
            if pattern in text_lower:
                return "hephaestus_query"
        
        # Check for Hermes domain patterns (text transformation)
        for pattern in self.hermes_patterns:
            if pattern in text_lower:
                return "hermes_query"
        
        # Check for Apollo domain patterns (health/wellness information)
        for pattern in self.apollo_patterns:
            if pattern in text_lower:
                return "apollo_query"
        
        # Check for Dionysus domain patterns (music/art/culture information)
        for pattern in self.dionysus_patterns:
            if pattern in text_lower:
                return "dionysus_query"
        
        # Check for Pluto domain patterns (financial/economic concepts information)
        for pattern in self.pluto_patterns:
            if pattern in text_lower:
                return "pluto_query"
        
        # Check for keyword matches
        for keyword, intent in self.keyword_map.items():
            if keyword in text_lower:
                return intent
        
        # Default fallback
        return "general"
