"""Recommendation engine - EXPLICITLY FORBIDDEN in Pluto v0.2.

Recommendations for financial decisions are not allowed.
Pluto provides conceptual information only.
"""


class RecommendationEngine:
    """Recommendation engine explicitly forbidden in Pluto v0.2."""
    
    def __init__(self):
        raise RuntimeError(
            "Recommendations are forbidden in Pluto v0.2. "
            "Pluto provides educational information only. "
            "Consult financial professionals for personalized guidance."
        )
