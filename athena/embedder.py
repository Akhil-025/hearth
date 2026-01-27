"""
Embedder - Local embedding generation via Ollama.
"""
from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from ..core.kernel import IService, ServiceInfo, ServiceStatus
from ..hestia.ollama_client import OllamaClient
from ..shared.logging.structured_logger import StructuredLogger
from .document_ingestor import DocumentChunk


class EmbeddingModel(BaseModel):
    """Embedding model configuration."""
    name: str
    dimensions: int
    max_batch_size: int = 32
    context_length: int = 512
    normalized: bool = True


class EmbeddingCacheEntry(BaseModel):
    """Embedding cache entry."""
    text_hash: str
    embedding: List[float]
    model_name: str
    created_at: float  # Unix timestamp
    accessed_count: int = 0


class Embedder(IService):
    """
    Local embedding generator using Ollama.
    
    Features:
    - Batch embedding generation
    - Embedding cache
    - Multiple model support
    - Fallback strategies
    """
    
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        default_model: str = "llama2:7b",
        cache_size: int = 10000
    ):
        self.logger = StructuredLogger(__name__)
        self.ollama_client = ollama_client or OllamaClient()
        self.default_model = default_model
        
        # Embedding cache (LRU-like)
        self.cache: Dict[str, EmbeddingCacheEntry] = {}
        self.cache_size = cache_size
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Available models (detected at runtime)
        self.available_models: Dict[str, EmbeddingModel] = {}
        
        # Service info
        self.service_info = ServiceInfo(
            name="athena_embedder",
            version="0.1.0",
            dependencies=["hestia_ollama"]
        )
        
        self.logger.info("Embedder initialized")
    
    async def start(self) -> None:
        """Start embedder service."""
        self.service_info.status = ServiceStatus.STARTING
        
        # Start Ollama client if not already started
        if not hasattr(self.ollama_client, 'session') or not self.ollama_client.session:
            await self.ollama_client.initialize()
        
        # Detect available models
        await self._detect_available_models()
        
        self.service_info.status = ServiceStatus.RUNNING
        self.logger.info(
            "Embedder started",
            default_model=self.default_model,
            available_models=list(self.available_models.keys())
        )
    
    async def stop(self) -> None:
        """Stop embedder service."""
        self.service_info.status = ServiceStatus.STOPPING
        
        # Clear cache
        self.cache.clear()
        
        self.service_info.status = ServiceStatus.STOPPED
        self.logger.info("Embedder stopped")
    
    def get_service_info(self) -> ServiceInfo:
        """Get service metadata."""
        return self.service_info
    
    async def health_check(self) -> bool:
        """Health check for embedding generation."""
        try:
            # Test embedding generation with small text
            test_text = "Test embedding generation"
            embedding = await self.embed_text(test_text)
            return len(embedding) > 0
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return False
    
    async def _detect_available_models(self) -> None:
        """Detect available embedding models."""
        try:
            # Get available models from Ollama
            models = await self.ollama_client.list_models()
            
            # Common embedding dimensions for known models
            model_dimensions = {
                "llama2:7b": 4096,
                "llama2:13b": 5120,
                "mistral:7b": 4096,
                "codellama:7b": 4096,
                "nomic-embed-text": 768,
                "all-minilm": 384
            }
            
            for model_name in models:
                dimensions = model_dimensions.get(model_name, 4096)  # Default
                
                self.available_models[model_name] = EmbeddingModel(
                    name=model_name,
                    dimensions=dimensions
                )
            
            self.logger.debug(
                "Available models detected",
                models=list(self.available_models.keys())
            )
            
        except Exception as e:
            self.logger.warning(
                "Failed to detect models, using defaults",
                error=str(e)
            )
            # Fallback to default model
            self.available_models[self.default_model] = EmbeddingModel(
                name=self.default_model,
                dimensions=4096
            )
    
    def _get_text_hash(self, text: str, model_name: str) -> str:
        """Generate hash for text and model combination."""
        import hashlib
        text_normalized = text.strip().lower()
        hash_input = f"{model_name}:{text_normalized}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    async def embed_text(
        self,
        text: str,
        model_name: Optional[str] = None,
        use_cache: bool = True
    ) -> List[float]:
        """
        Generate embedding for single text.
        
        Args:
            text: Text to embed
            model_name: Model to use (defaults to configured model)
            use_cache: Whether to use embedding cache
        
        Returns:
            Embedding vector
        """
        model = model_name or self.default_model
        
        # Check cache
        if use_cache:
            text_hash = self._get_text_hash(text, model)
            if text_hash in self.cache:
                self.cache_hits += 1
                entry = self.cache[text_hash]
                entry.accessed_count += 1
                return entry.embedding.copy()
        
        self.cache_misses += 1
        
        try:
            # Generate embedding using Ollama
            embedding = await self.ollama_client.generate_embedding(text, model)
            
            # Cache the result
            if use_cache:
                self._add_to_cache(text, model, embedding)
            
            self.logger.debug(
                "Text embedded",
                text_preview=text[:100],
                model=model,
                dimensions=len(embedding)
            )
            
            return embedding
            
        except Exception as e:
            self.logger.error(
                "Failed to generate embedding",
                error=str(e),
                model=model
            )
            # Return zero vector as fallback
            model_dim = self.available_models.get(model, EmbeddingModel(name=model, dimensions=384))
            return [0.0] * model_dim.dimensions
    
    async def embed_batch(
        self,
        texts: List[str],
        model_name: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for batch of texts.
        
        Args:
            texts: List of texts to embed
            model_name: Model to use
            batch_size: Maximum batch size
        
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        model = model_name or self.default_model
        
        # Determine batch size
        if batch_size is None:
            model_config = self.available_models.get(model)
            batch_size = model_config.max_batch_size if model_config else 8
        
        # Split into batches
        batches = [
            texts[i:i + batch_size]
            for i in range(0, len(texts), batch_size)
        ]
        
        embeddings = []
        
        for batch in batches:
            batch_embeddings = await asyncio.gather(*[
                self.embed_text(text, model)
                for text in batch
            ])
            embeddings.extend(batch_embeddings)
        
        self.logger.debug(
            "Batch embedding complete",
            total_texts=len(texts),
            batches=len(batches),
            model=model
        )
        
        return embeddings
    
    async def embed_chunks(
        self,
        chunks: List[DocumentChunk],
        model_name: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> List[DocumentChunk]:
        """
        Embed document chunks.
        
        Args:
            chunks: Document chunks
            model_name: Model to use
            batch_size: Maximum batch size
        
        Returns:
            Chunks with embeddings added
        """
        if not chunks:
            return []
        
        # Extract texts
        texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings
        embeddings = await self.embed_batch(texts, model_name, batch_size)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        self.logger.info(
            "Chunks embedded",
            chunks=len(chunks),
            model=model_name or self.default_model
        )
        
        return chunks
    
    def _add_to_cache(self, text: str, model_name: str, embedding: List[float]) -> None:
        """Add embedding to cache."""
        text_hash = self._get_text_hash(text, model_name)
        
        entry = EmbeddingCacheEntry(
            text_hash=text_hash,
            embedding=embedding,
            model_name=model_name,
            created_at=asyncio.get_event_loop().time(),
            accessed_count=1
        )
        
        self.cache[text_hash] = entry
        
        # Enforce cache size limit (simple FIFO)
        if len(self.cache) > self.cache_size:
            # Remove oldest entries
            entries = sorted(
                self.cache.values(),
                key=lambda e: e.created_at
            )
            
            for old_entry in entries[:len(self.cache) - self.cache_size]:
                del self.cache[old_entry.text_hash]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        total_size = sum(len(entry.embedding) * 8 for entry in self.cache.values())  # 8 bytes per float64
        
        return {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / max(self.cache_hits + self.cache_misses, 1),
            "total_size_bytes": total_size,
            "avg_embedding_dim": (
                sum(len(entry.embedding) for entry in self.cache.values()) / 
                max(len(self.cache), 1)
            )
        }
    
    async def normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize embedding to unit length."""
        import math
        
        # Calculate magnitude
        magnitude = math.sqrt(sum(x * x for x in embedding))
        
        if magnitude == 0:
            return embedding
        
        # Normalize
        return [x / magnitude for x in embedding]
    
    async def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between embeddings."""
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have same dimensions")
        
        # Normalize embeddings
        norm1 = await self.normalize_embedding(embedding1)
        norm2 = await self.normalize_embedding(embedding2)
        
        # Calculate dot product
        similarity = sum(a * b for a, b in zip(norm1, norm2))
        
        return max(-1.0, min(1.0, similarity))  # Clamp to [-1, 1]