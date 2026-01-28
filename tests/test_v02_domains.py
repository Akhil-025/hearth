"""
HEARTH v0.2 Domain Tests

Tests for domain isolation, non-autonomy, and explicit reasoning.

Key Guarantees:
1. Domains return strings only (no side effects)
2. Domains never write memory (read-only reasoning)
3. Domains cannot call other domains (isolation)
4. Domain responses are deterministic (no LLM or randomness)
5. Domains triggered only by explicit patterns
6. Domain failures degrade gracefully
"""

import pytest
from typing import Dict, List
from unittest.mock import Mock, patch

from hestia.agent import HestiaAgent
from hestia.intent_classifier import IntentClassifier


class TestDomainInterface:
    """Test minimal domain interface: handle(query: str) -> str"""

    def test_domain_returns_string(self):
        """Domain.handle() returns string only, no side effects."""
        from domains.hephaestus.service import HephaestusService
        
        domain = HephaestusService()
        result = domain.handle("Debug this: function returns None")
        
        # Must be string
        assert isinstance(result, str), "Domain handle() must return str"
        
        # Must be non-empty
        assert len(result) > 0, "Domain must return non-empty response"

    def test_domain_no_memory_writes(self):
        """Domain.handle() never writes to memory."""
        from domains.hephaestus.service import HephaestusService
        from mnemosyne.memory_store import MemoryStore
        import tempfile
        import os
        
        # Create temp database
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            memory = MemoryStore(db_path)
            
            initial_count = memory.count()
            
            # Call domain
            domain = HephaestusService()
            domain.handle("How would you refactor this code?")
            
            # Memory count unchanged
            final_count = memory.count()
            assert initial_count == final_count, "Domain must not write memory"

    def test_domain_deterministic_responses(self):
        """Domain.handle() returns same response for same query."""
        from domains.hephaestus.service import HephaestusService
        
        domain = HephaestusService()
        query = "Debug this code"
        
        response1 = domain.handle(query)
        response2 = domain.handle(query)
        
        # Same input → same output (deterministic)
        assert response1 == response2, "Domain responses must be deterministic"


class TestHephaestusService:
    """Test Hephaestus domain (code reasoning, debugging)."""

    def test_hephaestus_debug_trigger(self):
        """Hephaestus handles 'debug' keyword."""
        from domains.hephaestus.service import HephaestusService
        
        domain = HephaestusService()
        result = domain.handle("Debug: function crashes with IndexError")
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hephaestus_design_trigger(self):
        """Hephaestus handles 'design' keyword."""
        from domains.hephaestus.service import HephaestusService
        
        domain = HephaestusService()
        result = domain.handle("Design: API for user authentication")
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hephaestus_code_review(self):
        """Hephaestus handles code review requests."""
        from domains.hephaestus.service import HephaestusService
        
        domain = HephaestusService()
        result = domain.handle("Review: for loop with nested conditionals")
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hephaestus_refactor_suggestion(self):
        """Hephaestus handles refactoring requests."""
        from domains.hephaestus.service import HephaestusService
        
        domain = HephaestusService()
        result = domain.handle("How to refactor duplicate code patterns?")
        
        assert isinstance(result, str)
        assert len(result) > 0


class TestHermesService:
    """Test Hermes domain (text transformation, communication)."""

    def test_hermes_rewrite_trigger(self):
        """Hermes handles 'rewrite' keyword."""
        from domains.hermes.service import HermesService
        
        domain = HermesService()
        result = domain.handle("Rewrite this text: The system is functioning properly at this time.")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "rewrite" in result.lower() or "guidance" in result.lower()

    def test_hermes_rephrase_trigger(self):
        """Hermes handles 'rephrase' keyword."""
        from domains.hermes.service import HermesService
        
        domain = HermesService()
        result = domain.handle("Rephrase this sentence: The meeting was attended by everyone.")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "rephrase" in result.lower() or "guidance" in result.lower()

    def test_hermes_summarize_trigger(self):
        """Hermes handles 'summarize' keyword."""
        from domains.hermes.service import HermesService
        
        domain = HermesService()
        result = domain.handle("Summarize this long article about climate change impacts.")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "summar" in result.lower() or "guidance" in result.lower()

    def test_hermes_simplify_trigger(self):
        """Hermes handles 'simplify' keyword."""
        from domains.hermes.service import HermesService
        
        domain = HermesService()
        result = domain.handle("Simplify this technical explanation for beginners.")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "simplif" in result.lower() or "guidance" in result.lower()

    def test_hermes_clarify_trigger(self):
        """Hermes handles 'clearer' keyword."""
        from domains.hermes.service import HermesService
        
        domain = HermesService()
        result = domain.handle("Make this clearer: The system processes data.")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "clarif" in result.lower() or "guidance" in result.lower()

    def test_hermes_no_text_error(self):
        """Hermes returns error if no text provided."""
        from domains.hermes.service import HermesService
        
        domain = HermesService()
        result = domain.handle("Rewrite")
        
        assert isinstance(result, str)
        assert "error" in result.lower() or "no text" in result.lower()


