"""
Message Planner - Drafts messages for various contexts.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


class MessageType(Enum):
    """Types of messages."""
    EMAIL = "email"
    CHAT = "chat"
    FORMAL = "formal"
    INFORMAL = "informal"
    BUSINESS = "business"
    PERSONAL = "personal"


class MessagePurpose(Enum):
    """Purposes for messages."""
    REQUEST = "request"
    INFORM = "inform"
    NEGOTIATE = "negotiate"
    APOLOGIZE = "apologize"
    THANK = "thank"
    FOLLOW_UP = "follow_up"
    INTRODUCE = "introduce"


class MessageTemplate:
    """Message template with placeholders."""
    
    def __init__(self, template_type: MessageType, purpose: MessagePurpose):
        self.template_type = template_type
        self.purpose = purpose
        self.templates = self._load_templates()
    
    def _load_templates(self) -> List[str]:
        """Load templates based on type and purpose."""
        # Simplified template database
        templates = {
            (MessageType.EMAIL, MessagePurpose.REQUEST): [
                "Dear {recipient},\n\nI hope this message finds you well. I'm writing to {key_points}.\n\n{constraints}\n\nBest regards,\n{sender}",
                "Hello {recipient},\n\nI wanted to reach out about {key_points}. {constraints}\n\nLooking forward to your response.\n\nSincerely,\n{sender}"
            ],
            (MessageType.CHAT, MessagePurpose.INFORM): [
                "Hey {recipient}, just wanted to let you know: {key_points}",
                "{recipient}, quick update: {key_points}"
            ],
            (MessageType.FORMAL, MessagePurpose.THANK): [
                "Dear {recipient},\n\nI want to express my sincere gratitude for {key_points}.\n\n{constraints}\n\nWith appreciation,\n{sender}",
            ],
        }
        
        return templates.get((self.template_type, self.purpose), [
            "{recipient},\n\n{key_points}\n\n{constraints}\n\n{sender}"
        ])


class MessagePlanner:
    """
    Plans and drafts messages based on context.
    
    Rules:
    - No AI generation (rule-based only)
    - No personal data inference
    - Multiple draft options
    """
    
    def __init__(self):
        self.templates = {}
        self._initialize_templates()
    
    def _initialize_templates(self) -> None:
        """Initialize message templates."""
        for msg_type in MessageType:
            for purpose in MessagePurpose:
                key = (msg_type, purpose)
                self.templates[key] = MessageTemplate(msg_type, purpose)
    
    def generate_drafts(
        self,
        message_type: str,
        recipient: str,
        purpose: str,
        key_points: List[str],
        constraints: List[str] = None,
        previous_context: Optional[str] = None,
        sender: str = "User"
    ) -> List[Dict[str, any]]:
        """
        Generate multiple message drafts.
        
        Returns structured drafts with metadata.
        """
        # Parse enums
        try:
            msg_type = MessageType(message_type)
            msg_purpose = MessagePurpose(purpose)
        except ValueError:
            # Default to email/request if invalid
            msg_type = MessageType.EMAIL
            msg_purpose = MessagePurpose.REQUEST
        
        # Get templates
        template_key = (msg_type, msg_purpose)
        template_obj = self.templates.get(template_key)
        
        if not template_obj:
            # Fallback template
            templates = ["{recipient},\n\n{key_points}\n\n{constraints}\n\n{sender}"]
        else:
            templates = template_obj.templates
        
        # Prepare content
        key_points_text = self._format_key_points(key_points, msg_type)
        constraints_text = self._format_constraints(constraints or [])
        
        # Generate drafts
        drafts = []
        for i, template in enumerate(templates[:3]):  # Max 3 drafts
            draft_id = str(uuid4())
            
            # Fill template
            content = template.format(
                recipient=recipient,
                key_points=key_points_text,
                constraints=constraints_text,
                sender=sender,
                context=previous_context or ""
            )
            
            # Clean up empty sections
            content = self._clean_content(content)
            
            drafts.append({
                "draft_id": draft_id,
                "content": content,
                "version": i + 1,
                "characteristics": self._analyze_draft(content, msg_type),
                "suggested_use": self._suggest_use_case(content, msg_type, msg_purpose)
            })
        
        return drafts
    
    def _format_key_points(self, key_points: List[str], msg_type: MessageType) -> str:
        """Format key points based on message type."""
        if msg_type in [MessageType.CHAT, MessageType.INFORMAL]:
            # Concise format
            return " • " + "\n • ".join(key_points)
        else:
            # Formal format
            return "\n\n".join([f"{i+1}. {point}" for i, point in enumerate(key_points)])
    
    def _format_constraints(self, constraints: List[str]) -> str:
        """Format constraints."""
        if not constraints:
            return ""
        
        constraint_text = "Additional considerations:\n"
        for constraint in constraints:
            constraint_text += f"- {constraint}\n"
        
        return constraint_text.strip()
    
    def _clean_content(self, content: str) -> str:
        """Clean up template artifacts."""
        # Remove empty lines with only formatting
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip lines that are only template placeholders
            if stripped and not stripped.startswith("{") and not stripped.endswith("}"):
                cleaned_lines.append(line)
            elif stripped:  # Non-empty placeholder line
                cleaned_lines.append("")  # Add blank line
        
        # Remove multiple consecutive blank lines
        result = []
        prev_blank = False
        for line in cleaned_lines:
            is_blank = not line.strip()
            if not (prev_blank and is_blank):
                result.append(line)
            prev_blank = is_blank
        
        return '\n'.join(result).strip()
    
    def _analyze_draft(self, content: str, msg_type: MessageType) -> Dict[str, any]:
        """Analyze draft characteristics."""
        words = content.split()
        sentences = content.split('.')
        
        return {
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "avg_sentence_length": len(words) / max(len(sentences), 1),
            "formality_level": self._calculate_formality(content, msg_type),
            "readability_score": self._calculate_readability(content),
            "key_elements_present": self._check_elements(content, msg_type)
        }
    
    def _calculate_formality(self, content: str, msg_type: MessageType) -> float:
        """Calculate formality score (0-1)."""
        # Simple heuristic based on word choices and structure
        formal_words = {"sincerely", "regards", "dear", "respectfully", "please", "thank you"}
        informal_words = {"hey", "hi", "thanks", "cheers", "ok", "got it"}
        
        words = set(content.lower().split())
        
        formal_count = len(formal_words.intersection(words))
        informal_count = len(informal_words.intersection(words))
        
        total = formal_count + informal_count
        if total == 0:
            return 0.5  # Neutral
        
        formality = formal_count / total
        
        # Adjust by message type
        type_adjustment = {
            MessageType.FORMAL: 0.3,
            MessageType.BUSINESS: 0.2,
            MessageType.EMAIL: 0.1,
            MessageType.PERSONAL: -0.1,
            MessageType.INFORMAL: -0.2,
            MessageType.CHAT: -0.3
        }
        
        formality += type_adjustment.get(msg_type, 0)
        return max(0.0, min(1.0, formality))
    
    def _calculate_readability(self, content: str) -> float:
        """Simple readability score (higher = more readable)."""
        # Flesch Reading Ease approximation
        words = content.split()
        sentences = [s for s in content.split('.') if s.strip()]
        
        if not words or not sentences:
            return 0.5
        
        avg_words_per_sentence = len(words) / len(sentences)
        avg_syllables_per_word = self._estimate_syllables(words)
        
        # Simplified Flesch: 206.835 - 1.015*(words/sentence) - 84.6*(syllables/word)
        # Normalized to 0-1
        flesch = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
        
        # Normalize: 0-30 = difficult, 30-50 = fairly difficult, 50-60 = standard,
        # 60-70 = fairly easy, 70-80 = easy, 80-90 = very easy, 90-100 = very very easy
        normalized = max(0.0, min(1.0, flesch / 100.0))
        return normalized
    
    def _estimate_syllables(self, words: List[str]) -> float:
        """Estimate average syllables per word."""
        vowel_groups = {'a', 'e', 'i', 'o', 'u', 'y'}
        total_syllables = 0
        
        for word in words[:100]:  # Sample first 100 words
            word_lower = word.lower().strip(".,!?;:")
            if not word_lower:
                continue
            
            # Simple syllable counting
            syllables = 0
            prev_is_vowel = False
            
            for char in word_lower:
                is_vowel = char in vowel_groups
                if is_vowel and not prev_is_vowel:
                    syllables += 1
                prev_is_vowel = is_vowel
            
            # Adjust for common patterns
            if syllables == 0:
                syllables = 1
            if word_lower.endswith(('es', 'ed')):
                syllables = max(1, syllables - 1)
            
            total_syllables += syllables
        
        return total_syllables / max(len(words), 1)
    
    def _check_elements(self, content: str, msg_type: MessageType) -> Dict[str, bool]:
        """Check for required message elements."""
        checks = {
            "has_greeting": any(greeting in content.lower() for greeting in 
                              ["dear", "hello", "hi", "hey", "to"]),
            "has_closing": any(closing in content.lower() for closing in
                             ["sincerely", "regards", "best", "thanks", "cheers"]),
            "has_clear_points": len([s for s in content.split('.') if len(s.split()) > 3]) > 0,
            "has_contact_info": any(info in content for info in 
                                   ["@", "phone", "email", "call"]),
            "has_action_items": any(action in content.lower() for action in
                                  ["please", "could you", "would you", "let me know"])
        }
        
        # Adjust expectations by message type
        if msg_type in [MessageType.CHAT, MessageType.INFORMAL]:
            checks["has_greeting"] = True  # Less strict
            checks["has_closing"] = True   # Less strict
        
        return checks
    
    def _suggest_use_case(self, content: str, msg_type: MessageType, purpose: MessagePurpose) -> str:
        """Suggest when to use this draft."""
        word_count = len(content.split())
        
        if word_count < 50:
            length_desc = "brief"
        elif word_count < 200:
            length_desc = "moderate"
        else:
            length_desc = "detailed"
        
        formality = self._calculate_formality(content, msg_type)
        
        if formality > 0.7:
            style = "formal"
        elif formality > 0.4:
            style = "balanced"
        else:
            style = "casual"
        
        return f"{length_desc} {style} message for {purpose.value}"