"""
Document Chunker - Semantic chunking with overlap.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import nltk
from pydantic import BaseModel, Field

from ..shared.logging.structured_logger import StructuredLogger
from .document_ingestor import DocumentChunk, IngestedDocument


class ChunkingStrategy(Enum):
    """Chunking strategies."""
    FIXED = "fixed"  # Fixed size chunks
    SEMANTIC = "semantic"  # Semantic boundaries
    PARAGRAPH = "paragraph"  # Paragraph boundaries
    SENTENCE = "sentence"  # Sentence boundaries


class ChunkingConfig(BaseModel):
    """Chunking configuration."""
    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    chunk_size: int = Field(ge=100, le=10000, default=1000)
    chunk_overlap: int = Field(ge=0, le=500, default=200)
    max_chunks: int = Field(ge=1, le=1000, default=100)
    
    # Semantic chunking options
    respect_paragraphs: bool = True
    respect_sentences: bool = True
    min_chunk_size: int = 50
    max_chunk_size: int = 2000
    
    # Language options
    language: str = "english"
    
    class Config:
        use_enum_values = True


@dataclass
class ChunkBoundary:
    """Chunk boundary information."""
    start: int
    end: int
    is_semantic: bool = True
    boundary_type: Optional[str] = None  # paragraph, sentence, heading, etc.


class DocumentChunker:
    """
    Advanced document chunker with semantic boundary detection.
    
    Features:
    - Multiple chunking strategies
    - Semantic boundary preservation
    - Overlap management
    - Language-specific tokenization
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self.logger = StructuredLogger(__name__)
        
        # Download NLTK data if needed
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            self.logger.info("Downloading NLTK data...")
            nltk.download('punkt')
            nltk.download('averaged_perceptron_tagger')
        
        # Compile regex patterns
        self.heading_pattern = re.compile(r'^(#+|\d+\.\s+|\b(CHAPTER|SECTION)\s+\d+)', re.IGNORECASE)
        self.list_pattern = re.compile(r'^(\s*[\-\*•]\s+|\s*\d+\.\s+)')
        
        self.logger.info(
            "Document chunker initialized",
            strategy=self.config.strategy,
            chunk_size=self.config.chunk_size
        )
    
    def _detect_semantic_boundaries(self, text: str) -> List[ChunkBoundary]:
        """
        Detect semantic boundaries in text.
        
        Returns list of (start, end) positions for semantic units.
        """
        boundaries = []
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        current_pos = 0
        
        for para in paragraphs:
            if not para.strip():
                current_pos += 2  # Account for \n\n
                continue
            
            para_start = current_pos
            para_end = current_pos + len(para)
            
            # Check if this looks like a heading
            lines = para.split('\n')
            first_line = lines[0].strip() if lines else ""
            
            is_heading = (
                len(lines) == 1 and
                len(first_line) < 100 and
                (
                    self.heading_pattern.match(first_line) or
                    first_line.isupper() or
                    first_line.endswith(':')
                )
            )
            
            if is_heading and self.config.respect_paragraphs:
                # Treat heading as separate chunk
                boundaries.append(ChunkBoundary(
                    start=para_start,
                    end=para_end,
                    is_semantic=True,
                    boundary_type="heading"
                ))
            else:
                # Further split paragraph by sentences if needed
                if self.config.respect_sentences and len(para) > self.config.max_chunk_size:
                    sentences = self._split_sentences(para)
                    sent_start = para_start
                    
                    for sentence in sentences:
                        if not sentence.strip():
                            continue
                        
                        sent_end = sent_start + len(sentence)
                        boundaries.append(ChunkBoundary(
                            start=sent_start,
                            end=sent_end,
                            is_semantic=True,
                            boundary_type="sentence"
                        ))
                        sent_start = sent_end
                else:
                    boundaries.append(ChunkBoundary(
                        start=para_start,
                        end=para_end,
                        is_semantic=True,
                        boundary_type="paragraph"
                    ))
            
            current_pos = para_end + 2  # Account for \n\n
        
        return boundaries
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK."""
        try:
            sentences = nltk.sent_tokenize(text, language=self.config.language)
            return sentences
        except Exception:
            # Fallback to simple period-based splitting
            sentences = []
            current = []
            chars = list(text)
            
            for i, char in enumerate(chars):
                current.append(char)
                if char in '.!?':
                    # Check if it's really end of sentence
                    if i + 1 < len(chars) and chars[i + 1] in ' \t\n':
                        sentences.append(''.join(current))
                        current = []
            
            if current:
                sentences.append(''.join(current))
            
            return sentences
    
    def _merge_boundaries_into_chunks(
        self,
        boundaries: List[ChunkBoundary],
        text: str
    ) -> List[Tuple[int, int, bool]]:
        """
        Merge semantic boundaries into chunks based on configuration.
        
        Returns list of (start, end, is_semantic) tuples.
        """
        chunks = []
        current_start = 0
        current_length = 0
        current_boundaries = []
        
        for boundary in boundaries:
            boundary_length = boundary.end - boundary.start
            
            # If adding this boundary would exceed max chunk size
            if (current_length + boundary_length > self.config.chunk_size and 
                current_length >= self.config.min_chunk_size):
                
                # Finalize current chunk
                if current_boundaries:
                    chunk_end = current_boundaries[-1].end
                    is_semantic = all(b.is_semantic for b in current_boundaries)
                    chunks.append((current_start, chunk_end, is_semantic))
                
                # Start new chunk with overlap
                if self.config.chunk_overlap > 0 and chunks:
                    last_chunk_start, last_chunk_end, _ = chunks[-1]
                    overlap_start = max(last_chunk_end - self.config.chunk_overlap, last_chunk_start)
                    
                    # Find boundary that contains overlap start
                    for i, b in enumerate(boundaries):
                        if b.start <= overlap_start <= b.end:
                            current_start = b.start
                            current_boundaries = boundaries[i:]
                            current_length = sum(b.end - b.start for b in current_boundaries[:1])
                            break
                    else:
                        current_start = boundary.start
                        current_boundaries = [boundary]
                        current_length = boundary_length
                else:
                    current_start = boundary.start
                    current_boundaries = [boundary]
                    current_length = boundary_length
            else:
                # Add boundary to current chunk
                current_boundaries.append(boundary)
                current_length += boundary_length
        
        # Add final chunk
        if current_boundaries:
            chunk_end = current_boundaries[-1].end
            is_semantic = all(b.is_semantic for b in current_boundaries)
            chunks.append((current_start, chunk_end, is_semantic))
        
        return chunks
    
    def _fixed_size_chunking(self, text: str) -> List[Tuple[int, int, bool]]:
        """Simple fixed-size chunking."""
        chunks = []
        text_length = len(text)
        
        for i in range(0, text_length, self.config.chunk_size - self.config.chunk_overlap):
            chunk_start = i
            chunk_end = min(i + self.config.chunk_size, text_length)
            
            # Adjust end to not break words if possible
            if chunk_end < text_length:
                # Try to end at sentence boundary
                for j in range(chunk_end, max(chunk_start, chunk_end - 100), -1):
                    if text[j] in '.!?\n':
                        chunk_end = j + 1
                        break
                # Try to end at word boundary
                elif chunk_end < text_length and text[chunk_end] not in ' \t\n':
                    for j in range(chunk_end, min(text_length, chunk_end + 100)):
                        if text[j] in ' \t\n':
                            chunk_end = j
                            break
            
            chunks.append((chunk_start, chunk_end, False))
            
            if chunk_end >= text_length:
                break
        
        return chunks
    
    def chunk_document(self, document: IngestedDocument) -> List[DocumentChunk]:
        """
        Chunk document based on configured strategy.
        
        Args:
            document: Ingested document
        
        Returns:
            List of document chunks
        """
        text = document.content
        
        if not text.strip():
            return []
        
        # Select chunking strategy
        if self.config.strategy == ChunkingStrategy.FIXED:
            chunk_ranges = self._fixed_size_chunking(text)
        else:
            # Semantic-based chunking
            boundaries = self._detect_semantic_boundaries(text)
            chunk_ranges = self._merge_boundaries_into_chunks(boundaries, text)
        
        # Create chunks
        chunks = []
        for chunk_index, (start, end, is_semantic) in enumerate(chunk_ranges):
            if chunk_index >= self.config.max_chunks:
                break
            
            chunk_text = text[start:end].strip()
            if not chunk_text:
                continue
            
            # Calculate checksum for chunk
            import hashlib
            checksum = hashlib.sha256(chunk_text.encode()).hexdigest()
            
            # Determine page number if available
            page_number = None
            if document.metadata.parser_metadata and 'pages' in document.metadata.parser_metadata:
                # Simple approximation: assume uniform distribution
                # This could be enhanced with actual page mapping from parser
                pass
            
            chunk = DocumentChunk(
                document_id=document.document_id,
                content=chunk_text,
                chunk_index=chunk_index,
                start_position=start,
                end_position=end,
                page_number=page_number,
                metadata={
                    "is_semantic": is_semantic,
                    "strategy": self.config.strategy,
                    "original_title": document.title
                },
                checksum=checksum
            )
            
            chunks.append(chunk)
        
        self.logger.debug(
            "Document chunked",
            document_id=document.document_id,
            chunks=len(chunks),
            strategy=self.config.strategy
        )
        
        return chunks
    
    def chunk_text(self, text: str, document_id: str = "generated") -> List[DocumentChunk]:
        """
        Chunk raw text.
        
        Args:
            text: Raw text to chunk
            document_id: Document identifier
        
        Returns:
            List of document chunks
        """
        # Create a minimal document structure
        document = IngestedDocument(
            document_id=document_id,
            title="Generated Text",
            content=text,
            metadata=DocumentMetadata(
                document_id=document_id,
                title="Generated Text",
                document_type=DocumentType.TEXT,
                file_name="generated.txt",
                file_size=len(text),
                file_extension=".txt",
                checksum=hashlib.sha256(text.encode()).hexdigest(),
                source_path="generated"
            ),
            checksum=hashlib.sha256(text.encode()).hexdigest(),
            processing_time_ms=0.0
        )
        
        return self.chunk_document(document)