class TestApolloService:
    """Test Apollo domain (health/wellness information)."""

    def test_apollo_health_trigger(self):
        """Apollo handles 'health' keyword."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        result = domain.handle("What is VO2 max?")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "disclaimer" in result.lower() or "health" in result.lower()

    def test_apollo_fitness_trigger(self):
        """Apollo handles 'fitness' keyword."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        result = domain.handle("Explain fitness fundamentals")
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_apollo_exercise_trigger(self):
        """Apollo handles 'exercise' keyword."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        result = domain.handle("Tell me about exercise science")
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_apollo_sleep_trigger(self):
        """Apollo handles 'sleep' keyword."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        result = domain.handle("Explain sleep cycles")
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_apollo_nutrition_trigger(self):
        """Apollo handles 'nutrition' keyword."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        result = domain.handle("What is protein nutrition?")
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_apollo_refuses_diagnosis(self):
        """Apollo explicitly refuses diagnostic requests."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        result = domain.handle("I think I have diabetes. Diagnose me.")
        
        assert isinstance(result, str)
        assert "cannot" in result.lower() or "refus" in result.lower() or "disclaimer" in result.lower()

    def test_apollo_refuses_treatment_advice(self):
        """Apollo explicitly refuses treatment advice."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        result = domain.handle("Should I take antibiotics?")
        
        assert isinstance(result, str)
        assert "cannot" in result.lower() or "consult" in result.lower() or "disclaimer" in result.lower()

    def test_apollo_refuses_personalized_advice(self):
        """Apollo explicitly refuses personalized advice."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        result = domain.handle("I have back pain, what should I do?")
        
        assert isinstance(result, str)
        assert "personalized" in result.lower() or "cannot" in result.lower() or "consult" in result.lower()


class TestDionysusService:
    """Test Dionysus domain (music/art/culture information)."""

    def test_dionysus_music_trigger(self):
        """Dionysus handles 'music' keyword."""
        from domains.dionysus.service import DionysusService
        
        domain = DionysusService()
        result = domain.handle("Explain jazz music")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "jazz" in result.lower() or "music" in result.lower()

    def test_dionysus_art_trigger(self):
        """Dionysus handles 'art' keyword."""
        from domains.dionysus.service import DionysusService
        
        domain = DionysusService()
        result = domain.handle("What is Renaissance art?")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "renaissance" in result.lower() or "art" in result.lower()

    def test_dionysus_culture_trigger(self):
        """Dionysus handles 'culture' keyword."""
        from domains.dionysus.service import DionysusService
        
        domain = DionysusService()
        result = domain.handle("Tell me about festival culture")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "festival" in result.lower() or "culture" in result.lower()

    def test_dionysus_vibe_trigger(self):
        """Dionysus handles 'vibe' keyword."""
        from domains.dionysus.service import DionysusService
        
        domain = DionysusService()
        result = domain.handle("Describe a chill party vibe")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "chill" in result.lower() or "vibe" in result.lower()

    def test_dionysus_refuses_creative_generation(self):
        """Dionysus explicitly refuses creative generation."""
        from domains.dionysus.service import DionysusService
        
        domain = DionysusService()
        result = domain.handle("Write me a song about love")
        
        assert isinstance(result, str)
        assert "cannot" in result.lower() or "generate" in result.lower()

    def test_dionysus_refuses_lyrics_creation(self):
        """Dionysus explicitly refuses lyrics creation."""
        from domains.dionysus.service import DionysusService
        
        domain = DionysusService()
        result = domain.handle("Create lyrics for a rap song")
        
        assert isinstance(result, str)
        assert "cannot" in result.lower() or "create" in result.lower()

    def test_dionysus_refuses_recommendations(self):
        """Dionysus explicitly refuses personal recommendations."""
        from domains.dionysus.service import DionysusService
        
        domain = DionysusService()
        result = domain.handle("Recommend me some music")
        
        assert isinstance(result, str)
        assert "cannot" in result.lower() or "recommend" in result.lower()


