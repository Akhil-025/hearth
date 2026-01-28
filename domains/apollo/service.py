"""
Apollo Domain (v0.2)

Health, fitness, and wellbeing information ONLY.

Triggered by keywords:
- "health"
- "fitness"
- "exercise"
- "nutrition"
- "sleep"
- "wellbeing"
- "body"
- "physiology"

Characteristics:
- Pure deterministic informational responses (no LLM, no randomness)
- No memory writes or reads
- No personalized medical advice
- No autonomy or planning
- No cross-domain calls
- Explicit refusal for: diagnosis, treatment, prescriptions, personalized advice, mental health counseling
"""

from ..base_v2 import Domain


class ApolloService(Domain):
    """Health and wellness information domain.
    
    Provides:
    - Definitions of health/fitness concepts
    - General explanations of physiological processes
    - Safety disclaimers
    - Educational summaries
    
    STRICTLY FORBIDDEN:
    - Diagnosis or diagnostic guidance
    - Treatment advice or recommendations
    - Prescriptions or dosages
    - Personalized health advice
    - Mental health counseling
    - Emergency medical instructions
    
    All responses are deterministic template-based guidance
    with no external dependencies (no LLM, no memory).
    
    IMPORTANT: Apollo is INFORMATIONAL ONLY. Always include
    medical disclaimer and explicit refusals for advice queries.
    """

    # Medical disclaimer (required for all responses)
    MEDICAL_DISCLAIMER = (
        "DISCLAIMER: This information is educational only. "
        "For medical advice, diagnosis, or treatment, consult a qualified healthcare provider."
    )

    # Refusal patterns for forbidden requests
    REFUSAL_PATTERNS = {
        "diagnose": "I cannot diagnose medical conditions. Consult a healthcare provider.",
        "treatment": "I cannot provide treatment recommendations. See a qualified healthcare provider.",
        "prescription": "I cannot recommend prescriptions or medications. Consult a doctor.",
        "dosage": "I cannot provide dosage information. Ask your pharmacist or doctor.",
        "personalized": "I cannot provide personalized health advice. Consult a healthcare provider.",
        "mental health": "I cannot provide mental health counseling. Contact a mental health professional.",
        "emergency": "For emergencies, call emergency services immediately.",
        "symptom": "Symptoms require professional diagnosis. Consult a healthcare provider.",
    }

    # Informational definitions (educational content only)
    INFORMATION_PATTERNS = {
        "vo2": "VO2 max is the maximum amount of oxygen your body can use during exercise, measured in milliliters per kilogram of body weight per minute (ml/kg/min). It's an indicator of cardiovascular fitness.",
        "bmi": "BMI (Body Mass Index) is a measure of body fat based on height and weight. It is calculated as weight(kg) / height(m)². BMI categories: Underweight (<18.5), Normal (18.5-24.9), Overweight (25-29.9), Obese (≥30).",
        "sleep cycle": "Sleep cycles last approximately 90 minutes and include stages: light sleep (N1, N2), deep sleep (N3), and REM sleep. A full night typically includes 4-6 complete cycles.",
        "heart rate": "Resting heart rate (RHR) is the number of heartbeats per minute at rest. Normal RHR for adults: 60-100 bpm. Athletes may have lower RHR (40-60 bpm).",
        "blood pressure": "Blood pressure is measured as systolic/diastolic (mmHg). Normal: <120/<80. Elevated: 120-129/<80. High: ≥130/≥80. These are educational ranges; individual targets vary.",
        "metabolism": "Metabolism is the process by which your body converts food into energy. Basal metabolic rate (BMR) is the calories burned at rest for basic functions.",
        "hydration": "General guidelines suggest drinking about 8 glasses (2 liters) of water daily, though needs vary by activity level, climate, and individual factors.",
        "protein": "Protein is a macronutrient essential for muscle repair and growth. Daily protein needs vary: sedentary adults ~0.8g/kg, athletes may need 1.2-2.0g/kg.",
        "carbohydrate": "Carbohydrates are the primary energy source for the brain and muscles. They're found in grains, fruits, vegetables, and legumes.",
        "fat": "Dietary fats are essential for hormone production, vitamin absorption, and cellular function. Distinguish between saturated, unsaturated, and trans fats.",
        "exercise": "Regular exercise provides benefits including improved cardiovascular health, stronger muscles and bones, better mood, and enhanced cognitive function.",
        "flexibility": "Flexibility is the range of motion in joints. Regular stretching and activities like yoga can improve flexibility and reduce injury risk.",
        "strength": "Strength training involves resistance exercises to build muscle and bone density. Typically recommended 2+ times per week with rest days between sessions.",
        "endurance": "Endurance is the ability to sustain physical activity over time. Cardiovascular exercise (running, cycling, swimming) builds endurance.",
        "stress": "Stress is a normal physiological and psychological response. Chronic stress can affect health; management techniques include exercise, meditation, sleep, and social connection.",
        "immunity": "The immune system defends against infections and disease. Factors supporting immunity: sleep, nutrition, exercise, stress management, hygiene.",
    }

    def handle(self, query: str) -> str:
        """Handle health/wellness information query.
        
        Returns deterministic health information or explicit refusals.
        Does NOT provide medical advice, diagnosis, or treatment.
        
        Args:
            query: User query about health/wellness
            
        Returns:
            String with health information or refusal message
        """
        query_lower = query.lower()
        
        # Check for forbidden request patterns FIRST (hard refusal)
        for forbidden_pattern, refusal in self.REFUSAL_PATTERNS.items():
            if forbidden_pattern in query_lower:
                return f"{refusal} {self.MEDICAL_DISCLAIMER}"
        
        # Check for personalization indicators (hard refusal)
        personal_indicators = [
            "my symptoms", "i have", "i'm experiencing", "i've been",
            "my health", "my condition", "do i have", "should i take",
            "what should i do", "am i", "could i have"
        ]
        
        for indicator in personal_indicators:
            if indicator in query_lower:
                return f"I cannot provide personalized medical advice. Please consult a qualified healthcare provider. {self.MEDICAL_DISCLAIMER}"
        
        # Route to appropriate informational handler
        if any(word in query_lower for word in ["what is", "explain", "define", "tell me about"]):
            return self._handle_information_request(query_lower)
        elif any(word in query_lower for word in ["health", "fitness", "exercise", "nutrition", "sleep", "wellbeing", "body", "physiology"]):
            return self._handle_general_wellness(query_lower)
        else:
            return f"Apollo provides health and wellness information. Ask about: fitness, exercise, nutrition, sleep, physiology, or health concepts. {self.MEDICAL_DISCLAIMER}"

    def _handle_information_request(self, query: str) -> str:
        """Handle general information requests."""
        for keyword, information in self.INFORMATION_PATTERNS.items():
            if keyword in query:
                return f"{information} {self.MEDICAL_DISCLAIMER}"
        
        # Default informational response
        return f"General health information: Apollo can explain fitness concepts, nutrition basics, sleep science, physiology, and exercise principles. {self.MEDICAL_DISCLAIMER}"

    def _handle_general_wellness(self, query: str) -> str:
        """Handle general wellness topic queries."""
        # Attempt to match information patterns
        for keyword, information in self.INFORMATION_PATTERNS.items():
            if keyword in query:
                return f"{information} {self.MEDICAL_DISCLAIMER}"
        
        # Default wellness response
        return f"Wellness information: Health and fitness involve sleep, nutrition, exercise, and stress management. Consult professionals for personalized guidance. {self.MEDICAL_DISCLAIMER}"
