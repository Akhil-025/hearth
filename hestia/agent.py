"""
HEARTH Hestia Agent - With Optional LLM Reasoning and Memory (v0.1)

ENABLED IN v0.1:
- Intent classification (keyword-based)
- LLM reasoning via Ollama (optional, pure function)
- Memory storage (optional, append-only, user-confirmed)

DISABLED IN v0.1:
- Domain routing and intelligence
- Automatic memory proposals
- Action execution
- Context building
- Planner FSM
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

# DISABLED IN v0.1 — not part of execution spine
# from .planner_fsm import PlannerFSM
# from .context_builder import ContextBuilder
# from .action_router import ActionRouter
# from .domain_router import DomainRouter

from .intent_classifier import IntentClassifier
from .ollama_client import OllamaClient


class AgentResponse(BaseModel):
    """Agent response with optional memory confirmation."""
    response_id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    intent: str = "general"
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    timestamp: datetime = Field(default_factory=datetime.now)
    memory_saved: bool = False  # Track if memory was saved


class HestiaAgent:
    """
    Hestia agent with optional LLM reasoning and memory.
    
    Execution modes:
    - enable_llm=False: Keyword classification + deterministic response
    - enable_llm=True: Keyword classification + LLM generation
    - enable_memory=True: Ask user for confirmation before saving
    
    FUTURE: Will include planning, actions, domains.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        
        self.intent_classifier = IntentClassifier()
        self.enable_llm = config.get("enable_llm", False)
        self.enable_memory = config.get("enable_memory", False)
        
        # Optional LLM client
        self.llm_client: Optional[OllamaClient] = None
        if self.enable_llm:
            self.llm_client = OllamaClient(
                base_url=config.get("ollama_url", "http://localhost:11434"),
                model=config.get("ollama_model", "mistral:latest"),
                timeout=config.get("ollama_timeout", 60)
            )
        
        # Optional memory store
        self.memory_store = None
        if self.enable_memory:
            from mnemosyne.memory_store import MemoryStore
            self.memory_store = MemoryStore(
                db_path=config.get("memory_db_path", "./data/memory.db")
            )
        
        self._llm_initialized = False
    
    async def initialize(self) -> None:
        """Initialize LLM client if enabled."""
        if self.enable_llm and self.llm_client:
            try:
                await self.llm_client.initialize()
                
                # Check if Ollama is actually available
                if not await self.llm_client.is_available():
                    print("WARNING: Ollama not available at configured URL. LLM disabled.")
                    self.enable_llm = False
                else:
                    self._llm_initialized = True
                    
            except Exception as e:
                print(f"WARNING: Failed to initialize Ollama: {e}")
                print("Falling back to deterministic responses.")
                self.enable_llm = False
    
    async def cleanup(self) -> None:
        """Cleanup LLM client if initialized."""
        if self.llm_client and self._llm_initialized:
            await self.llm_client.cleanup()
    
    async def process(self, user_input: str) -> AgentResponse:
        """
        Process input with optional LLM reasoning and memory.
        
        Flow:
        1. Classify intent (keyword matching)
        2. If intent is memory_query: Retrieve and format memories (NO LLM)
        3. Else if LLM enabled: Generate LLM response
        4. Else: Generate deterministic response
        
        Args:
            user_input: Raw text input from user
            
        Returns:
            AgentResponse with classified intent and response
        """
        # Classify intent
        classification = await self.intent_classifier.classify(user_input)
        intent = classification["intent"]
        confidence = classification["confidence"]
        
        # Handle explicit memory query (NEVER goes through LLM)
        if intent == "memory_query":
            response_text = self._handle_memory_query()
            return AgentResponse(
                text=response_text,
                intent=intent,
                confidence=confidence
            )
        
        # Generate response (normal flow)
        if self.enable_llm and self._llm_initialized:
            response_text = await self._generate_llm_response(intent, user_input)
        else:
            response_text = self._generate_deterministic_response(intent, user_input)
        
        return AgentResponse(
            text=response_text,
            intent=intent,
            confidence=confidence
        )

    def should_use_memory_for_context(self, user_input: str) -> bool:
        """Return True only when user explicitly asks to use past memories."""
        if not (self.enable_memory and self.memory_store):
            return False
        text = user_input.lower()
        triggers = [
            "based on what you remember",
            "using my past notes",
            "consider my previous memories",
            "use what you remember about me",
            "use what you remember",
            "based on my memories",
            "using what you remember"
        ]
        return any(trigger in text for trigger in triggers)

    def get_contextual_memory(self, limit: int = 5) -> Optional[str]:
        """Return formatted memory block for LLM context (most recent first)."""
        if not self.memory_store:
            return None

        try:
            memories = self.memory_store.get_recent(count=limit)
            if not memories:
                return None

            lines = [
                "The following are notes the user explicitly asked you to consider.",
                "Do not infer beyond them.",
                ""
            ]

            for i, memory in enumerate(memories, 1):
                timestamp = memory.timestamp[:19]
                lines.append(f"{i}. [{timestamp}] {memory.content}")

            return "\n".join(lines)

        except Exception:
            # Fail closed: if memory retrieval fails, do not inject anything
            return None
    
    def _handle_memory_query(self) -> str:
        """
        Handle explicit user request to see their memories.
        
        This method is ONLY called when user explicitly asks.
        Memories are NEVER automatically injected into responses.
        
        Returns:
            Formatted list of memories or message if none exist
        """
        if not self.memory_store:
            return "Memory is not enabled. Use --memory flag to enable it."
        
        try:
            # Get recent memories (limit to 10 for readability)
            memories = self.memory_store.get_recent(count=10)
            
            if not memories:
                return "I don't have any memories saved yet."
            
            # Format memories as a numbered list
            lines = ["You asked me to remember:"]
            for i, memory in enumerate(memories, 1):
                # Parse timestamp for readability
                timestamp = memory.timestamp[:19]  # Strip microseconds
                lines.append(f"  {i}. [{timestamp}] {memory.content}")
            
            # Add count if there are more
            total = self.memory_store.count()
            if total > len(memories):
                lines.append(f"\n(Showing {len(memories)} of {total} total memories)")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error retrieving memories: {e}"
    
    def should_offer_memory(self, user_input: str, intent: str) -> bool:
        """
        Decide if this input is worth remembering.
        
        Simple heuristic: Remember if it's a statement (not a greeting/question/memory_query).
        """
        if not self.enable_memory:
            return False
        
        # NEVER offer to remember memory queries themselves
        if intent == "memory_query":
            return False
        
        # Don't remember greetings or help requests
        if intent in ["greeting", "help_request"]:
            return False
        
        # Remember substantial statements (not questions)
        if intent in ["information_request", "general"] and len(user_input.strip()) > 10:
            return True
        
        return False
    
    def prompt_memory_confirmation(self, user_input: str) -> bool:
        """
        Ask user if they want to save this to memory.
        
        Returns:
            True if user confirms, False otherwise
        """
        print("\nWould you like me to remember this? (yes/no): ", end="", flush=True)
        response = input().strip().lower()
        return response in ["yes", "y"]
    
    def save_memory(self, user_input: str, intent: str) -> bool:
        """
        Save memory record after user confirmation.
        
        Returns:
            True if saved successfully, False otherwise
        """
        if not self.memory_store:
            return False
        
        try:
            from mnemosyne.memory_store import MemoryRecord
            
            record = MemoryRecord(
                content=user_input,
                memory_type=intent,
                source="user_confirmation",
                metadata={"timestamp": datetime.now().isoformat()}
            )
            
            self.memory_store.append(record)
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to save memory: {e}")
            return False
    
    async def _generate_llm_response(self, intent: str, user_input: str) -> str:
        """Generate response using LLM."""
        if not self.llm_client:
            return self._generate_deterministic_response(intent, user_input)
        
        # Construct system prompt based on intent
        system_prompt = self._build_system_prompt(intent)
        prompt = user_input

        # Only inject memory when explicitly requested
        if self.should_use_memory_for_context(user_input):
            memory_context = self.get_contextual_memory(limit=5)
            if memory_context:
                prompt = f"{memory_context}\n\nUser request: {user_input}"
        
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt
            )
            return response
            
        except Exception as e:
            # Explicit failure handling
            return f"LLM error: {e}\n\nFallback: {self._generate_deterministic_response(intent, user_input)}"
    
    def _build_system_prompt(self, intent: str) -> str:
        """Build minimal system prompt based on intent."""
        base = "You are Hestia, a helpful personal assistant. "
        
        if intent == "greeting":
            return base + "Respond warmly and briefly to greetings."
        elif intent == "help_request":
            return base + "Explain what you can help with concisely."
        elif intent == "question":
            return base + "Answer questions clearly and accurately. If uncertain, say so."
        elif intent == "information_request":
            return base + "Provide relevant information concisely."
        else:
            return base + "Respond helpfully and conversationally."
    
    def _generate_deterministic_response(self, intent: str, user_input: str) -> str:
        """Generate deterministic fallback response."""
        if intent == "greeting":
            return "Hello! HEARTH v0.1 is running in minimal mode."
        elif intent == "help_request":
            return "HEARTH v0.1 - Minimal execution spine. Type any text to see intent classification."
        elif intent == "question":
            return f"You asked: '{user_input}'. Full reasoning is disabled in v0.1."
        elif intent == "information_request":
            return f"Information request received: '{user_input}'. Knowledge retrieval is disabled in v0.1."
        else:
            return f"Received: '{user_input}' (classified as: {intent})"