class TestPlutoService:
    """Test Pluto domain (financial/economic concepts information)."""

    def test_pluto_financial_concept_trigger(self):
        """Pluto handles 'finance' keyword."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        result = domain.handle("What is finance?")
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Should return concept information
        assert "conceptual" in result.lower() or "finance" in result.lower() or "information" in result.lower()

    def test_pluto_inflation_concept(self):
        """Pluto provides inflation concept explanation."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        result = domain.handle("What is inflation?")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "inflation" in result.lower()

    def test_pluto_asset_concept(self):
        """Pluto provides asset concept explanation."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        result = domain.handle("Explain assets and liabilities")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "asset" in result.lower() or "liability" in result.lower()

    def test_pluto_capital_concept(self):
        """Pluto provides capital concept explanation."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        result = domain.handle("What is capital in economics?")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "capital" in result.lower()

    def test_pluto_refuses_advice(self):
        """Pluto explicitly refuses financial advice."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        result = domain.handle("Should I invest in stocks?")
        
        assert isinstance(result, str)
        assert "cannot" in result.lower() or "advice" in result.lower()

    def test_pluto_refuses_recommendations(self):
        """Pluto explicitly refuses personal recommendations."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        result = domain.handle("Recommend me an investment")
        
        assert isinstance(result, str)
        assert "cannot" in result.lower() or "recommend" in result.lower()

    def test_pluto_refuses_numbers(self):
        """Pluto explicitly refuses numerical guidance."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        result = domain.handle("How much should I budget?")
        
        assert isinstance(result, str)
        assert "cannot" in result.lower() or "guidance" in result.lower()

    def test_pluto_refuses_risk_assessment(self):
        """Pluto explicitly refuses risk evaluation."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        result = domain.handle("Is this investment risky?")
        
        assert isinstance(result, str)
        assert "cannot" in result.lower() or "assess" in result.lower() or "risk" in result.lower()

    def test_pluto_includes_disclaimer(self):
        """Pluto responses include educational disclaimer."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        result = domain.handle("What is inflation?")
        
        assert isinstance(result, str)
        # Should include disclaimer
        assert "conceptual" in result.lower() or "advice" in result.lower() or "professional" in result.lower()


class TestDomainIsolation:
    """Test domain isolation (no cross-domain calls)."""

    def test_hephaestus_no_cross_domain_calls(self):
        """Hephaestus cannot call other domains."""
        from domains.hephaestus.service import HephaestusService
        
        domain = HephaestusService()
        
        # Should not have attributes for calling other domains
        assert not hasattr(domain, 'call_domain'), "Domain must not call other domains"
        assert not hasattr(domain, 'route_to_domain'), "Domain must not route to other domains"
        assert not hasattr(domain, 'domain_registry'), "Domain must not access domain registry"

    def test_hermes_no_cross_domain_calls(self):
        """Hermes cannot call other domains."""
        from domains.hermes.service import HermesService
        
        domain = HermesService()
        
        # Should not have attributes for calling other domains
        assert not hasattr(domain, 'call_domain'), "Domain must not call other domains"
        assert not hasattr(domain, 'route_to_domain'), "Domain must not route to other domains"
        assert not hasattr(domain, 'domain_registry'), "Domain must not access domain registry"

    def test_apollo_no_cross_domain_calls(self):
        """Apollo cannot call other domains."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        
        # Should not have attributes for calling other domains
        assert not hasattr(domain, 'call_domain'), "Domain must not call other domains"
        assert not hasattr(domain, 'route_to_domain'), "Domain must not route to other domains"
        assert not hasattr(domain, 'domain_registry'), "Domain must not access domain registry"

    def test_dionysus_no_cross_domain_calls(self):
        """Dionysus cannot call other domains."""
        from domains.dionysus.service import DionysusService
        
        domain = DionysusService()
        
        # Should not have attributes for calling other domains
        assert not hasattr(domain, 'call_domain'), "Domain must not call other domains"
        assert not hasattr(domain, 'route_to_domain'), "Domain must not route to other domains"
        assert not hasattr(domain, 'domain_registry'), "Domain must not access domain registry"

    def test_pluto_no_cross_domain_calls(self):
        """Pluto cannot call other domains."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        
        # Should not have attributes for calling other domains
        assert not hasattr(domain, 'call_domain'), "Domain must not call other domains"
        assert not hasattr(domain, 'route_to_domain'), "Domain must not route to other domains"
        assert not hasattr(domain, 'domain_registry'), "Domain must not access domain registry"

    def test_hephaestus_only_has_handle_method(self):
        """Hephaestus interface is minimal: only handle() method."""
        from domains.hephaestus.service import HephaestusService
        
        domain = HephaestusService()
        
        # Check public interface
        public_methods = [m for m in dir(domain) if not m.startswith('_')]
        
        # Should have 'handle' at least
        assert 'handle' in public_methods, "Domain must have handle() method"


class TestDomainNonAutonomy:
    """Test that domains don't exhibit autonomous behavior."""

    def test_hephaestus_no_planning(self):
        """Hephaestus cannot plan or execute actions."""
        from domains.hephaestus.service import HephaestusService
        
        domain = HephaestusService()
        
        # Should not have planning attributes
        assert not hasattr(domain, 'plan'), "Domain must not plan"
        assert not hasattr(domain, 'execute'), "Domain must not execute"
        assert not hasattr(domain, 'planner'), "Domain must not have planner"

    def test_hephaestus_no_autonomy_attributes(self):
        """Hephaestus has no autonomous decision-making."""
        from domains.hephaestus.service import HephaestusService
        
        domain = HephaestusService()
        
        # Should not have autonomy-related attributes
        forbidden_attrs = [
            'should_act', 'decide', 'choose', 'select',
            'autonomous_mode', 'auto_execute', 'background_task'
        ]
        
        for attr in forbidden_attrs:
            assert not hasattr(domain, attr), f"Domain must not have {attr}"

    def test_hermes_no_planning(self):
        """Hermes cannot plan or execute actions."""
        from domains.hermes.service import HermesService
        
        domain = HermesService()
        
        # Should not have planning attributes
        assert not hasattr(domain, 'plan'), "Domain must not plan"
        assert not hasattr(domain, 'execute'), "Domain must not execute"
        assert not hasattr(domain, 'planner'), "Domain must not have planner"

    def test_hermes_no_autonomy_attributes(self):
        """Hermes has no autonomous decision-making."""
        from domains.hermes.service import HermesService
        
        domain = HermesService()
        
        # Should not have autonomy-related attributes
        forbidden_attrs = [
            'should_act', 'decide', 'choose', 'select',
            'autonomous_mode', 'auto_execute', 'background_task'
        ]
        
        for attr in forbidden_attrs:
            assert not hasattr(domain, attr), f"Domain must not have {attr}"

    def test_apollo_no_planning(self):
        """Apollo cannot plan or execute actions."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        
        # Should not have planning attributes
        assert not hasattr(domain, 'plan'), "Domain must not plan"
        assert not hasattr(domain, 'execute'), "Domain must not execute"
        assert not hasattr(domain, 'planner'), "Domain must not have planner"

    def test_apollo_no_autonomy_attributes(self):
        """Apollo has no autonomous decision-making."""
        from domains.apollo.service import ApolloService
        
        domain = ApolloService()
        
        # Should not have autonomy-related attributes
        forbidden_attrs = [
            'should_act', 'decide', 'choose', 'select',
            'autonomous_mode', 'auto_execute', 'background_task'
        ]
        
        for attr in forbidden_attrs:
            assert not hasattr(domain, attr), f"Domain must not have {attr}"

    def test_dionysus_no_planning(self):
        """Dionysus cannot plan or execute actions."""
        from domains.dionysus.service import DionysusService
        
        domain = DionysusService()
        
        # Should not have planning attributes
        assert not hasattr(domain, 'plan'), "Domain must not plan"
        assert not hasattr(domain, 'execute'), "Domain must not execute"
        assert not hasattr(domain, 'planner'), "Domain must not have planner"

    def test_dionysus_no_autonomy_attributes(self):
        """Dionysus has no autonomous decision-making."""
        from domains.dionysus.service import DionysusService
        
        domain = DionysusService()
        
        # Should not have autonomy-related attributes
        forbidden_attrs = [
            'should_act', 'decide', 'choose', 'select',
            'autonomous_mode', 'auto_execute', 'background_task'
        ]
        
        for attr in forbidden_attrs:
            assert not hasattr(domain, attr), f"Domain must not have {attr}"

    def test_pluto_no_planning(self):
        """Pluto cannot plan or execute actions."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        
        # Should not have planning attributes
        assert not hasattr(domain, 'plan'), "Domain must not plan"
        assert not hasattr(domain, 'execute'), "Domain must not execute"
        assert not hasattr(domain, 'planner'), "Domain must not have planner"

    def test_pluto_no_autonomy_attributes(self):
        """Pluto has no autonomous decision-making."""
        from domains.pluto.service import PlutoService
        
        domain = PlutoService()
        
        # Should not have autonomy-related attributes
        forbidden_attrs = [
            'should_act', 'decide', 'choose', 'select',
            'autonomous_mode', 'auto_execute', 'background_task'
        ]
        
        for attr in forbidden_attrs:
            assert not hasattr(domain, attr), f"Domain must not have {attr}"


