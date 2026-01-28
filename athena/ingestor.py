"""
Manual document ingestion for Athena.

Explicit user command only. No background watchers.
"""

from pathlib import Path
from typing import Optional

from .adapters import extract_text_from_pdf, scan_pdf_directory
from .config import AthenaConfig
from .retriever import AthenaRetriever
from .utils import chunk_text, clean_text


class AthenaIngestor:
    """
    Manual document ingestion into Athena index.
    
    Designed for explicit user commands only.
    No background watchers, no automatic ingestion.
    """

    def __init__(self, config: AthenaConfig, retriever: AthenaRetriever):
        """
        Initialize ingestor.
        
        Args:
            config: AthenaConfig
            retriever: AthenaRetriever instance
        """
        self.config = config
        self.retriever = retriever

    def ingest_pdf(
        self,
        pdf_path: Path,
        subject: Optional[str] = None,
        module: Optional[str] = None,
    ) -> dict:
        """
        Ingest a single PDF file.
        
        Args:
            pdf_path: Path to PDF
            subject: Optional subject category
            module: Optional module category
        
        Returns:
            Dict with ingestion stats
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            return {"success": False, "error": f"File not found: {pdf_path}"}

        try:
            # Extract text
            text, metadata = extract_text_from_pdf(pdf_path)
            text = clean_text(text)

            if not text:
                return {"success": False, "error": "No text extracted from PDF"}

            # Chunk text
            chunks = chunk_text(
                text,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
            )

            # Extract page numbers from metadata
            page_breaks = metadata.get("page_breaks", {})

            # Prepare documents with page numbers
            documents = []
            for chunk in chunks:
                # Find which page this chunk is on
                page_num = 1
                for pos, pnum in sorted(page_breaks.items()):
                    if text.find(chunk) >= pos:
                        page_num = pnum

                documents.append({"text": chunk, "page_number": page_num})

            # Add to index
            self.retriever.add_documents(
                documents,
                file_name=pdf_path.name,
                subject=subject or "uncategorized",
                module=module or "general",
            )

            return {
                "success": True,
                "file_name": pdf_path.name,
                "chunks_created": len(documents),
                "text_length": len(text),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def ingest_directory(
        self,
        directory: Optional[Path] = None,
        subject: Optional[str] = None,
        module: Optional[str] = None,
    ) -> dict:
        """
        Ingest all PDFs in a directory.
        
        Args:
            directory: Directory to scan (uses config.data_dir if None)
            subject: Optional subject for all files
            module: Optional module for all files
        
        Returns:
            Dict with aggregated ingestion stats
        """
        directory = Path(directory or self.config.data_dir)

        if not directory.is_dir():
            return {
                "success": False,
                "error": f"Directory not found: {directory}",
            }

        pdf_files = scan_pdf_directory(directory)

        if not pdf_files:
            return {
                "success": True,
                "files_processed": 0,
                "total_chunks": 0,
                "message": "No PDFs found in directory",
            }

        total_chunks = 0
        successful = 0
        failed = []

        for pdf_file in pdf_files:
            result = self.ingest_pdf(pdf_file, subject=subject, module=module)

            if result["success"]:
                successful += 1
                total_chunks += result.get("chunks_created", 0)
            else:
                failed.append({"file": pdf_file.name, "error": result.get("error")})

        return {
            "success": True,
            "files_found": len(pdf_files),
            "files_processed": successful,
            "total_chunks": total_chunks,
            "failed": failed if failed else None,
        }

    def get_ingestion_stats(self) -> dict:
        """
        Get statistics about ingested documents.
        
        Returns:
            Dict with index stats
        """
        return self.retriever.get_index_stats()
