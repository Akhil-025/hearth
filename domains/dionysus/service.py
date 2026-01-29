"""
Dionysus Domain (v0.2)

Music, art, culture, and entertainment information ONLY.

Triggered by keywords:
- "music"
- "song"
- "genre"
- "art"
- "culture"
- "party"
- "fun"
- "vibe"
- "entertainment"

Characteristics:
- Pure deterministic informational responses (no LLM, no randomness)
- No memory writes or reads
- No creative generation (NO songs, poems, lyrics, stories)
- No emotional or mental health advice
- No substance use advice
- No autonomy or planning
- No cross-domain calls
- Explicit refusal for: creativity generation, emotional advice, lifestyle coaching
"""

from ..base_v2 import Domain


class DionysusService(Domain):
    """Music, art, culture, and entertainment information domain.
    
    Provides:
    - Music genre explanations
    - Art style descriptions
    - Cultural context
    - Entertainment trivia
    - Party theme descriptions (descriptive only)
    - Mood descriptions (NOT advice)
    
    STRICTLY FORBIDDEN:
    - Creative generation (songs, poems, lyrics, stories, art)
    - Emotional or mental health advice
    - Substance use advice or recommendations
    - Lifestyle coaching
    - Motivational speech
    - Personal recommendations
    
    All responses are deterministic template-based information
    with no external dependencies (no LLM, no memory).
    
    IMPORTANT: Dionysus is INFORMATIONAL ONLY about culture and art.
    Always refuse creative generation requests explicitly.
    """

    # Refusal patterns for forbidden requests (HARD STOP)
    REFUSAL_PATTERNS = {
        "create": "I cannot generate creative content. I provide information about music, art, and culture only.",
        "write": "I cannot write creative content. I can explain art forms and cultural concepts.",
        "generate": "I cannot generate creative work. I provide cultural and artistic information.",
        "compose": "I cannot compose music or creative content. I can explain musical concepts.",
        "emotional": "I cannot provide emotional or mental health advice. Contact a mental health professional.",
        "substance": "I cannot provide substance-related advice. Consult a healthcare provider.",
        "lifestyle": "I cannot provide lifestyle coaching. I offer cultural and artistic information only.",
        "advice": "I provide information, not advice. For personal guidance, consult appropriate professionals.",
        "should i": "I cannot make recommendations. I explain cultural concepts and art forms.",
    }

    # Informational content (educational explanations only)
    MUSIC_GENRES = {
        "jazz": "Jazz is a music genre originating in African American communities, characterized by swing, blue notes, improvisation, and syncopation. Key styles: bebop, cool jazz, fusion.",
        "rock": "Rock music emerged in the 1950s, characterized by electric guitars, strong beat, and typically verse-chorus structure. Subgenres: classic rock, punk, metal, indie.",
        "classical": "Classical music refers to Western art music spanning roughly 1750-1820, emphasizing form, clarity, and balance. Key composers: Mozart, Beethoven, Haydn.",
        "hip hop": "Hip hop originated in 1970s NYC, characterized by rapping, DJing, breakdancing, and graffiti. Elements: beats, rhymes, sampling, MCing.",
        "electronic": "Electronic music uses electronic instruments and technology. Subgenres: house, techno, trance, dubstep, ambient. Emerged in late 20th century.",
        "blues": "Blues originated in African American communities in the Deep South, characterized by specific chord progressions (12-bar blues), blue notes, and call-and-response patterns.",
        "country": "Country music originated in southern US, characterized by string instruments (guitar, banjo, fiddle), storytelling lyrics, and rural themes.",
        "pop": "Pop music is characterized by short-to-medium songs, repeated choruses, melodic tunes, and hooks. Emphasis on accessibility and mainstream appeal.",
        "reggae": "Reggae originated in Jamaica in the 1960s, characterized by offbeat rhythms, bass-heavy sound, and often socially conscious lyrics.",
        "folk": "Folk music consists of traditional music passed through generations orally. Acoustic instruments, storytelling, cultural preservation.",
    }

    ART_STYLES = {
        "renaissance": "Renaissance art (14th-17th century) emphasized realism, humanism, perspective, and classical themes. Key artists: Leonardo, Michelangelo, Raphael.",
        "impressionism": "Impressionism (late 1800s) focused on capturing light and momentary effects through visible brushstrokes and emphasis on perception. Artists: Monet, Renoir, Degas.",
        "abstract": "Abstract art (20th century) uses shapes, colors, and forms independent of visual reality. Emphasizes non-representational expression.",
        "cubism": "Cubism (early 1900s) depicted subjects from multiple viewpoints simultaneously using geometric forms. Pioneers: Picasso, Braque.",
        "baroque": "Baroque art (1600-1750) featured drama, emotion, grandeur, and ornate detail. Characterized by movement, contrast, and tension.",
        "surrealism": "Surrealism (1920s) explored unconscious mind, dreams, and irrational juxtapositions. Artists: Dalí, Magritte, Miró.",
        "pop art": "Pop art (1950s-60s) used imagery from popular culture, mass media, and advertising. Artists: Warhol, Lichtenstein.",
        "minimalism": "Minimalism (1960s-70s) emphasized simplicity, geometric forms, and reduction to essential elements. Focus on materials and space.",
    }

    CULTURAL_CONCEPTS = {
        "festival": "Cultural festivals are celebrations marking traditions, seasons, or historical events. Include music, food, rituals, community gathering.",
        "concert": "Concerts are live music performances, ranging from intimate shows to large stadium events. Include classical recitals, rock concerts, DJ sets.",
        "gallery": "Art galleries display visual art for public viewing. Types: commercial galleries (selling), museums (educational), pop-up exhibitions.",
        "theater": "Theater is live performance art combining acting, dialogue, music, and stagecraft. Forms: drama, musical theater, experimental.",
        "cinema": "Cinema encompasses film art and industry. Genres: drama, comedy, documentary, experimental. Combines visual storytelling with sound.",
        "dance": "Dance is expressive movement to rhythm. Forms: ballet, contemporary, hip hop, folk, ballroom. Cultural and artistic expression.",
    }

    PARTY_VIBES = {
        "chill": "Chill vibe: Relaxed atmosphere, mellow music (lounge, acoustic, lo-fi), comfortable seating, low-key lighting, conversational.",
        "energetic": "Energetic vibe: Upbeat music (dance, electronic, pop), dynamic lighting, movement-oriented space, high energy.",
        "elegant": "Elegant vibe: Sophisticated atmosphere, refined music (jazz, classical), formal dress, dim lighting, tasteful decor.",
        "casual": "Casual vibe: Laid-back setting, diverse music, comfortable attire, mixed lighting, social mingling focus.",
        "festive": "Festive vibe: Celebratory atmosphere, varied upbeat music, decorations, themed elements, joyful mood.",
    }

    def handle(self, query: str) -> str:
        """Handle music/art/culture information query.
        
        Returns deterministic cultural information or explicit refusals.
        Does NOT generate creative content or provide personal advice.
        
        Artemis enforcement: Domain execution policy enforced at entry
        
        Args:
            query: User query about music/art/culture/entertainment
            
        Returns:
            String with cultural information or refusal message
            
        Raises:
            RuntimeError: If Artemis policy blocks domain execution
        """
        # Artemis enforcement boundary
        # Fail-closed by design
        # Do not bypass
        self._enforce_domain_policy()

        # Artemis fault containment
        # Blast radius limited
        # Fail closed
        # No recovery without restart
        try:
            query_lower = query.lower()
            
            # Check for forbidden creative generation requests FIRST (HARD STOP)
            creative_indicators = [
                "write", "create", "generate", "compose", "make me",
                "give me lyrics", "write a song", "write a poem",
                "create a story", "make music", "design art"
            ]
            
            for indicator in creative_indicators:
                if indicator in query_lower:
                    return "I cannot generate creative content (songs, poems, lyrics, stories, art). I provide information about music, art, and culture."
            
            # Check for other forbidden request patterns (emotional/substance/lifestyle)
            for forbidden_pattern, refusal in self.REFUSAL_PATTERNS.items():
                if forbidden_pattern in query_lower:
                    return refusal
            
            # Check for personal recommendation requests (HARD STOP)
            recommendation_indicators = [
                "should i listen", "recommend me", "what should i",
                "best song for", "suggest music", "which art"
            ]
            
            for indicator in recommendation_indicators:
                if indicator in query_lower:
                    return "I cannot make personal recommendations. I provide information about music genres, art styles, and cultural concepts."
            
            # Route to appropriate informational handler (vibe FIRST to avoid "art" in "party")
            if any(word in query_lower for word in ["party", "vibe", "atmosphere", "mood"]):
                return self._handle_vibe_query(query_lower)
            elif any(word in query_lower for word in ["music", "genre", "song", "band", "artist"]):
                return self._handle_music_query(query_lower)
            elif any(word in query_lower for word in ["art", "painting", "style"]):
                return self._handle_art_query(query_lower)
            elif any(word in query_lower for word in ["culture", "festival", "theater", "cinema", "entertainment"]):
                return self._handle_culture_query(query_lower)
            else:
                return "Dionysus provides information about music, art, culture, and entertainment. Ask about: genres, art styles, cultural concepts, or party vibes."
        except Exception as e:
            self._contain_domain_failure(e)

    def _handle_music_query(self, query: str) -> str:
        """Handle music information requests."""
        for genre, information in self.MUSIC_GENRES.items():
            if genre in query:
                return f"Music Information: {information}"
        
        # Default music response
        return "Music Information: Dionysus can explain music genres (jazz, rock, classical, hip hop, electronic, blues, country, pop, reggae, folk) and musical concepts."

    def _handle_art_query(self, query: str) -> str:
        """Handle art information requests."""
        for style, information in self.ART_STYLES.items():
            if style in query:
                return f"Art Information: {information}"
        
        # Default art response
        return "Art Information: Dionysus can explain art styles (Renaissance, Impressionism, Abstract, Cubism, Baroque, Surrealism, Pop Art, Minimalism) and artistic movements."

    def _handle_vibe_query(self, query: str) -> str:
        """Handle party/vibe description requests."""
        for vibe, description in self.PARTY_VIBES.items():
            if vibe in query:
                return f"Vibe Description: {description}"
        
        # Default vibe response
        return "Vibe Description: Party atmospheres vary (chill, energetic, elegant, casual, festive) based on music, lighting, setting, and social dynamics."

    def _handle_culture_query(self, query: str) -> str:
        """Handle cultural concept requests."""
        for concept, information in self.CULTURAL_CONCEPTS.items():
            if concept in query:
                return f"Cultural Information: {information}"
        
        # Default culture response
        return "Cultural Information: Dionysus can explain entertainment concepts (festivals, concerts, galleries, theater, cinema, dance) and cultural practices."