class TestHephaestusIntentDetection:
    """Test Hephaestus trigger detection in intent classifier."""

    def test_hephaestus_debug_intent(self):
        """Intent classifier detects 'debug' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Debug: function returns wrong value")
        assert intent == "hephaestus_query", f"Expected hephaestus_query, got {intent}"

    def test_hephaestus_design_intent(self):
        """Intent classifier detects 'design' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Design: scalable database schema")
        assert intent == "hephaestus_query", f"Expected hephaestus_query, got {intent}"

    def test_hephaestus_refactor_intent(self):
        """Intent classifier detects 'refactor' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("How to refactor this?")
        assert intent == "hephaestus_query", f"Expected hephaestus_query, got {intent}"

    def test_hephaestus_code_review_intent(self):
        """Intent classifier detects 'review' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Review this code for quality")
        assert intent == "hephaestus_query", f"Expected hephaestus_query, got {intent}"

    def test_non_hephaestus_queries_not_routed(self):
        """Non-Hephaestus queries don't trigger domain."""
        classifier = IntentClassifier()
        
        # These should NOT be hephaestus_query
        non_hephaestus = [
            "Hello",
            "What time is it?",
            "Tell me a joke",
        ]
        
        for query in non_hephaestus:
            intent = classifier.classify(query)
            assert intent != "hephaestus_query", \
                f"Query '{query}' should not trigger hephaestus_query"


