"""
Document Ingestor - Handle various document formats with OCR.
"""
from __future__ import annotations

import asyncio
import hashlib
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple
from uuid import uuid4

import pdfplumber
import pytesseract
from PIL import Image
from pydantic import BaseModel, Field
from pypdf import PdfReader
from python_docx import Document as DocxDocument

from ..core.kernel import IService, ServiceInfo, ServiceStatus
from ..shared.logging.structured_logger import StructuredLogger
from ..shared.schemas.knowledge import DocumentMetadata, DocumentType


class DocumentChunk(BaseModel):
    """Document chunk with metadata."""
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    content: str
    chunk_index: int
    start_position: int
    end_position: int
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    checksum: str


class IngestedDocument(BaseModel):
    """Ingested document result."""
    document_id: str
    title: str
    content: str
    chunks: List[DocumentChunk] = Field(default_factory=list)
    metadata: DocumentMetadata
    checksum: str
    processing_time_ms: float


class IDocumentParser(ABC):
    """Document parser interface."""
    
    @abstractmethod
    async def parse(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Parse document and return content and metadata."""
        pass
    
    @abstractmethod
    def supports(self, file_extension: str) -> bool:
        """Check if parser supports file extension."""
        pass


class PDFParser(IDocumentParser):
    """PDF document parser with OCR fallback."""
    
    def __init__(self, enable_ocr: bool = True, ocr_lang: str = "eng"):
        self.enable_ocr = enable_ocr
        self.ocr_lang = ocr_lang
        self.logger = StructuredLogger(__name__)
    
    def supports(self, file_extension: str) -> bool:
        return file_extension.lower() in ['.pdf']
    
    async def parse(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Parse PDF file."""
        content_parts = []
        metadata = {
            "pages": 0,
            "has_text": False,
            "ocr_used": False
        }
        
        try:
            # Try to extract text normally
            with pdfplumber.open(file_path) as pdf:
                metadata["pages"] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    
                    if text and len(text.strip()) > 50:
                        content_parts.append(text)
                        metadata["has_text"] = True
                    elif self.enable_ocr:
                        # Use OCR for scanned PDFs
                        image = page.to_image(resolution=300)
                        ocr_text = pytesseract.image_to_string(
                            image.original,
                            lang=self.ocr_lang
                        )
                        if ocr_text:
                            content_parts.append(ocr_text)
                            metadata["ocr_used"] = True
            
            # Fallback to pypdf if pdfplumber fails
            if not content_parts:
                reader = PdfReader(file_path)
                metadata["pages"] = len(reader.pages)
                
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        content_parts.append(text)
                        metadata["has_text"] = True
            
            content = "\n\n".join(content_parts)
            
            # Extract metadata from PDF
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                doc_info = reader.metadata
                if doc_info:
                    metadata.update({
                        "author": doc_info.author,
                        "creator": doc_info.creator,
                        "producer": doc_info.producer,
                        "subject": doc_info.subject,
                        "title": doc_info.title,
                        "creation_date": str(doc_info.get('/CreationDate', '')),
                        "modification_date": str(doc_info.get('/ModDate', ''))
                    })
            
            return content, metadata
            
        except Exception as e:
            self.logger.error(
                "Failed to parse PDF",
                file_path=str(file_path),
                error=str(e)
            )
            raise


class DOCXParser(IDocumentParser):
    """DOCX document parser."""
    
    def supports(self, file_extension: str) -> bool:
        return file_extension.lower() in ['.docx', '.doc']
    
    async def parse(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Parse DOCX file."""
        try:
            doc = DocxDocument(file_path)
            content_parts = []
            
            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content_parts.append(paragraph.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            content_parts.append(cell.text)
            
            content = "\n\n".join(content_parts)
            
            # Extract metadata
            metadata = {
                "paragraphs": len(doc.paragraphs),
                "tables": len(doc.tables),
                "core_properties": {}
            }
            
            # Extract core properties
            cp = doc.core_properties
            if cp:
                metadata["core_properties"] = {
                    "author": cp.author,
                    "category": cp.category,
                    "comments": cp.comments,
                    "content_status": cp.content_status,
                    "created": cp.created,
                    "identifier": cp.identifier,
                    "keywords": cp.keywords,
                    "language": cp.language,
                    "last_modified_by": cp.last_modified_by,
                    "last_printed": cp.last_printed,
                    "modified": cp.modified,
                    "revision": cp.revision,
                    "subject": cp.subject,
                    "title": cp.title,
                    "version": cp.version
                }
            
            return content, metadata
            
        except Exception as e:
            self.logger.error(
                "Failed to parse DOCX",
                file_path=str(file_path),
                error=str(e)
            )
            raise


class ImageParser(IDocumentParser):
    """Image parser with OCR."""
    
    def __init__(self, ocr_lang: str = "eng"):
        self.ocr_lang = ocr_lang
        self.supported_extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']
    
    def supports(self, file_extension: str) -> bool:
        return file_extension.lower() in self.supported_extensions
    
    async def parse(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Parse image file with OCR."""
        try:
            # Open and process image
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode not in ['RGB', 'L']:
                    img = img.convert('RGB')
                
                # Get image metadata
                metadata = {
                    "format": img.format,
                    "size": img.size,
                    "mode": img.mode,
                    "resolution": img.info.get('dpi', (72, 72))
                }
                
                # Perform OCR
                content = pytesseract.image_to_string(img, lang=self.ocr_lang)
                
                return content.strip(), metadata
                
        except Exception as e:
            self.logger.error(
                "Failed to parse image",
                file_path=str(file_path),
                error=str(e)
            )
            raise


class TextParser(IDocumentParser):
    """Plain text parser."""
    
    def supports(self, file_extension: str) -> bool:
        return file_extension.lower() in ['.txt', '.md', '.csv', '.json', '.xml', '.html']
    
    async def parse(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Parse text file."""
        try:
            # Detect encoding
            encodings = ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    
                    metadata = {
                        "encoding": encoding,
                        "size": file_path.stat().st_size,
                        "lines": len(content.splitlines())
                    }
                    
                    return content, metadata
                    
                except UnicodeDecodeError:
                    continue
            
            # Fallback to binary read
            with open(file_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='ignore')
            
            metadata = {
                "encoding": "binary_fallback",
                "size": file_path.stat().st_size,
                "lines": len(content.splitlines())
            }
            
            return content, metadata
            
        except Exception as e:
            self.logger.error(
                "Failed to parse text file",
                file_path=str(file_path),
                error=str(e)
            )
            raise


class DocumentIngestor(IService):
    """
    Document ingestion service supporting multiple formats.
    
    Features:
    - Multi-format support (PDF, DOCX, images, text)
    - OCR for scanned documents
    - Encoding detection
    - Checksum verification
    """
    
    def __init__(self):
        self.logger = StructuredLogger(__name__)
        
        # Register parsers
        self.parsers: List[IDocumentParser] = [
            PDFParser(),
            DOCXParser(),
            ImageParser(),
            TextParser()
        ]
        
        # Service info
        self.service_info = ServiceInfo(
            name="athena_document_ingestor",
            version="0.1.0",
            dependencies=[]
        )
        
        # Cache for processed files
        self.processed_cache: Dict[str, IngestedDocument] = {}
        
        self.logger.info("Document ingestor initialized")
    
    async def start(self) -> None:
        """Start ingestor service."""
        self.service_info.status = ServiceStatus.RUNNING
        self.logger.info("Document ingestor started")
    
    async def stop(self) -> None:
        """Stop ingestor service."""
        self.service_info.status = ServiceStatus.STOPPED
        self.processed_cache.clear()
        self.logger.info("Document ingestor stopped")
    
    def get_service_info(self) -> ServiceInfo:
        """Get service metadata."""
        return self.service_info
    
    async def health_check(self) -> bool:
        """Health check for OCR capabilities."""
        try:
            # Test OCR availability
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            self.logger.warning("OCR not available, will skip image processing")
            return True  # OCR is optional
    
    def _get_parser(self, file_extension: str) -> Optional[IDocumentParser]:
        """Get appropriate parser for file extension."""
        for parser in self.parsers:
            if parser.supports(file_extension):
                return parser
        return None
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file."""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _extract_title(self, content: str, metadata: Dict[str, Any]) -> str:
        """Extract or generate document title."""
        # Try to get title from metadata
        if metadata.get("core_properties", {}).get("title"):
            return metadata["core_properties"]["title"]
        
        if metadata.get("title"):
            return metadata["title"]
        
        # Generate title from first line or content
        first_line = content.split('\n')[0].strip()
        if first_line and len(first_line) < 100:
            return first_line
        
        # Fallback to generic title
        return "Untitled Document"
    
    async def ingest_document(
        self,
        file_path: Path,
        document_type: Optional[DocumentType] = None,
        metadata_overrides: Optional[Dict[str, Any]] = None
    ) -> IngestedDocument:
        """
        Ingest a document from file path.
        
        Args:
            file_path: Path to document file
            document_type: Override detected document type
            metadata_overrides: Additional metadata
        
        Returns:
            Ingested document with content and metadata
        """
        start_time = asyncio.get_event_loop().time()
        
        # Validate file
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Calculate checksum for deduplication
        checksum = self._calculate_checksum(file_path)
        
        # Check cache
        if checksum in self.processed_cache:
            self.logger.debug("Using cached document", checksum=checksum[:16])
            return self.processed_cache[checksum].copy()
        
        # Get file extension and parser
        file_extension = file_path.suffix.lower()
        parser = self._get_parser(file_extension)
        
        if not parser:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        # Parse document
        content, parser_metadata = await parser.parse(file_path)
        
        # Create document ID
        document_id = hashlib.sha256(f"{checksum}:{file_path.name}".encode()).hexdigest()[:32]
        
        # Determine document type
        if not document_type:
            if file_extension == '.pdf':
                document_type = DocumentType.PDF
            elif file_extension in ['.docx', '.doc']:
                document_type = DocumentType.DOCUMENT
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff']:
                document_type = DocumentType.IMAGE
            else:
                document_type = DocumentType.TEXT
        
        # Extract title
        title = self._extract_title(content, parser_metadata)
        
        # Build metadata
        metadata = DocumentMetadata(
            document_id=document_id,
            title=title,
            document_type=document_type,
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            file_extension=file_extension,
            checksum=checksum,
            source_path=str(file_path),
            parser_metadata=parser_metadata
        )
        
        # Apply overrides
        if metadata_overrides:
            for key, value in metadata_overrides.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
        
        # Create result (chunks will be added by chunker)
        result = IngestedDocument(
            document_id=document_id,
            title=title,
            content=content,
            metadata=metadata,
            checksum=checksum,
            processing_time_ms=0.0
        )
        
        # Calculate processing time
        end_time = asyncio.get_event_loop().time()
        result.processing_time_ms = (end_time - start_time) * 1000
        
        # Cache result
        self.processed_cache[checksum] = result
        
        self.logger.info(
            "Document ingested",
            document_id=document_id,
            title=title,
            file_type=file_extension,
            content_length=len(content),
            processing_time_ms=result.processing_time_ms
        )
        
        return result
    
    async def ingest_from_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        document_type: Optional[DocumentType] = None
    ) -> IngestedDocument:
        """
        Ingest document from bytes.
        
        Useful for API uploads.
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            suffix=Path(file_name).suffix,
            delete=False
        ) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = await self.ingest_document(tmp_path, document_type)
            return result
        finally:
            # Cleanup temporary file
            tmp_path.unlink(missing_ok=True)
    
    async def batch_ingest(
        self,
        directory_path: Path,
        file_pattern: str = "**/*",
        max_workers: int = 4
    ) -> List[IngestedDocument]:
        """
        Batch ingest documents from directory.
        
        Args:
            directory_path: Directory to scan
            file_pattern: Glob pattern for files
            max_workers: Maximum concurrent ingestions
        
        Returns:
            List of ingested documents
        """
        if not directory_path.is_dir():
            raise ValueError(f"Not a directory: {directory_path}")
        
        # Find files
        files = list(directory_path.glob(file_pattern))
        files = [f for f in files if f.is_file()]
        
        self.logger.info(
            "Batch ingestion started",
            directory=str(directory_path),
            file_count=len(files)
        )
        
        # Process files with semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_workers)
        results = []
        
        async def process_file(file_path: Path) -> Optional[IngestedDocument]:
            async with semaphore:
                try:
                    return await self.ingest_document(file_path)
                except Exception as e:
                    self.logger.error(
                        "Failed to ingest file",
                        file_path=str(file_path),
                        error=str(e)
                    )
                    return None
        
        # Process all files
        tasks = [process_file(f) for f in files]
        results = await asyncio.gather(*tasks)
        
        # Filter out failures
        successful = [r for r in results if r is not None]
        
        self.logger.info(
            "Batch ingestion completed",
            total_files=len(files),
            successful=len(successful),
            failed=len(files) - len(successful)
        )
        
        return successful
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        extensions = set()
        for parser in self.parsers:
            # This would require adding a method to get extensions from parser
            # For now, we'll return a hardcoded list
            pass
        
        return [
            '.pdf', '.docx', '.doc',
            '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif',
            '.txt', '.md', '.csv', '.json', '.xml', '.html'
        ]