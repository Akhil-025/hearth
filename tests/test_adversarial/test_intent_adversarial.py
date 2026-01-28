"""
ADVERSARIAL TEST SUITE - CYCLE 1: Intent Classification

Testing adversarial intent phrasing, multi-intent sentences, collisions, edge cases.
"""
import pytest
from hestia.intent_classifier import IntentClassifier


class TestIntentClassificationAdversarial:
    """Adversarial intent classification tests."""
    
    @pytest.fixture
    def classifier(self):
        """Fresh classifier for each test."""
        return IntentClassifier()
    
    # ============ Edge Cases & Ambiguous Phrasing ============
    
    def test_empty_string_intent(self, classifier):
        """What does classifier do with empty input?"""
        result = classifier.classify("")
        assert isinstance(result, str)
        # FIND: What's the fallback intent for empty input?
    
    def test_whitespace_only_intent(self, classifier):
        """Whitespace-only input."""
        result = classifier.classify("   ")
        assert isinstance(result, str)
    
    def test_single_character_intent(self, classifier):
        """Single character input."""
        result = classifier.classify("a")
        assert isinstance(result, str)
    
    def test_numbers_only_intent(self, classifier):
        """Pure numeric input."""
        result = classifier.classify("123456789")
        assert isinstance(result, str)
    
    def test_special_characters_intent(self, classifier):
        """Special characters only."""
        result = classifier.classify("!@#$%^&*()")
        assert isinstance(result, str)
    
    # ============ Adversarial Phrasing ============
    
    def test_pattern_embedded_in_sentence(self, classifier):
        """Pattern hidden in middle of sentence."""
        result = classifier.classify("I was thinking about how to search my notes about Python")
        # Does it trigger athena_query? Should it?
        return result
    
    def test_negation_of_pattern(self, classifier):
        """Pattern negated."""
        result = classifier.classify("I don't want to search my notes")
        assert result != "athena_query"  # Shouldn't trigger despite having pattern
    
    def test_pattern_misspelled(self, classifier):
        """Pattern with typo."""
        result = classifier.classify("serch my notes")  # typo: "serch"
        assert result != "athena_query"  # Typo shouldn't match
    
    def test_pattern_partial_word_boundary(self, classifier):
        """Pattern as substring of larger word."""
        result = classifier.classify("researching my notes on Python")
        # "search" is substring of "researching" - does it trigger?
        return result
    
    def test_multiple_trigger_phrases_same_input(self, classifier):
        """Input has multiple trigger phrases."""
        result = classifier.classify("search my knowledge for Python, also search my notes about memory")
        # Which one wins? knowledge_query or athena_query?
        return result
    
    def test_trigger_phrase_repeated(self, classifier):
        """Same trigger phrase repeated multiple times."""
        result = classifier.classify("search search search my notes")
        assert isinstance(result, str)
    
    # ============ Multi-Intent Ambiguity ============
    
    def test_memory_and_athena_together(self, classifier):
        """Query asking for both memory and Athena."""
        result = classifier.classify("what do my notes say about what you remember about me")
        # Is this memory_query or athena_query? 
        return result
    
    def test_knowledge_and_athena_together(self, classifier):
        """Query asking for both knowledge and Athena."""
        result = classifier.classify("search my knowledge for Python in my study materials")
        # knowledge_patterns vs athena_patterns collision
        return result
    
    def test_domain_and_memory_together(self, classifier):
        """Domain query mixed with memory."""
        result = classifier.classify("based on what you remember, tell me about sleep hygiene")
        # Should trigger memory context, but is the intent memory_query or apollo_query?
        return result
    
    def test_all_domains_mentioned(self, classifier):
        """All domains in one query."""
        result = classifier.classify(
            "debug my code, simplify my thoughts, tell me about health, "
            "explain jazz, and what is inflation"
        )
        # Which domain wins?
        return result
    
    # ============ Case Sensitivity & Normalization ============
    
    def test_mixed_case_pattern(self, classifier):
        """Pattern in mixed case."""
        result = classifier.classify("SEARCH MY NOTES about Python")
        assert result == "athena_query"  # Should be case-insensitive
    
    def test_unicode_characters(self, classifier):
        """Unicode input."""
        result = classifier.classify("search my notes about 数据科学")
        assert isinstance(result, str)
    
    # ============ Very Long Input ============
    
    def test_extremely_long_input(self, classifier):
        """1MB of text."""
        long_input = "hello world " * 100000
        result = classifier.classify(long_input)
        assert isinstance(result, str)
    
    def test_pattern_at_end_of_long_input(self, classifier):
        """Pattern buried at the end of huge input."""
        long_input = "a " * 100000 + "search my notes"
        result = classifier.classify(long_input)
        assert result == "athena_query"  # Should still find it
    
    # ============ Pattern Ordering ============
    
    def test_athena_before_knowledge_same_trigger(self, classifier):
        """Does pattern check order matter?"""
        result = classifier.classify("search my knowledge for Python")
        # knowledge_patterns has "search my knowledge for"
        # athena_patterns has "search my study material" - no match
        # What's the order of checks?
        return result
    
    def test_check_order_matters(self, classifier):
        """Verify check order consistency."""
        result1 = classifier.classify("search my knowledge for notes")
        result2 = classifier.classify("search my study material for notes")
        # Both could match different patterns
        return result1, result2
    
    # ============ Whitespace Variants ============
    
    def test_extra_spaces_in_pattern(self, classifier):
        """Pattern with extra spaces."""
        result = classifier.classify("search  my  notes")  # double spaces
        # Is pattern matching space-sensitive?
        return result
    
    def test_newlines_in_pattern(self, classifier):
        """Pattern split across lines."""
        result = classifier.classify("search my\nnotes about Python")
        return result
    
    def test_tabs_in_pattern(self, classifier):
        """Pattern with tabs."""
        result = classifier.classify("search\tmy\tnotes about Python")
        return result
    
    # ============ Keyword Map Collisions ============
    
    def test_hello_as_greeting_or_help(self, classifier):
        """'hello' could match greeting or other patterns."""
        result = classifier.classify("hello")
        assert result == "greeting"
    
    def test_help_ambiguity(self, classifier):
        """'help' matches help_request."""
        result = classifier.classify("help me search my notes")
        # Does it trigger help_request or athena_query?
        return result
    
    def test_question_words(self, classifier):
        """All question words at once."""
        result = classifier.classify("what how why")
        assert result == "question"
    
    # ============ Intent Confidence ============
    
    def test_classifier_has_no_confidence_score(self, classifier):
        """Classifier returns string, not structured intent."""
        result = classifier.classify("search my notes")
        assert isinstance(result, str)
        assert result == "athena_query"
        # No confidence score - always 100% or 0%?
    
    # ============ Consistency Tests ============
    
    def test_same_input_same_output(self, classifier):
        """Same input always produces same output."""
        input_text = "search my notes about Python machine learning"
        result1 = classifier.classify(input_text)
        result2 = classifier.classify(input_text)
        assert result1 == result2
    
    def test_classifier_state_isolation(self, classifier):
        """Previous classifications don't affect next one."""
        classifier.classify("search my notes")
        result = classifier.classify("hello")
        assert result == "greeting"