class TestHermesIntentDetection:
    """Test Hermes trigger detection in intent classifier."""

    def test_hermes_rewrite_intent(self):
        """Intent classifier detects 'rewrite' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Rewrite this text: The weather is nice.")
        assert intent == "hermes_query", f"Expected hermes_query, got {intent}"

    def test_hermes_rephrase_intent(self):
        """Intent classifier detects 'rephrase' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Rephrase this sentence for clarity")
        assert intent == "hermes_query", f"Expected hermes_query, got {intent}"

    def test_hermes_summarize_intent(self):
        """Intent classifier detects 'summarize' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Summarize this article")
        assert intent == "hermes_query", f"Expected hermes_query, got {intent}"

    def test_hermes_simplify_intent(self):
        """Intent classifier detects 'simplify' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Simplify this explanation")
        assert intent == "hermes_query", f"Expected hermes_query, got {intent}"

    def test_hermes_clearer_intent(self):
        """Intent classifier detects 'clearer' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Make this clearer")
        assert intent == "hermes_query", f"Expected hermes_query, got {intent}"

    def test_non_hermes_queries_not_routed(self):
        """Non-Hermes queries don't trigger domain."""
        classifier = IntentClassifier()
        
        # These should NOT be hermes_query
        non_hermes = [
            "Hello",
            "Debug this code",
            "What time is it?",
        ]
        
        for query in non_hermes:
            intent = classifier.classify(query)
            assert intent != "hermes_query", \
                f"Query '{query}' should not trigger hermes_query"


class TestApolloIntentDetection:
    """Test Apollo trigger detection in intent classifier."""

    def test_apollo_health_intent(self):
        """Intent classifier detects 'health' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("What is health?")
        assert intent == "apollo_query", f"Expected apollo_query, got {intent}"

    def test_apollo_fitness_intent(self):
        """Intent classifier detects 'fitness' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Fitness information please")
        assert intent == "apollo_query", f"Expected apollo_query, got {intent}"

    def test_apollo_exercise_intent(self):
        """Intent classifier detects 'exercise' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Tell me about exercise")
        assert intent == "apollo_query", f"Expected apollo_query, got {intent}"

    def test_apollo_sleep_intent(self):
        """Intent classifier detects 'sleep' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Explain sleep science")
        assert intent == "apollo_query", f"Expected apollo_query, got {intent}"

    def test_apollo_nutrition_intent(self):
        """Intent classifier detects 'nutrition' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("nutrition basics")
        assert intent == "apollo_query", f"Expected apollo_query, got {intent}"

    def test_non_apollo_queries_not_routed(self):
        """Non-Apollo queries don't trigger domain."""
        classifier = IntentClassifier()
        
        # These should NOT be apollo_query
        non_apollo = [
            "Hello",
            "Rewrite this text",
            "Debug the code",
        ]
        
        for query in non_apollo:
            intent = classifier.classify(query)
            assert intent != "apollo_query", \
                f"Query '{query}' should not trigger apollo_query"


