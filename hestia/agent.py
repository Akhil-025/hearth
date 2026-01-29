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

ENABLED IN v0.2:
- Hephaestus domain (read-only code reasoning)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

# DISABLED IN v0.1 — not part of execution spine
# from .planner_fsm import PlannerFSM
# from .context_builder import ContextBuilder
# from .action_router import ActionRouter
# from .domain_router import DomainRouter

from artemis.boundary import LockdownPolicy
from artemis.approval import ApprovalRequest, validate_approval_request
from artemis.security_summary import SecuritySummary
from artemis.plan_compiler import PlanCompiler, PlanDraft, StepParseError, ValidationError

from athena.service import AthenaService
from .intent_classifier import IntentClassifier
from .ollama_client import OllamaClient
from domains.hephaestus.service import HephaestusService
from domains.hermes.service import HermesService
from domains.apollo.service import ApolloService
from domains.dionysus.service import DionysusService
from domains.pluto.service import PlutoService


# Context Bounds for LLM Safety and Transparency
MAX_MEMORY_ITEMS = 5  # Max memories to inject
MAX_MEMORY_CHARS = 2000  # Max total characters for memory block
MAX_LLM_CONTEXT_CHARS = 8000  # Max prompt size before user warning
EXCERPT_MAX_CHARS = 200  # Max chars per memory or knowledge excerpt


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
    
    Policy awareness:
      Hestia has access to Artemis security policy via Kernel.
      Policy awareness only — enforcement occurs later.
      No behavior changes based on policy at this stage.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, kernel: Optional[Any] = None):
        config = config or {}
        
        self.intent_classifier = IntentClassifier()
        self.enable_llm = config.get("enable_llm", False)
        self.enable_memory = config.get("enable_memory", False)
        self.enable_athena = config.get("enable_athena", True)
        self._kernel = kernel  # Kernel reference for policy visibility
        
        # # LLM reasoning → plan
        # # No execution authority
        # # No autonomy
        # # Fail-closed
        self._plan_compiler = PlanCompiler(kernel=kernel)
        
        # Optional LLM client
        self.llm_client: Optional[OllamaClient] = None
        if self.enable_llm:
            self.llm_client = OllamaClient(
                base_url=config.get("ollama_url", "http://localhost:11434"),
                model=config.get("ollama_model", "mistral:latest"),
                timeout=config.get("ollama_timeout", 60)
            )
        
        # Memory service (Mnemosyne) - always initialized
        # BUG-2.1 FIX: Never None; always returns a service (possibly disabled)
        # Guarantee: memory_service.read() never raises AttributeError
        from mnemosyne.service import MnemosyneService
        from mnemosyne.service_config import MnemosyneConfig
        
        memory_config = MnemosyneConfig(
            enabled=self.enable_memory,
            db_path=config.get("memory_db_path", "./data/memory.db")
        )
        self.memory_service = MnemosyneService(config=memory_config)
        self.memory_store = None  # Backward compatibility
        # Expose the underlying store for backward compatibility
        if self.memory_service.memory_store:
            self.memory_store = self.memory_service.memory_store
        
        # Optional knowledge retriever (v0.1 knowledge system)
        self.knowledge_retriever = None
        if self.enable_athena:
            from athena.knowledge_store import KnowledgeStore
            self.knowledge_retriever = KnowledgeStore(
                store_path=config.get("knowledge_path", "./data/knowledge.json")
            )

        # Athena service (knowledge base search, read-only, intent-gated)
        from athena.config import AthenaConfig
        athena_config = AthenaConfig(
            enabled=config.get("enable_athena", False),
            data_dir=config.get("athena_data_dir", "./data/notes"),
            index_dir=config.get("athena_index_dir", "./.athena_index"),
        )
        self.athena = AthenaService(config=athena_config)
        
        # Hephaestus domain (code reasoning, deterministic)
        self.hephaestus = HephaestusService()
        
        # Hermes domain (text transformation, deterministic)
        self.hermes = HermesService()
        
        # Apollo domain (health/wellness information, deterministic)
        self.apollo = ApolloService()
        
        # Dionysus domain (music/art/culture information, deterministic)
        self.dionysus = DionysusService()
        
        # Pluto domain (financial/economic concepts information, deterministic)
        self.pluto = PlutoService()
        
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
    
    def current_security_posture(self) -> LockdownPolicy:
        """
        Get the current security policy from Artemis via Kernel.
        
        Policy awareness only — enforcement occurs later.
        This method returns policy information for inspection/logging,
        not for behavior modification.
        
        Returns:
            The current LockdownPolicy, or a safe default if unavailable
        """
        if self._kernel is None:
            # No kernel reference - return a permissive default
            from artemis.boundary import POLICY_SECURE
            return POLICY_SECURE
        
        # Simply return what Kernel knows - no enforcement here
        return self._kernel.get_security_policy()

    def current_security_summary(self) -> SecuritySummary:
        """
        Get the current security summary for user display.

        Artemis security UX
        Informational only
        No authority
        No side effects
        """
        if self._kernel is None:
            return SecuritySummary(
                state="UNKNOWN",
                explanation="Security posture unavailable. Execution status unknown.",
                last_transition_time="unknown",
                execution_allowed=False,
            )

        summary = self._kernel.inspect_security_summary()
        if summary is None:
            return SecuritySummary(
                state="UNKNOWN",
                explanation="Security posture unavailable. Execution status unknown.",
                last_transition_time="unknown",
                execution_allowed=False,
            )
        return summary

    def evaluate_approval_request(self, request: ApprovalRequest) -> tuple[bool, str]:
        """
        Evaluate approval request against security posture.

        Artemis security UX
        Informational only
        No authority
        No side effects
        """
        allowed, reason = validate_approval_request(request)
        state = request.security_summary.state

        if allowed:
            return True, reason

        explanation = f"{reason} Security state is {state}."
        return False, explanation
    
    async def process(self, user_input: str) -> AgentResponse:
        """
        Process input with optional LLM reasoning, memory, and domains.
        
        Flow:
        1. Classify intent (keyword matching)
        2. If intent is memory_query: Retrieve and format memories (NO LLM)
        3. If intent is knowledge_query: Run Athena lookup (NO LLM)
        4. If intent is hephaestus_query: Route to Hephaestus domain (NO LLM)
        5. If intent is hermes_query: Route to Hermes domain (NO LLM)
        6. If intent is apollo_query: Route to Apollo domain (NO LLM)
        7. If intent is dionysus_query: Route to Dionysus domain (NO LLM)
        8. If intent is pluto_query: Route to Pluto domain (NO LLM)
        9. Else if LLM enabled: Generate LLM response
        10. Else: Generate deterministic response
        
        Args:
            user_input: Raw text input from user
            
        Returns:
            AgentResponse with classified intent and response
        """
        # Classify intent
        intent = self.intent_classifier.classify(user_input)
        
        # Handle explicit memory query (NEVER goes through LLM)
        if intent == "memory_query":
            response_text = self._handle_memory_query()
            return AgentResponse(
                text=response_text,
                intent=intent,
                confidence=0.9
            )

        # Handle explicit knowledge query (NO LLM, read-only lookup)
        if intent == "knowledge_query":
            response_text = self._handle_knowledge_query(user_input)
            return AgentResponse(
                text=response_text,
                intent=intent,
                confidence=0.9
            )
        
        # Handle Hephaestus domain (code reasoning, NO LLM, deterministic)
        if intent == "hephaestus_query":
            response_text = self._handle_hephaestus_query(user_input)
            return AgentResponse(
                text=response_text,
                intent=intent,
                confidence=0.9
            )
        
        # Handle Hermes domain (text transformation, NO LLM, deterministic)
        if intent == "hermes_query":
            response_text = self._handle_hermes_query(user_input)
            return AgentResponse(
                text=response_text,
                intent=intent,
                confidence=0.9
            )
        
        # Handle Apollo domain (health/wellness information, NO LLM, deterministic)
        if intent == "apollo_query":
            response_text = self._handle_apollo_query(user_input)
            return AgentResponse(
                text=response_text,
                intent=intent,
                confidence=0.9
            )
        
        # Handle Dionysus domain (music/art/culture information, NO LLM, deterministic)
        if intent == "dionysus_query":
            response_text = self._handle_dionysus_query(user_input)
            return AgentResponse(
                text=response_text,
                intent=intent,
                confidence=0.9
            )
        
        # Handle Pluto domain (financial/economic concepts information, NO LLM, deterministic)
        if intent == "pluto_query":
            response_text = self._handle_pluto_query(user_input)
            return AgentResponse(
                text=response_text,
                intent=intent,
                confidence=0.9
            )
        
        # Handle Athena domain (knowledge base search, NO LLM, read-only)
        if intent == "athena_query":
            response_text = self._handle_athena_query(user_input)
            return AgentResponse(
                text=response_text,
                intent=intent,
                confidence=0.9
            )
        
        # Generate response (normal flow)
        if self.enable_llm and self._llm_initialized:
            response_text = await self._generate_llm_response(intent, user_input)
        else:
            response_text = self._generate_deterministic_response(intent, user_input)
        
        return AgentResponse(
            text=response_text,
            intent=intent,
            confidence=0.8
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

    def get_contextual_memory(self, limit: int = MAX_MEMORY_ITEMS) -> Tuple[Optional[str], bool]:
        """Return formatted memory block for LLM context with truncation tracking.
        
        Returns:
            (memory_block, was_truncated) where was_truncated indicates if memories or characters were capped
        """
        if not self.memory_store:
            return None, False

        try:
            # Cap by item count
            limit = min(limit, MAX_MEMORY_ITEMS)
            memories = self.memory_store.get_recent(count=limit)
            if not memories:
                return None, False

            lines = [
                "The following are notes the user explicitly asked you to consider.",
                "Do not infer beyond them.",
                ""
            ]

            total_chars = sum(len(line) for line in lines)
            truncated = False
            included_count = 0

            for i, memory in enumerate(memories, 1):
                timestamp = memory.timestamp[:19]
                line = f"{i}. [{timestamp}] {memory.content}"
                line_chars = len(line) + 1  # +1 for newline
                
                # Check if adding this memory would exceed character limit
                if total_chars + line_chars > MAX_MEMORY_CHARS:
                    truncated = True
                    break
                
                lines.append(line)
                total_chars += line_chars
                included_count += 1
            
            # Check if we had to skip memories
            if included_count < len(memories):
                truncated = True
                lines.append(f"\n[Note: Showing {included_count} of {len(memories)} memories due to size limits]")
            
            return "\n".join(lines), truncated

        except Exception:
            # Fail closed: if memory retrieval fails, do not inject anything
            return None, False
    
    def _handle_memory_query(self) -> str:
        """
        Handle explicit user request to see their memories.
        
        This method is ONLY called when user explicitly asks.
        Memories are NEVER automatically injected into responses.
        
        Returns:
            Formatted list of memories or message if none exist
        """
        if not self.memory_service or not self.memory_service.config.enabled:
            return "Memory is not enabled. Use --memory flag to enable it."
        
        try:
            # Use MnemosyneService to read recent memories
            memories_text = self.memory_service.read(limit=10)
            
            if not memories_text:
                return "I don't have any memories saved yet."
            
            # Format memories as a numbered list
            lines = ["You asked me to remember:"]
            for i, memory_content in enumerate(memories_text, 1):
                lines.append(f"  {i}. {memory_content}")
            
            # Add count if there are more
            stats = self.memory_service.stats()
            total = stats.get("memory_count", 0)
            if total > len(memories_text):
                lines.append(f"\n(Showing {len(memories_text)} of {total} total memories)")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error retrieving memories: {e}"

    def _extract_knowledge_query(self, user_input: str) -> str:
        """Extract the search string after the trigger phrase."""
        text_lower = user_input.lower()
        for pattern in getattr(self.intent_classifier, "knowledge_patterns", []):
            if pattern in text_lower:
                return user_input.lower().split(pattern, 1)[-1].strip() or user_input
        return user_input

    def _handle_knowledge_query(self, user_input: str) -> str:
        """Handle explicit user request to search knowledge (NO LLM)."""
        if not self.knowledge_retriever:
            return "Knowledge retrieval is disabled."

        query = self._extract_knowledge_query(user_input)
        results = self.knowledge_retriever.search(query, limit=5)

        if not results:
            return "I don't have any knowledge entries matching that."

        lines = ["Found knowledge entries:"]
        for idx, item in enumerate(results, 1):
            excerpt = self.knowledge_retriever.excerpt(item, query)
            lines.append(f"  {idx}. {item.title}")
            lines.append(f"     Excerpt: {excerpt}")

        return "\n".join(lines)
    
    def _handle_hephaestus_query(self, user_input: str) -> str:
        """
        Handle code reasoning request via Hephaestus domain.
        
        Hephaestus is a deterministic, read-only domain that provides:
        - Debugging assistance
        - Design guidance
        - Refactoring suggestions
        - Code review insights
        
        NO side effects (no LLM, no memory writes, no planning).
        
        Returns:
            str: Domain response with reasoning and suggestions
        """
        try:
            response = self.hephaestus.handle(user_input)
            return response
        except Exception as e:
            return f"Code reasoning temporarily unavailable: {e}"
    
    def _handle_hermes_query(self, user_input: str) -> str:
        """
        Handle text transformation request via Hermes domain.
        
        Hermes is a deterministic, read-only domain that provides:
        - Text rewriting guidance
        - Rephrasing suggestions
        - Summarization techniques
        - Simplification strategies
        - Clarity improvements
        
        NO side effects (no LLM, no memory writes, no planning).
        
        Returns:
            str: Domain response with transformation guidance
        """
        try:
            response = self.hermes.handle(user_input)
            return response
        except Exception as e:
            return f"Text transformation temporarily unavailable: {e}"
    
    def _handle_apollo_query(self, user_input: str) -> str:
        """
        Handle health/wellness information request via Apollo domain.
        
        Apollo is a deterministic, read-only domain that provides:
        - Health and fitness information
        - Wellness definitions
        - Educational content
        - Safety disclaimers
        
        STRICTLY DOES NOT provide:
        - Medical diagnosis
        - Treatment advice
        - Personalized health guidance
        - Mental health counseling
        
        NO side effects (no LLM, no memory writes, no planning).
        
        Returns:
            str: Domain response with health information or explicit refusal
        """
        try:
            response = self.apollo.handle(user_input)
            return response
        except Exception as e:
            return f"Health information temporarily unavailable: {e}"
    
    def _handle_dionysus_query(self, user_input: str) -> str:
        """
        Handle music/art/culture information request via Dionysus domain.
        
        Dionysus is a deterministic, read-only domain that provides:
        - Music genre explanations
        - Art style descriptions
        - Cultural information
        - Entertainment concepts
        - Party vibe descriptions
        
        STRICTLY DOES NOT provide:
        - Creative generation (songs, poems, lyrics, stories)
        - Emotional or mental health advice
        - Substance use advice
        - Lifestyle coaching
        - Personal recommendations
        
        NO side effects (no LLM, no memory writes, no planning).
        
        Returns:
            str: Domain response with cultural information or explicit refusal
        """
        try:
            response = self.dionysus.handle(user_input)
            return response
        except Exception as e:
            return f"Cultural information temporarily unavailable: {e}"
    
    def _handle_pluto_query(self, user_input: str) -> str:
        """
        Handle financial/economic concepts request via Pluto domain.
        
        Pluto is a deterministic, read-only domain that provides:
        - Financial concept definitions
        - Economic mechanism explanations
        - Historical/theoretical context
        - Neutral descriptions of economic systems
        
        STRICTLY DOES NOT provide:
        - Advice ("You should...")
        - Recommendations ("Invest in...")
        - Numbers, calculations, or projections
        - Risk assessment or modeling
        - Personal finance guidance
        - Trading or investing strategy
        - Crypto guidance
        - Tax strategy
        
        NO side effects (no LLM, no memory writes, no planning).
        
        Returns:
            str: Domain response with concept explanation or explicit refusal
        """
        try:
            response = self.pluto.handle(user_input)
            return response
        except Exception as e:
            return f"Financial concept information temporarily unavailable: {e}"
    
    def _handle_athena_query(self, user_input: str) -> str:
        """
        Handle knowledge base search via Athena service.
        
        Athena is a read-only, intent-gated vector search system that:
        - Retrieves documents from user's local knowledge base
        - Returns source excerpts with page numbers and file names
        - Performs deterministic vector similarity search
        
        STRICTLY DOES NOT:
        - Call LLM (returns raw context only)
        - Write to memory
        - Run background indexing
        - Activate without explicit user intent
        - Automatically retrieve or summarize
        
        Flow:
        1. User asks: "search my notes for X"
        2. Athena performs vector search
        3. Returns matching excerpts with metadata
        4. User decides if LLM should generate answer from context
        
        NO side effects (read-only, no LLM, no memory writes, no autonomy).
        
        Returns:
            str: Formatted source excerpts or "no results" message
        """
        try:
            if not self.athena.config.enabled:
                return "Athena knowledge base search is disabled."
            
            result = self.athena.query(user_input, top_k=5)
            
            if not result.has_sources:
                return (
                    "No matching documents found in knowledge base. "
                    "Make sure PDFs are indexed using explicit ingestion commands."
                )
            
            # Format sources for display
            lines = [f"Found {result.source_count} matching sources:\n"]
            for i, source in enumerate(result.sources, 1):
                page_str = f", page {source.page_number}" if source.page_number else ""
                lines.append(
                    f"{i}. [{source.file_name}{page_str}] "
                    f"({source.similarity_score:.2%} match)\n"
                    f"   {source.text[:150]}...\n"
                )
            
            return "".join(lines).strip()
            
        except Exception as e:
            return f"Knowledge base search temporarily unavailable: {e}"
    
    def should_offer_memory(self, user_input: str, intent: str) -> bool:
        """
        Decide if this input is worth remembering.
        
        Simple heuristic: Remember if it's a statement (not a greeting/question/memory_query).
        """
        if not self.enable_memory:
            return False
        
        # NEVER offer to remember memory, knowledge, or domain queries themselves
        if intent in ["memory_query", "knowledge_query", "hephaestus_query", "hermes_query", "apollo_query", "dionysus_query", "pluto_query", "athena_query"]:
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
        if not self.memory_service or not self.memory_service.config.enabled:
            return False
        
        try:
            # Use MnemosyneService.write() for explicit memory writing
            return self.memory_service.write(
                content=user_input,
                memory_type=intent,
                metadata={"timestamp": datetime.now().isoformat()}
            )
            
        except Exception as e:
            print(f"ERROR: Failed to save memory: {e}")
            return False
    
    async def _generate_llm_response(self, intent: str, user_input: str) -> str:
        """Generate response using LLM with strict context bounds and transparency."""
        if not self.llm_client:
            return self._generate_deterministic_response(intent, user_input)
        
        # Construct system prompt based on intent
        system_prompt = self._build_system_prompt(intent)
        prompt = user_input
        truncation_notice = ""

        # Only inject memory when explicitly requested
        if self.should_use_memory_for_context(user_input):
            memory_context, was_truncated = self.get_contextual_memory(limit=MAX_MEMORY_ITEMS)
            if memory_context:
                prompt = f"{memory_context}\n\nUser request: {user_input}"
                if was_truncated:
                    truncation_notice = "\n[Note: Memory context was truncated to fit size limits.]"
        
        # Enforce total context size limit with transparency
        prompt_size = len(prompt) + len(system_prompt)
        if prompt_size > MAX_LLM_CONTEXT_CHARS:
            # Notify user that context is being bounded
            truncation_notice += f"\n[Note: Context size ({prompt_size} chars) exceeds safe limit ({MAX_LLM_CONTEXT_CHARS} chars). Limiting prompt.]"
            # Truncate user request if necessary (preserve system context)
            max_user_size = MAX_LLM_CONTEXT_CHARS - len(system_prompt) - 100
            if "User request:" in prompt:
                prefix, user_part = prompt.rsplit("User request:", 1)
                prompt = prefix + "User request:" + user_part[:max_user_size]
            else:
                prompt = prompt[:max_user_size]
        
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt
            )
            # Append truncation notice if context was limited
            if truncation_notice:
                response += truncation_notice
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

    # ========================================================================
    # PLAN COMPILATION
    # ========================================================================
    # LLM reasoning → plan
    # No execution authority
    # No autonomy
    # Fail-closed

    def compile_plan(
        self,
        intent: str,
        llm_output: str,
        draft_id: Optional[str] = None,
    ) -> Tuple[Optional[PlanDraft], str]:
        """
        Compile LLM reasoning into a strict, executable plan.

        # LLM reasoning → plan
        # No execution authority
        # No autonomy
        # Fail-closed

        Args:
            intent: User's original intent
            llm_output: Raw LLM text (must use explicit step markers)
            draft_id: Optional draft identifier (auto-generated if not provided)

        Returns:
            (PlanDraft or None, message)
            - PlanDraft: Successfully compiled plan (immutable)
            - None: Compilation failed (message contains reason)
            - message: Status or error explanation (human-readable)
        """
        if not draft_id:
            from uuid import uuid4
            draft_id = str(uuid4())

        # Get current security summary (inspection only, no mutation)
        security_snapshot = {}
        if self._kernel:
            try:
                summary = self._kernel.inspect_security_state()
                if summary:
                    security_snapshot = {
                        "state": getattr(summary, "state", "unknown"),
                        "explanation": getattr(summary, "explanation", ""),
                        "execution_allowed": getattr(summary, "execution_allowed", False),
                    }
            except Exception:
                # Fail closed: if inspection fails, use empty snapshot
                pass

        try:
            # Compile plan
            plan = self._plan_compiler.compile(
                intent=intent,
                llm_output=llm_output,
                security_summary=security_snapshot,
                draft_id=draft_id,
            )
            return plan, f"Plan compiled successfully ({plan.step_count()} steps)"

        except StepParseError as e:
            return None, f"Parse error: {e}"

        except ValidationError as e:
            return None, f"Validation error: {e}"

        except Exception as e:
            # Fail closed: unexpected errors treated as compilation failures
            return None, f"Compilation error: {e}"

    def get_plan_draft(self, plan: PlanDraft) -> Dict[str, Any]:
        """
        Export plan draft as structured dict (immutable).

        # LLM reasoning → plan
        # No execution authority
        # No autonomy
        # Fail-closed

        Args:
            plan: Compiled PlanDraft

        Returns:
            Immutable dict representation
        """
        return plan.to_dict()

    # ========================================================================
    # HESTIA AUTHORITY FLOW - UI LAYER
    # ========================================================================
    # UX only
    # No authority
    # No execution
    # No autonomy

    def present_plan(self, plan_draft: PlanDraft) -> Any:
        """
        Convert PlanDraft into human-readable PlanPresentation.

        # UX only
        # No authority
        # No execution
        # No autonomy

        This method has NO execution authority.
        It only converts a plan into human-readable form.

        Args:
            plan_draft: PlanDraft (immutable)

        Returns:
            PlanPresentation (immutable, human-readable)
        """
        from hestia.ui_layer import HestiaUIBoundary
        return HestiaUIBoundary.present_plan(plan_draft)

    def request_approval(self, plan_draft: PlanDraft) -> Tuple[bool, str]:
        """
        Request user approval for a plan.

        # UX only
        # No authority
        # No execution
        # No autonomy

        This method has NO approval authority.
        It only prompts the user and records their response.
        The actual decision belongs entirely to the user.

        Args:
            plan_draft: PlanDraft (immutable)

        Returns:
            (approved: bool, reason: str)
        """
        from hestia.ui_layer import HestiaUIBoundary
        plan_presentation = HestiaUIBoundary.present_plan(plan_draft)
        return HestiaUIBoundary.request_approval_from_user(plan_presentation)

    def explain_rejection(self, reason: str) -> str:
        """
        Build human-readable explanation for a rejected plan.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Args:
            reason: The reason the plan was rejected

        Returns:
            str - Human-readable explanation
        """
        from hestia.ui_layer import HestiaUIBoundary
        return HestiaUIBoundary.explain_rejection(reason)

    def display_authority_boundaries(self) -> str:
        """
        Display what Hestia can and cannot do.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Returns:
            str - Factual description of Hestia's boundaries
        """
        from hestia.ui_layer import HestiaUIBoundary
        return HestiaUIBoundary.display_authority_constraints()

    # =========================================================================
    # LIVE MODE GATE UX METHODS (Step 18)
    # =========================================================================
    # These methods expose the live mode gate to the human user.
    # They provide visibility and control over the execution authority switch.
    # NO autonomy, NO automation, NO background execution.
    # =========================================================================

    def display_live_mode_status(self, live_mode_gate: Any) -> str:
        """
        Display current live mode status.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Shows:
        - Current gate state (DRY_RUN or LIVE)
        - What this means for execution
        - Recent transition history

        Args:
            live_mode_gate: LiveModeGate instance

        Returns:
            str - Human-readable status display
        """
        if not live_mode_gate:
            return "[LIVE MODE GATE NOT CONFIGURED]\nNo execution gate is active.\n"

        state = live_mode_gate.get_state()
        state_name = state.value

        status_lines = []
        status_lines.append("=" * 60)
        status_lines.append("LIVE MODE GATE STATUS")
        status_lines.append("=" * 60)
        status_lines.append(f"Current State: {state_name}")
        status_lines.append("")

        if live_mode_gate.is_dry_run():
            status_lines.append("EXECUTION: BLOCKED")
            status_lines.append("All approved plans will be validated but NOT executed.")
            status_lines.append("This is the SAFE default state.")
        else:
            status_lines.append("EXECUTION: ENABLED")
            status_lines.append("Approved plans WILL be executed.")
            status_lines.append("Changes WILL affect your system.")

        # Show recent transitions
        history = live_mode_gate.get_transition_history()
        if history:
            status_lines.append("")
            status_lines.append("Recent Transitions:")
            for transition in history[-3:]:  # Last 3 transitions
                ts = transition.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                auto_flag = " [AUTO]" if transition.automatic else ""
                status_lines.append(
                    f"  {ts}: {transition.from_state.value} → "
                    f"{transition.to_state.value}{auto_flag}"
                )
                status_lines.append(f"    Reason: {transition.reason}")
                if transition.user_identity:
                    status_lines.append(f"    User: {transition.user_identity}")

        status_lines.append("=" * 60)
        return "\n".join(status_lines)

    def explain_live_mode_consequences(self) -> str:
        """
        Explain what enabling live mode means.

        # UX only
        # No authority
        # No execution
        # No autonomy

        Provides clear explanation of:
        - What DRY_RUN means (safe)
        - What LIVE means (dangerous)
        - Security implications
        - Recommended practices

        Returns:
            str - Human-readable explanation
        """
        explanation = """
========================================================================
LIVE MODE GATE: CONSEQUENCES AND RISKS
========================================================================

DRY_RUN MODE (Default - SAFE):
- All approved plans are validated but NOT executed
- You can test the governance loop without risk
- No changes are made to your system
- No commands are run
- No files are created/modified/deleted
- This is the FAIL-CLOSED default state

LIVE MODE (DANGEROUS):
- Approved plans WILL be executed
- Commands WILL be run on your system
- Files WILL be created/modified/deleted
- Changes MAY be irreversible
- Security risks increase significantly
- You are responsible for all consequences

SECURITY INTEGRATION:
- If security state degrades to COMPROMISED or LOCKDOWN,
  the gate will AUTOMATICALLY revert to DRY_RUN
- This prevents execution during security incidents
- Manual re-enable required after security recovery

RECOMMENDED PRACTICE:
1. Start in DRY_RUN mode (default)
2. Test your plans thoroughly
3. Review approval decisions
4. Enable LIVE mode only when:
   - You understand the plan completely
   - You trust the approval process
   - You accept all risks
5. Disable LIVE mode immediately after execution
6. Never leave LIVE mode enabled unattended

REMEMBER:
- Live mode is NOT a replacement for careful review
- Live mode is NOT safe for untested plans
- Live mode is NOT for experimentation
- Live mode is opt-in, explicit, and audited

========================================================================
        """
        return explanation.strip()

    def enable_live_mode(
        self,
        live_mode_gate: Any,
        reason: str,
        user_identity: str = "anonymous",
    ) -> Tuple[bool, str]:
        """
        Enable live mode (allow execution).

        # UX wrapper only
        # No authority beyond gate control
        # No execution
        # No autonomy

        This method wraps the gate's enable_live() method and provides
        user-friendly feedback.

        Args:
            live_mode_gate: LiveModeGate instance
            reason: WHY you are enabling live mode (required)
            user_identity: WHO is enabling live mode (required)

        Returns:
            (success: bool, message: str)
        """
        if not live_mode_gate:
            return False, "ERROR: No live mode gate configured"

        if not reason or not reason.strip():
            return False, "ERROR: Reason is required to enable live mode"

        if not user_identity or not user_identity.strip():
            return False, "ERROR: User identity is required to enable live mode"

        # Attempt to enable
        success, message = live_mode_gate.enable_live(
            reason=reason.strip(),
            user_identity=user_identity.strip(),
        )

        if success:
            return True, f"✓ LIVE MODE ENABLED\n{message}\n\nWARNING: Execution is now ACTIVE."
        else:
            return False, f"✗ LIVE MODE NOT ENABLED\n{message}"

    def disable_live_mode(
        self,
        live_mode_gate: Any,
        reason: str,
        user_identity: str = "anonymous",
    ) -> Tuple[bool, str]:
        """
        Disable live mode (block execution).

        # UX wrapper only
        # No authority beyond gate control
        # No execution
        # No autonomy

        This method wraps the gate's disable_live() method and provides
        user-friendly feedback.

        Args:
            live_mode_gate: LiveModeGate instance
            reason: WHY you are disabling live mode (required)
            user_identity: WHO is disabling live mode (required)

        Returns:
            (success: bool, message: str)
        """
        if not live_mode_gate:
            return False, "ERROR: No live mode gate configured"

        if not reason or not reason.strip():
            return False, "ERROR: Reason is required to disable live mode"

        if not user_identity or not user_identity.strip():
            return False, "ERROR: User identity is required to disable live mode"

        # Attempt to disable
        success, message = live_mode_gate.disable_live(
            reason=reason.strip(),
            user_identity=user_identity.strip(),
            automatic=False,
        )

        if success:
            return True, f"✓ LIVE MODE DISABLED\n{message}\n\nExecution is now BLOCKED (safe)."
        else:
            return False, f"✗ LIVE MODE STATE UNCHANGED\n{message}"

    # =========================================================================
    # EXECUTION OBSERVABILITY UX METHODS (Step 19)
    # =========================================================================
    # These methods display execution results and rollback guidance.
    # NO automation, NO retries, NO rollback execution.
    # =========================================================================

    def display_execution_summary(self, execution_record: Any) -> str:
        """
        Display execution summary clearly.

        # Post-execution inspection only
        # No automatic recovery
        # No retries
        # Fail-closed

        Shows:
        - Execution ID and status
        - Duration
        - Steps executed
        - Security state before/after
        - Any failures

        Args:
            execution_record: ExecutionRecord from artemis.execution_observability

        Returns:
            str - Human-readable summary
        """
        if not execution_record:
            return "[NO EXECUTION RECORD]\n"

        summary_lines = []
        summary_lines.append("=" * 70)
        summary_lines.append("EXECUTION SUMMARY")
        summary_lines.append("=" * 70)
        summary_lines.append("")

        # Status and ID
        summary_lines.append(f"Execution ID: {execution_record.execution_id}")
        summary_lines.append(f"Plan ID: {execution_record.plan_id}")
        summary_lines.append(f"Live Mode: {execution_record.live_mode_state}")
        summary_lines.append(f"Status: {execution_record.status.value}")
        summary_lines.append("")

        # Duration
        if execution_record.timestamp_end:
            duration = execution_record.timestamp_end - execution_record.timestamp_start
            summary_lines.append(f"Duration: {duration.total_seconds():.2f} seconds")
            summary_lines.append(f"Started: {execution_record.timestamp_start.strftime('%Y-%m-%d %H:%M:%S')}")
            summary_lines.append(f"Ended: {execution_record.timestamp_end.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            summary_lines.append(f"Started: {execution_record.timestamp_start.strftime('%Y-%m-%d %H:%M:%S')}")
        summary_lines.append("")

        # Steps
        if execution_record.step_events:
            summary_lines.append(f"Steps executed: {len(execution_record.step_events)}")
            completed_count = sum(1 for e in execution_record.step_events 
                                 if e.event_type.value == "step_completed")
            failed_count = sum(1 for e in execution_record.step_events 
                              if e.event_type.value == "step_failed")
            summary_lines.append(f"  ✓ Completed: {completed_count}")
            if failed_count > 0:
                summary_lines.append(f"  ✗ Failed: {failed_count}")
        else:
            summary_lines.append("Steps executed: 0")
        summary_lines.append("")

        # Security
        summary_lines.append("Security State:")
        summary_lines.append(f"  Before: {execution_record.security_snapshot_pre.security_state}")
        if execution_record.security_snapshot_post:
            summary_lines.append(f"  After: {execution_record.security_snapshot_post.security_state}")
        summary_lines.append("")

        # Completion reason
        if execution_record.completion_reason:
            summary_lines.append(f"Reason: {execution_record.completion_reason}")
            summary_lines.append("")

        summary_lines.append("=" * 70)
        return "\n".join(summary_lines)

    def show_irreversible_actions(self, execution_record: Any) -> str:
        """
        Show which actions were irreversible.

        # Post-execution inspection only
        # No automatic recovery
        # No retries
        # Fail-closed

        Args:
            execution_record: ExecutionRecord

        Returns:
            str - List of irreversible actions
        """
        if not execution_record or not execution_record.step_events:
            return "[NO STEPS EXECUTED]\n"

        lines = []
        lines.append("=" * 70)
        lines.append("IRREVERSIBLE ACTIONS")
        lines.append("=" * 70)
        lines.append("")

        lines.append("Steps that CANNOT be automatically undone:")
        lines.append("")

        for i, event in enumerate(execution_record.step_events, 1):
            if event.event_type.value == "step_completed":
                lines.append(f"{i}. Step {event.step_index}: {event.step_name}")
                lines.append(f"   Completed at: {event.timestamp.strftime('%H:%M:%S')}")
                lines.append("")

        lines.append("=" * 70)
        lines.append("Note: ALL executed steps may have side effects.")
        lines.append("Manual verification is required before attempting rollback.")
        lines.append("=" * 70)
        return "\n".join(lines)

    def show_rollback_guidance(self, rollback_scaffold: Any) -> str:
        """
        Show rollback guidance (NOT EXECUTED).

        # Post-execution inspection only
        # No automatic recovery
        # No retries
        # Fail-closed

        Args:
            rollback_scaffold: RollbackScaffold from artemis.execution_observability

        Returns:
            str - Rollback guidance (human-readable)
        """
        if not rollback_scaffold:
            return "[NO ROLLBACK GUIDANCE]\n"

        return rollback_scaffold.to_summary()

    def confirm_manual_rollback(self, rollback_scaffold: Any) -> Tuple[bool, str]:
        """
        Request user confirmation for manual rollback.

        # Post-execution inspection only
        # No automatic recovery
        # No retries
        # Fail-closed

        This method prompts the user and records their response.
        It does NOT execute rollback - only confirms intent.

        Args:
            rollback_scaffold: RollbackScaffold

        Returns:
            (confirmed: bool, reason: str)
        """
        if not rollback_scaffold:
            return False, "ERROR: No rollback scaffold provided"

        if not rollback_scaffold.is_rollback_possible:
            return False, f"Rollback not possible: {rollback_scaffold.reason}"

        # Display guidance
        guidance = rollback_scaffold.to_summary()
        print(guidance)
        print()

        # Request confirmation
        print("=" * 70)
        print("MANUAL ROLLBACK CONFIRMATION")
        print("=" * 70)
        print()
        print("⚠️  WARNING: Rollback will NOT be executed automatically.")
        print("You are responsible for all manual rollback steps.")
        print()
        print("Do you want to proceed with MANUAL rollback?")
        print("Type 'yes' to confirm, anything else to cancel: ", end="")

        user_input = input().strip().lower()

        if user_input == "yes":
            return True, "User confirmed - Ready for manual rollback (NOT EXECUTED)"
        else:
            return False, "User declined manual rollback"
    # ================================================================================
    # GUIDANCE MODE (Step 20)
    # ================================================================================
    # Guidance only
    # No execution authority
    # No memory mutation
    # No autonomy
    # Fail-closed

    def display_guidance_event(self, guidance_event: Any) -> str:
        """
        Display guidance event to operator.

        # Guidance only
        # No execution
        # Advisory only

        Args:
            guidance_event: GuidanceEvent from artemis.guidance_mode

        Returns:
            str - Formatted guidance (human-readable)
        """
        if not guidance_event:
            return "[NO GUIDANCE]\n"

        output = []
        output.append("=" * 70)
        output.append(" GUIDANCE — NO ACTION TAKEN")
        output.append("=" * 70)
        output.append("")
        
        output.append(f"Event ID: {guidance_event.event_id}")
        output.append(f"Type: {guidance_event.trigger_type.value}")
        output.append(f"Confidence: {guidance_event.confidence_level.value.upper()}")
        output.append(f"Time: {guidance_event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("")
        
        output.append("OBSERVATION:")
        output.append(f"  {guidance_event.observation}")
        output.append("")
        
        output.append("IMPLICATION:")
        output.append(f"  {guidance_event.implication}")
        output.append("")
        
        if guidance_event.suggested_actions:
            output.append("POSSIBLE ACTIONS (advisory only):")
            for action in guidance_event.suggested_actions:
                output.append(f"  • {action}")
            output.append("")
        
        if guidance_event.risk_notes:
            output.append("RISKS & CAVEATS:")
            for risk in guidance_event.risk_notes:
                output.append(f"  ⚠ {risk}")
            output.append("")
        
        output.append("=" * 70)
        output.append("This is ADVISORY only. No action has been taken.")
        output.append("=" * 70)
        
        return "\n".join(output)

    def show_draft_plan(self, draft_plan: Any) -> str:
        """
        Display proposed draft plan to operator.

        # Guidance only
        # Not executed
        # Operator review required

        Args:
            draft_plan: PlanDraft from artemis.guidance_mode

        Returns:
            str - Formatted draft (human-readable)
        """
        if not draft_plan:
            return "[NO DRAFT PLAN]\n"

        output = []
        output.append("=" * 70)
        output.append(" PROPOSED DRAFT PLAN — ADVISORY ONLY")
        output.append("=" * 70)
        output.append("")
        
        output.append(f"Draft ID: {draft_plan.draft_id}")
        output.append(f"Based on: {draft_plan.guidance_event_id}")
        output.append("")
        
        output.append(f"Title: {draft_plan.title}")
        output.append(f"Description: {draft_plan.description}")
        output.append("")
        
        output.append("RATIONALE:")
        output.append(f"  {draft_plan.rationale}")
        output.append("")
        
        if draft_plan.proposed_steps:
            output.append("PROPOSED STEPS:")
            for step in draft_plan.proposed_steps:
                step_order = step.get("order", "?")
                step_suggestion = step.get("suggestion", "")
                output.append(f"  {step_order}. {step_suggestion}")
            output.append("")
        
        if draft_plan.risks:
            output.append("RISKS:")
            for risk in draft_plan.risks:
                output.append(f"  ⚠ {risk}")
            output.append("")
        
        output.append("=" * 70)
        output.append("This plan has NOT been executed.")
        output.append("Operator approval required before any action.")
        output.append("=" * 70)
        
        return "\n".join(output)

    def guidance_prompt(self, guidance_event: Any, draft_plan: Optional[Any] = None) -> Tuple[str, str]:
        """
        Prompt operator for guidance response.

        # Guidance only
        # No execution
        # Operator choice required

        Args:
            guidance_event: GuidanceEvent
            draft_plan: Optional PlanDraft

        Returns:
            (response: str, reason: str)
            response: "dismiss", "ask_more", or "draft_plan"
        """
        if not guidance_event:
            return "dismiss", "No guidance event provided"

        print()
        print("=" * 70)
        print(" GUIDANCE RESPONSE OPTIONS")
        print("=" * 70)
        print()
        print("1. Dismiss      - Acknowledge and discard guidance")
        print("2. Ask More     - Request additional context/analysis")
        print("3. Draft Plan   - Ask Hestia to draft a plan (if available)")
        print()
        print("Choose (1/2/3) or press Enter to dismiss: ", end="")
        
        choice = input().strip().lower()
        
        if choice in ("1", "dismiss", "d"):
            return "dismiss", "Operator dismissed guidance"
        elif choice in ("2", "ask_more", "a"):
            return "ask_more", "Operator requested more analysis"
        elif choice in ("3", "draft_plan", "draft"):
            if draft_plan:
                return "draft_plan", "Operator approved draft plan review"
            else:
                return "dismiss", "No draft plan available"
        else:
            return "dismiss", "No response (default dismiss)"