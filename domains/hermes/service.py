"""
Hermes Domain (v0.2)

Text transformation and communication clarity.

Triggered by keywords:
- "rewrite"
- "rephrase"
- "summarize"
- "simplify"
- "make this clearer"

Characteristics:
- Pure deterministic transformations (no LLM, no randomness)
- No memory writes
- No autonomy or planning
- No cross-domain calls
- No advice or opinions (transformation only)
"""

from ..base_v2 import Domain


class HermesService(Domain):
    """Text transformation and communication domain.
    
    Provides:
    - Rewriting text for different purposes
    - Rephrasing for clarity
    - Summarization techniques
    - Simplification strategies
    - Clarity improvements
    
    All responses are deterministic template-based guidance
    with no external dependencies (no LLM, no memory).
    
    IMPORTANT: Does NOT perform actual transformations.
    Returns guidance/templates for how to transform text.
    """

    # Transformation guidance templates (deterministic)
    REWRITE_PATTERNS = {
        "formal": "To rewrite formally: Remove contractions, use complete sentences, avoid colloquialisms, use professional vocabulary.",
        "casual": "To rewrite casually: Use contractions, shorter sentences, conversational tone, simple vocabulary.",
        "technical": "To rewrite technically: Use precise terminology, include specifications, add technical details, maintain objectivity.",
        "concise": "To rewrite concisely: Remove redundant words, use active voice, combine related sentences, eliminate filler phrases.",
        "persuasive": "To rewrite persuasively: Lead with benefits, use strong action words, include evidence/examples, create urgency.",
    }

    REPHRASE_PATTERNS = {
        "active": "To use active voice: Move subject before verb, identify actor, restructure passive constructions.",
        "passive": "To use passive voice: Move object before verb, use 'be' + past participle, de-emphasize actor.",
        "positive": "To rephrase positively: Focus on what IS possible, replace negative words with affirming alternatives, frame constructively.",
        "neutral": "To rephrase neutrally: Remove emotional language, use objective terms, present facts without judgment.",
        "direct": "To rephrase directly: State the point first, eliminate hedging words, use clear subject-verb structure.",
    }

    SUMMARIZE_PATTERNS = {
        "bullet": "To create bullet summary: Extract main points, one idea per bullet, use parallel structure, keep under 5 points.",
        "paragraph": "To create paragraph summary: Write topic sentence, include 2-3 key supporting points, conclude with implication.",
        "headline": "To create headline summary: Capture core message in 5-10 words, use strong verbs, make it scannable.",
        "abstract": "To create abstract: State purpose (1 sent), method (1 sent), key findings (2 sent), conclusion (1 sent).",
        "executive": "To create executive summary: Lead with recommendation, provide 3-5 key points, end with action items.",
    }

    SIMPLIFY_PATTERNS = {
        "jargon": "To remove jargon: Replace technical terms with common words, explain acronyms, use analogies for complex concepts.",
        "sentence": "To simplify sentences: Break long sentences into shorter ones, use subject-verb-object order, limit to one idea per sentence.",
        "vocabulary": "To simplify vocabulary: Replace complex words with common alternatives, use concrete vs abstract terms, avoid Latin phrases.",
        "structure": "To simplify structure: Use chronological order, group related ideas, add transitional phrases, use numbered lists.",
        "readability": "To improve readability: Use shorter paragraphs (3-4 sentences), add white space, use subheadings, vary sentence length.",
    }

    CLARIFY_PATTERNS = {
        "ambiguous": "To clarify ambiguity: Specify pronouns, define vague terms, add quantifiers (all/some/many), remove double negatives.",
        "logic": "To clarify logic: Show cause-effect relationships, use 'because/therefore/if-then', sequence steps clearly.",
        "examples": "To clarify with examples: Add concrete instances, use 'for example' or 'such as', show before/after comparisons.",
        "definitions": "To clarify definitions: Define key terms upfront, use parenthetical explanations, create glossary if needed.",
        "scope": "To clarify scope: State what IS and ISN'T included, specify audience, define boundaries, list assumptions.",
    }

    def handle(self, query: str) -> str:
        """Handle text transformation query.
        
        Returns deterministic guidance for text transformation.
        Does NOT perform actual transformation (no LLM).
        
        Args:
            query: User query requesting text transformation
            
        Returns:
            String with transformation guidance or error message
        """
        query_lower = query.lower()
        
        # Extract text to transform (look for patterns)
        # If no clear text is provided, return error
        if not self._has_transformable_text(query):
            return "Error: No text provided for transformation. Please provide the text you want to transform."
        
        # Route to appropriate transformation handler
        if any(word in query_lower for word in ["rewrite", "rewriting"]):
            return self._handle_rewrite(query_lower)
        elif any(word in query_lower for word in ["rephrase", "rephrasing"]):
            return self._handle_rephrase(query_lower)
        elif any(word in query_lower for word in ["summarize", "summary"]):
            return self._handle_summarize(query_lower)
        elif any(word in query_lower for word in ["simplify", "simpler"]):
            return self._handle_simplify(query_lower)
        elif any(word in query_lower for word in ["clarify", "clearer", "clear up"]):
            return self._handle_clarify(query_lower)
        else:
            return "Text Transformation: Hermes handles rewriting, rephrasing, summarizing, simplifying, and clarifying text. Specify which transformation you need."

    def _has_transformable_text(self, query: str) -> bool:
        """Check if query contains text to transform.
        
        Simple heuristic: query should have more than just the trigger word
        and should contain some content (more than 5 words or includes colon/quote).
        """
        words = query.split()
        # Check for content indicators
        has_colon = ":" in query
        has_quotes = '"' in query or "'" in query
        has_sufficient_length = len(words) > 5
        
        return has_colon or has_quotes or has_sufficient_length

    def _handle_rewrite(self, query: str) -> str:
        """Handle rewrite request."""
        for pattern, guidance in self.REWRITE_PATTERNS.items():
            if pattern in query:
                return f"Rewrite Guidance: {guidance}"
        
        # Default rewrite guidance
        return "Rewrite Guidance: To rewrite text effectively:\n1. Identify target audience and purpose\n2. Choose appropriate tone (formal/casual/technical)\n3. Restructure sentences for clarity\n4. Replace weak verbs with strong alternatives\n5. Ensure consistent voice throughout"

    def _handle_rephrase(self, query: str) -> str:
        """Handle rephrase request."""
        for pattern, guidance in self.REPHRASE_PATTERNS.items():
            if pattern in query:
                return f"Rephrase Guidance: {guidance}"
        
        # Default rephrase guidance
        return "Rephrase Guidance: To rephrase text:\n1. Preserve original meaning\n2. Use different sentence structure\n3. Replace synonyms where appropriate\n4. Adjust word order for emphasis\n5. Maintain consistent tone"

    def _handle_summarize(self, query: str) -> str:
        """Handle summarize request."""
        for pattern, guidance in self.SUMMARIZE_PATTERNS.items():
            if pattern in query:
                return f"Summarize Guidance: {guidance}"
        
        # Default summarize guidance
        return "Summarize Guidance: To summarize effectively:\n1. Identify main idea/thesis\n2. Extract 3-5 key supporting points\n3. Remove examples and details\n4. Use your own words\n5. Maintain logical flow"

    def _handle_simplify(self, query: str) -> str:
        """Handle simplify request."""
        for pattern, guidance in self.SIMPLIFY_PATTERNS.items():
            if pattern in query:
                return f"Simplify Guidance: {guidance}"
        
        # Default simplify guidance
        return "Simplify Guidance: To simplify text:\n1. Break complex sentences into simple ones\n2. Replace difficult words with common alternatives\n3. Remove unnecessary modifiers\n4. Use concrete examples\n5. Organize information logically"

    def _handle_clarify(self, query: str) -> str:
        """Handle clarify request."""
        for pattern, guidance in self.CLARIFY_PATTERNS.items():
            if pattern in query:
                return f"Clarify Guidance: {guidance}"
        
        # Default clarify guidance
        return "Clarify Guidance: To clarify text:\n1. Define ambiguous terms\n2. Add specific examples\n3. Explain cause-effect relationships\n4. Remove vague language\n5. Organize information with clear structure"
