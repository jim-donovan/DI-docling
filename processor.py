"""
Main OCR Processor
Orchestrates the complete OCR processing pipeline
"""

import time
import tempfile
import os
import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from config import config
from logger import ProcessingLogger
from ocr_engine import OCREngine
from text_processor import ContentFormatter, TextRepair
from utils import parse_page_ranges, validate_page_ranges

@dataclass
class ProcessingResult:
    """Container for processing results."""
    content: str
    output_file: Optional[str]
    status: str
    logs: str
    success: bool
    vision_calls_used: int = 0
    processing_time: float = 0.0
    pages_processed: int = 0

class DocumentProcessor:
    """Main document processor orchestrating the OCR pipeline."""
    
    def __init__(self):
        self.logger = ProcessingLogger()
        self.ocr_engine = OCREngine(self.logger)
        # Removed ContextExtractor as per streamlined version
        self.content_formatter = ContentFormatter(self.logger)
    
    def save_output(self, pdf_path: Path, content: str) -> Optional[str]:
        """Save processed content to file."""
        try:
            base_name = pdf_path.stem
            filename = f"{base_name}_processed.md"
            
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, filename)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            self.logger.log_success(f"Saved: {filename}")
            return output_path
            
        except Exception as e:
            self.logger.log_error(f"Save failed: {e}")
            return None
    
    def process_document(self, uploaded_file, page_ranges_str: Optional[str] = None, progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """
        Process a PDF document through the complete OCR pipeline.
        
        Args:
            uploaded_file: Uploaded PDF file
            page_ranges_str: Optional page ranges string (e.g., "1-5, 10, 15-20")
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessingResult containing all processing information
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not uploaded_file:
                return ProcessingResult(
                    content="Please upload a PDF file.",
                    output_file=None,
                    status="No file",
                    logs="",
                    success=False
                )
            
            pdf_path = Path(uploaded_file.name)
            self.logger.log_section(f"Processing: {pdf_path.name}")
            
            if progress_callback:
                progress_callback(f"📄 Processing: {pdf_path.name}")
            
            with fitz.open(pdf_path) as doc:
                total_pages = len(doc)
                self.logger.log_metric("Total pages in document", total_pages)
                
                if page_ranges_str and page_ranges_str.strip():
                    is_valid, error_msg, pages_to_process = validate_page_ranges(page_ranges_str, total_pages)
                    if not is_valid:
                        return ProcessingResult(
                            content=f"Invalid page ranges: {error_msg}",
                            output_file=None,
                            status="Invalid page ranges",
                            logs=self.logger.get_logs(),
                            success=False
                        )
                    
                    page_numbers = [p + 1 for p in pages_to_process]
                    self.logger.log_metric("Pages to process", f"{len(page_numbers)} pages: {page_ranges_str}")
                else:
                    page_numbers = list(range(1, total_pages + 1))
                    self.logger.log_metric("Pages to process", f"All {total_pages} pages")
                
                page_texts = {}
                for i, page_no in enumerate(page_numbers):
                    if progress_callback:
                        progress_callback(f"📖 Processing page {page_no} ({i+1}/{len(page_numbers)})")
                    
                    page = doc[page_no - 1]  # Convert to 0-indexed for fitz
                    text = self.ocr_engine.extract_page_text(page, page_no)
                    page_texts[page_no] = text
            
            self.logger.log_section("Content Formatting")
            if progress_callback:
                progress_callback("📝 Formatting content...")
            
            formatted_pages = []
            document_title = self._extract_document_title(pdf_path.name)
            
            for page_no in sorted(page_texts.keys()):
                if len(page_texts[page_no].strip()) >= 10:
                    formatted = self.content_formatter.format_content(
                        page_texts[page_no], 
                        page_no, 
                        document_title
                    )
                    formatted_pages.append(formatted)
            
            # Build final document
            self.logger.log_section("Document Assembly")
            header = self.content_formatter.build_document_header(document_title)
            
            if page_ranges_str and page_ranges_str.strip():
                header += f"\n\n**Pages Processed:** {page_ranges_str}"
            
            final_content = f"{header}\n\n---\n\n" + "\n\n---\n\n".join(formatted_pages)
            
            output_file = self.save_output(pdf_path, final_content)
            
            processing_time = time.time() - start_time
            vision_calls = self.ocr_engine.get_vision_calls_used()
            
            self.logger.log_section("Processing Complete")
            self.logger.log_metric("Processing time", f"{processing_time:.1f}s")
            self.logger.log_metric("Vision calls used", vision_calls)
            self.logger.log_metric("Pages processed", len(formatted_pages))
            self.logger.log_metric("Total words", len(final_content.split()))
            
            if progress_callback:
                progress_callback("✅ Complete!")
            
            return ProcessingResult(
                content=final_content,
                output_file=output_file,
                status="Complete",
                logs=self.logger.get_logs(),
                success=True,
                vision_calls_used=vision_calls,
                processing_time=processing_time,
                pages_processed=len(formatted_pages)
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Processing error: {str(e)}"
            self.logger.log_error(error_msg)
            
            return ProcessingResult(
                content=f"Processing error: {str(e)}",
                output_file=None,
                status="Error",
                logs=self.logger.get_logs(),
                success=False,
                vision_calls_used=self.ocr_engine.get_vision_calls_used(),
                processing_time=processing_time,
                pages_processed=0
            )
    
    def _extract_document_title(self, filename: str) -> str:
        """Extract a clean document title from filename."""
        # Remove file extension and clean up
        title = os.path.splitext(os.path.basename(filename))[0]
        # Replace underscores and hyphens with spaces
        title = title.replace('_', ' ').replace('-', ' ')
        # Capitalize words
        title = ' '.join(word.capitalize() for word in title.split())
        return title if title else "Document"
    
    def add_log_callback(self, callback: Callable[[str], None]) -> None:
        """Add a callback for real-time log updates."""
        self.logger.add_callback(callback)
    
    def clear_logs(self) -> None:
        """Clear all logs and reset counters."""
        self.logger.clear()
        self.ocr_engine.reset_vision_counter()