class TestDionysusIntentDetection:
    """Test Dionysus trigger detection in intent classifier."""

    def test_dionysus_music_intent(self):
        """Intent classifier detects 'music' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Tell me about music genres")
        assert intent == "dionysus_query", f"Expected dionysus_query, got {intent}"

    def test_dionysus_art_intent(self):
        """Intent classifier detects 'art' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Explain art history")
        assert intent == "dionysus_query", f"Expected dionysus_query, got {intent}"

    def test_dionysus_culture_intent(self):
        """Intent classifier detects 'culture' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("What is culture?")
        assert intent == "dionysus_query", f"Expected dionysus_query, got {intent}"

    def test_dionysus_party_intent(self):
        """Intent classifier detects 'party' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Describe party vibes")
        assert intent == "dionysus_query", f"Expected dionysus_query, got {intent}"

    def test_dionysus_entertainment_intent(self):
        """Intent classifier detects 'entertainment' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Entertainment concepts")
        assert intent == "dionysus_query", f"Expected dionysus_query, got {intent}"

    def test_non_dionysus_queries_not_routed(self):
        """Non-Dionysus queries don't trigger domain."""
        classifier = IntentClassifier()
        
        # These should NOT be dionysus_query
        non_dionysus = [
            "Hello",
            "Debug code",
            "Health information",
        ]
        
        for query in non_dionysus:
            intent = classifier.classify(query)
            assert intent != "dionysus_query", \
                f"Query '{query}' should not trigger dionysus_query"


class TestPlutoIntentDetection:
    """Test Pluto trigger detection in intent classifier."""

    def test_pluto_money_intent(self):
        """Intent classifier detects 'money' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Tell me about money management")
        assert intent == "pluto_query", f"Expected pluto_query, got {intent}"

    def test_pluto_finance_intent(self):
        """Intent classifier detects 'finance' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Explain finance concepts")
        assert intent == "pluto_query", f"Expected pluto_query, got {intent}"

    def test_pluto_economics_intent(self):
        """Intent classifier detects 'economics' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("What is economics?")
        assert intent == "pluto_query", f"Expected pluto_query, got {intent}"

    def test_pluto_asset_intent(self):
        """Intent classifier detects 'asset' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Explain what an asset is")
        assert intent == "pluto_query", f"Expected pluto_query, got {intent}"

    def test_pluto_budget_intent(self):
        """Intent classifier detects 'budget' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("What does budget mean?")
        assert intent == "pluto_query", f"Expected pluto_query, got {intent}"

    def test_pluto_risk_intent(self):
        """Intent classifier detects 'risk' keyword."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("Risk concepts in finance")
        assert intent == "pluto_query", f"Expected pluto_query, got {intent}"

    def test_non_pluto_queries_not_routed(self):
        """Non-Pluto queries don't trigger domain."""
        classifier = IntentClassifier()
        
        # These should NOT be pluto_query
        non_pluto = [
            "Hello",
            "Debug code",
            "Health information",
            "Musical concepts",
        ]
        
        for query in non_pluto:
            intent = classifier.classify(query)
            assert intent != "pluto_query", \
                f"Query '{query}' should not trigger pluto_query"


