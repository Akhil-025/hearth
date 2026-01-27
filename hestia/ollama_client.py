"""
HEARTH Ollama Client - Minimal LLM Interface (v0.1)

Pure function: text input → text output
No state, no logging, no complex prompting.
"""
from __future__ import annotations

import asyncio
from typing import Optional

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class OllamaClient:
    """
    Minimal Ollama client for LLM reasoning.
    
    Pure function wrapper around Ollama API.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "mistral:latest",
        timeout: int = 60
    ):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not installed. Run: pip install aiohttp")
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
    
    async def cleanup(self) -> None:
        """Cleanup HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def is_available(self) -> bool:
        """Check if Ollama is reachable."""
        if not self.session:
            return False
        
        try:
            async with self.session.get(
                f"{self.base_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text from prompt.
        
        Pure function: prompt → response text
        
        Args:
            prompt: User input text
            system_prompt: Optional system context
            
        Returns:
            Generated text response
            
        Raises:
            RuntimeError: If Ollama is unavailable or request fails
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama API error ({response.status}): {error_text}")
                
                result = await response.json()
                return result.get("response", "").strip()
                
        except asyncio.TimeoutError:
            raise RuntimeError(f"Ollama request timed out after {self.timeout}s")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Ollama connection failed: {e}")
