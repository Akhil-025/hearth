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
    
    async def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify intent using simple keyword matching.
        
        Returns:
            Dict with intent and confidence
        """
        text_lower = text.lower().strip()
        
        # Check for explicit memory query patterns FIRST
        for pattern in self.memory_patterns:
            if pattern in text_lower:
                return {
                    "intent": "memory_query",
                    "confidence": 0.9,
                    "method": "pattern_match"
                }
        
        # Check for keyword matches
        for keyword, intent in self.keyword_map.items():
            if keyword in text_lower:
                return {
                    "intent": intent,
                    "confidence": 0.8,
                    "method": "keyword_match"
                }
        
        # Default fallback
        return {
            "intent": "general",
            "confidence": 0.5,
            "method": "fallback"
        }