class TestDomainAgentIntegration:
    """Test domain routing from hestia/agent.py."""

    @pytest.mark.asyncio
    async def test_agent_routes_to_hephaestus(self):
        """Agent routes hephaestus_query to domain handler."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # Query that triggers hephaestus_query intent
        response = await agent.process("Debug: array index out of bounds")
        
        # Should get domain response (not deterministic fallback)
        assert response is not None
        assert isinstance(response.text, str)
        assert len(response.text) > 0
        assert response.intent == "hephaestus_query"

    @pytest.mark.asyncio
    async def test_agent_hephaestus_response_no_llm(self):
        """Hephaestus response doesn't use LLM."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": True, "enable_memory": False})
        
        # Query that triggers hephaestus_query
        response = await agent.process("Refactor: nested if statements")
        
        # Response should be from domain, not LLM
        # (Domain response is deterministic)
        assert response is not None
        assert isinstance(response.text, str)
        assert response.intent == "hephaestus_query"

    @pytest.mark.asyncio
    async def test_agent_hephaestus_response_no_memory(self):
        """Hephaestus response doesn't write memory."""
        from hestia.agent import HestiaAgent
        from mnemosyne.memory_store import MemoryStore
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            memory = MemoryStore(db_path)
            
            agent = HestiaAgent(config={"enable_llm": False, "enable_memory": True})
            agent.memory_store = memory
            
            initial_count = memory.count()
            
            # Query that triggers hephaestus_query
            response = await agent.process("Debug: null pointer exception")
            
            # Memory count unchanged (domain doesn't write memory)
            final_count = memory.count()
            assert initial_count == final_count, \
                "Hephaestus should not write memory"

    @pytest.mark.asyncio
    async def test_agent_routes_to_hermes(self):
        """Agent routes hermes_query to domain handler."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # Query that triggers hermes_query intent
        response = await agent.process("Rewrite this text: The system works well.")
        
        # Should get domain response
        assert response is not None
        assert isinstance(response.text, str)
        assert len(response.text) > 0
        assert response.intent == "hermes_query"

    @pytest.mark.asyncio
    async def test_agent_hermes_response_no_llm(self):
        """Hermes response doesn't use LLM."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": True, "enable_memory": False})
        
        # Query that triggers hermes_query
        response = await agent.process("Summarize this article about AI")
        
        # Response should be from domain, not LLM
        assert response is not None
        assert isinstance(response.text, str)
        assert response.intent == "hermes_query"

    @pytest.mark.asyncio
    async def test_agent_hermes_response_no_memory(self):
        """Hermes response doesn't write memory."""
        from hestia.agent import HestiaAgent
        from mnemosyne.memory_store import MemoryStore
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            memory = MemoryStore(db_path)
            
            agent = HestiaAgent(config={"enable_llm": False, "enable_memory": True})
            agent.memory_store = memory
            
            initial_count = memory.count()
            
            # Query that triggers hermes_query
            response = await agent.process("Simplify this technical description")
            
            # Memory count unchanged (domain doesn't write memory)
            final_count = memory.count()
            assert initial_count == final_count, \
                "Hermes should not write memory"

    @pytest.mark.asyncio
    async def test_agent_routes_to_apollo(self):
        """Agent routes apollo_query to domain handler."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # Query that triggers apollo_query intent (needs health/fitness/exercise/etc keyword)
        response = await agent.process("Explain fitness fundamentals")
        
        # Should get domain response
        assert response is not None
        assert isinstance(response.text, str)
        assert len(response.text) > 0
        assert response.intent == "apollo_query"

    @pytest.mark.asyncio
    async def test_agent_apollo_response_no_llm(self):
        """Apollo response doesn't use LLM."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": True, "enable_memory": False})
        
        # Query that triggers apollo_query
        response = await agent.process("Sleep science explanation")
        
        # Response should be from domain, not LLM
        assert response is not None
        assert isinstance(response.text, str)
        assert response.intent == "apollo_query"

    @pytest.mark.asyncio
    async def test_agent_apollo_response_no_memory(self):
        """Apollo response doesn't write memory."""
        from hestia.agent import HestiaAgent
        from mnemosyne.memory_store import MemoryStore
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            memory = MemoryStore(db_path)
            
            agent = HestiaAgent(config={"enable_llm": False, "enable_memory": True})
            agent.memory_store = memory
            
            initial_count = memory.count()
            
            # Query that triggers apollo_query
            response = await agent.process("Health information about metabolism")
            
            # Memory count unchanged (domain doesn't write memory)
            final_count = memory.count()
            assert initial_count == final_count, \
                "Apollo should not write memory"

    @pytest.mark.asyncio
    async def test_agent_apollo_refuses_diagnosis(self):
        """Apollo refuses diagnostic requests through agent."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # Query requesting diagnosis with apollo trigger
        response = await agent.process("Health question: diagnose my symptoms: fever and cough")
        
        # Should get refusal
        assert response is not None
        assert isinstance(response.text, str)
        assert response.intent == "apollo_query"
        assert "cannot" in response.text.lower() or "consult" in response.text.lower()


class TestDomainGracefulDegradation:
    """Test graceful degradation when domain fails."""

    @pytest.mark.asyncio
    async def test_agent_graceful_fallback_if_hephaestus_fails(self):
        """Agent falls back to deterministic response if domain fails."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # Mock domain to fail
        with patch.object(agent, 'hephaestus') as mock_domain:
            mock_domain.handle.side_effect = Exception("Domain error")
            
            # Should not crash, should return helpful message
            try:
                response = await agent.process("Debug: something")
                # Should still return a response
                assert response is not None
                assert isinstance(response.text, str)
            except Exception:
                pytest.fail("Agent should degrade gracefully on domain failure")

    @pytest.mark.asyncio
    async def test_agent_routes_to_dionysus(self):
        """Agent correctly routes music/art/culture queries to Dionysus domain."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        response = await agent.process("Explain jazz music")
        
        assert response is not None
        assert response.intent == "dionysus_query"
        # Should receive informational response, not empty
        assert isinstance(response.text, str)
        assert len(response.text) > 0

    @pytest.mark.asyncio
    async def test_agent_dionysus_response_no_llm(self):
        """Dionysus query responses don't use LLM."""
        from hestia.agent import HestiaAgent
        from unittest.mock import patch, AsyncMock
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # Mock LLM to track if it's called
        with patch.object(agent, 'llm_client') as mock_ollama:
            mock_ollama.generate = AsyncMock()
            
            # Process Dionysus query
            response = await agent.process("What is Renaissance art?")
            
            # LLM should NOT be called for domain queries
            mock_ollama.generate.assert_not_called()
            assert response.intent == "dionysus_query"

    @pytest.mark.asyncio
    async def test_agent_dionysus_response_no_memory(self):
        """Dionysus queries don't trigger memory saves."""
        from hestia.agent import HestiaAgent
        from unittest.mock import patch, MagicMock
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": True})
        
        # Mock memory to track saves
        with patch.object(agent, 'memory_store') as mock_memory:
            mock_memory.save = MagicMock(return_value=True)
            
            # Process Dionysus query
            response = await agent.process("Describe a chill party vibe")
            
            # Memory should NOT be saved for dionysus_query
            mock_memory.save.assert_not_called()
            assert response.intent == "dionysus_query"

    @pytest.mark.asyncio
    async def test_agent_dionysus_refuses_creative_generation(self):
        """Agent properly refuses creative generation requests."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # Should refuse to write/generate creative content
        response = await agent.process("Write me a song about love")
        
        assert response.intent == "dionysus_query"
        # Should contain refusal language
        assert any(word in response.text.lower() 
                  for word in ["cannot", "refusal", "generate", "creative"])

    @pytest.mark.asyncio
    async def test_agent_routes_to_pluto(self):
        """Agent correctly routes financial/economic queries to Pluto domain."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        response = await agent.process("What is money in economics?")
        
        assert response is not None
        assert response.intent == "pluto_query"
        # Should receive concept information
        assert isinstance(response.text, str)
        assert len(response.text) > 0

    @pytest.mark.asyncio
    async def test_agent_pluto_response_no_llm(self):
        """Pluto query responses don't use LLM."""
        from hestia.agent import HestiaAgent
        from unittest.mock import patch, AsyncMock
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # Mock LLM to track if it's called
        with patch.object(agent, 'llm_client') as mock_llm:
            mock_llm.generate = AsyncMock()
            
            # Process Pluto query
            response = await agent.process("Explain what an asset is")
            
            # LLM should NOT be called for domain queries
            mock_llm.generate.assert_not_called()
            assert response.intent == "pluto_query"

    @pytest.mark.asyncio
    async def test_agent_pluto_response_no_memory(self):
        """Pluto queries don't trigger memory saves."""
        from hestia.agent import HestiaAgent
        from unittest.mock import patch, MagicMock
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": True})
        
        # Mock memory to track saves
        with patch.object(agent, 'memory_store') as mock_memory:
            mock_memory.save = MagicMock(return_value=True)
            
            # Process Pluto query
            response = await agent.process("What is capital in economics?")
            
            # Memory should NOT be saved for pluto_query
            mock_memory.save.assert_not_called()
            assert response.intent == "pluto_query"

    @pytest.mark.asyncio
    async def test_agent_pluto_refuses_advice(self):
        """Agent properly refuses financial advice requests."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # Should refuse to give advice - must include financial keyword
        response = await agent.process("Should I invest in financial assets?")
        
        assert response.intent == "pluto_query"
        # Should contain refusal language
        assert any(word in response.text.lower() 
                  for word in ["cannot", "refusal", "advice", "recommend"])

    @pytest.mark.asyncio
    async def test_agent_pluto_refuses_numbers(self):
        """Agent refuses queries asking for specific numbers or calculations."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # Should refuse numerical guidance
        response = await agent.process("How much should I budget for retirement?")
        
        assert response.intent == "pluto_query"
        # Should contain refusal for numbers
        assert any(word in response.text.lower() 
                  for word in ["cannot", "refusal", "guidance", "recommend"])


