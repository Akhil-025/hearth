"""
Ollama Client - LLM interface implementation.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from pydantic import BaseModel, Field

from ..shared.logging.structured_logger import StructuredLogger


class LLMRequest(BaseModel):
    """LLM request model."""
    prompt: str
    system_prompt: Optional[str] = None
    model: str = "llama2:7b"
    temperature: float = Field(ge=0.0, le=2.0, default=0.7)
    max_tokens: int = Field(ge=1, le=8192, default=2048)
    top_p: float = Field(ge=0.0, le=1.0, default=0.9)
    stream: bool = False
    context: Optional[List[int]] = None


class LLMResponse(BaseModel):
    """LLM response model."""
    response: str
    model: str
    created_at: str
    done: bool
    total_duration: float
    load_duration: float
    prompt_eval_count: int
    prompt_eval_duration: float
    eval_count: int
    eval_duration: float
    context: Optional[List[int]] = None
    
    # Extended fields for HEARTH
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    reasoning: Optional[str] = None
    actions: Optional[List[Dict[str, Any]]] = None
    citations: Optional[List[Dict[str, Any]]] = None


class OllamaClient:
    """
    Ollama LLM client with structured prompting.
    
    Features:
    - Structured JSON responses
    - Action extraction
    - Confidence scoring
    - Request/response logging
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.logger = StructuredLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self.available_models: List[str] = []
        
        # Prompt templates
        self.system_prompt = """You are Hestia, a personal cognitive assistant.
        Your responses must be structured, actionable, and precise.
        
        RULES:
        1. Always respond in valid JSON format
        2. Include confidence score (0.0-1.0)
        3. Extract actionable items when appropriate
        4. Cite relevant knowledge when applicable
        5. Never fabricate information
        6. Acknowledge uncertainty when appropriate
        
        RESPONSE FORMAT:
        {
            "response": "Your natural language response",
            "confidence": 0.95,
            "reasoning": "Brief explanation of your reasoning",
            "actions": [
                {
                    "type": "action_type",
                    "parameters": {...},
                    "confidence": 0.9
                }
            ],
            "citations": [
                {
                    "source": "knowledge_source",
                    "relevance": 0.95,
                    "excerpt": "relevant text"
                }
            ]
        }"""
    
    async def initialize(self) -> None:
        """Initialize the client session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300)
        )
        
        # Check available models
        try:
            await self._refresh_available_models()
            self.logger.info(
                "Ollama client initialized",
                base_url=self.base_url,
                available_models=self.available_models
            )
        except Exception as e:
            self.logger.error(
                "Failed to initialize Ollama client",
                error=str(e)
            )
            raise
    
    async def cleanup(self) -> None:
        """Cleanup client session."""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.debug("Ollama client cleaned up")
    
    async def health_check(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200
        except Exception:
            return False
    
    async def _refresh_available_models(self) -> None:
        """Refresh list of available models."""
        if not self.session:
            raise RuntimeError("Client not initialized")
        
        async with self.session.get(f"{self.base_url}/api/tags") as response:
            if response.status == 200:
                data = await response.json()
                self.available_models = [model["name"] for model in data.get("models", [])]
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from Ollama."""
        if not self.session:
            raise RuntimeError("Client not initialized")
        
        self.logger.debug(
            "Generating LLM response",
            model=request.model,
            temperature=request.temperature
        )
        
        # Prepare request payload
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "system": request.system_prompt or self.system_prompt,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "num_predict": request.max_tokens
            },
            "stream": request.stream
        }
        
        if request.context:
            payload["context"] = request.context
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama API error: {error_text}")
                
                result = await response.json()
                
                # Parse response
                llm_response = LLMResponse(
                    response=result.get("response", ""),
                    model=result.get("model", request.model),
                    created_at=result.get("created_at", ""),
                    done=result.get("done", True),
                    total_duration=result.get("total_duration", 0) / 1e9,  # Convert to seconds
                    load_duration=result.get("load_duration", 0) / 1e9,
                    prompt_eval_count=result.get("prompt_eval_count", 0),
                    prompt_eval_duration=result.get("prompt_eval_duration", 0) / 1e9,
                    eval_count=result.get("eval_count", 0),
                    eval_duration=result.get("eval_duration", 0) / 1e9,
                    context=result.get("context")
                )
                
                # Try to parse structured response
                await self._parse_structured_response(llm_response)
                
                end_time = asyncio.get_event_loop().time()
                processing_time = end_time - start_time
                
                self.logger.debug(
                    "LLM response generated",
                    model=llm_response.model,
                    eval_count=llm_response.eval_count,
                    eval_duration=llm_response.eval_duration,
                    total_time=processing_time,
                    confidence=llm_response.confidence
                )
                
                return llm_response
                
        except Exception as e:
            self.logger.error(
                "LLM generation failed",
                error=str(e),
                model=request.model
            )
            raise
    
    async def _parse_structured_response(self, response: LLMResponse) -> None:
        """Attempt to parse structured JSON from response."""
        try:
            # Look for JSON block in response
            text = response.response.strip()
            
            # Try to find JSON object
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                data = json.loads(json_str)
                
                # Update response with structured data
                response.response = data.get("response", response.response)
                response.confidence = data.get("confidence", response.confidence)
                response.reasoning = data.get("reasoning")
                response.actions = data.get("actions")
                response.citations = data.get("citations")
                
                # Validate actions structure
                if response.actions:
                    for action in response.actions:
                        if "type" not in action:
                            self.logger.warning("Invalid action structure", action=action)
                            response.actions = None
                            break
        except (json.JSONDecodeError, ValueError) as e:
            # Response is not structured JSON, which is acceptable
            pass
    
    async def generate_embedding(self, text: str, model: str = "llama2:7b") -> List[float]:
        """Generate embeddings for text."""
        if not self.session:
            raise RuntimeError("Client not initialized")
        
        payload = {
            "model": model,
            "prompt": text
        }
        
        async with self.session.post(
            f"{self.base_url}/api/embeddings",
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Embedding generation failed: {error_text}")
            
            result = await response.json()
            return result.get("embedding", [])
    
    async def list_models(self) -> List[str]:
        """List available models."""
        if not self.available_models:
            await self._refresh_available_models()
        return self.available_models.copy()