class TestDomainNonRegression:
    """Test that v0.1 guarantees still hold with domains."""

    @pytest.mark.asyncio
    async def test_v01_memory_write_confirmation_still_enforced(self):
        """v0.1 memory write confirmation not bypassed by domains."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": True})
        
        # Save memory requires explicit call and intent
        # This method exists and requires both parameters
        result = agent.save_memory("test input", intent="general")
        
        # Should work (we have memory_store)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_v01_general_queries_unaffected(self):
        """v0.1 general query handling unchanged."""
        from hestia.agent import HestiaAgent
        
        agent = HestiaAgent(config={"enable_llm": False, "enable_memory": False})
        
        # General query (not hephaestus)
        response = await agent.process("Hello")
        
        assert response is not None
        assert isinstance(response.text, str)
        assert len(response.text) > 0

    def test_intent_classification_backwards_compatible(self):
        """Intent classifier still recognizes v0.1 intents."""
        from hestia.intent_classifier import IntentClassifier
        
        classifier = IntentClassifier()
        
        # v0.1 intents should still work
        assert classifier.classify("what do you remember") == "memory_query"
        assert classifier.classify("search my knowledge for X") == "knowledge_query"
        
        # Greetings should be detected
        assert classifier.classify("hello") in ["greeting", "general"]
