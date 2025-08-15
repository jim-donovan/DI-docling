"""
Docling Document Processor
Streamlined document processing using native docling with SmolDocling fallback
"""

import time
import tempfile
import os
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
import hashlib
import json

import fitz  # PyMuPDF
from config import config
from logger import ProcessingLogger

# Import docling components
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TableStructureOptions,
        OCROptions
    )
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    print("Warning: docling not available. Install with: pip install docling")

# Import SmolDocling as fallback
try:
    from ocr_engine_smoldocling import SmolDoclingOCREngine
    SMOLDOCLING_AVAILABLE = True
except ImportError:
    SMOLDOCLING_AVAILABLE = False
    print("Warning: SmolDocling not available for fallback")

# Import text formatter if OpenAI is configured
try:
    from text_processor import ContentFormatter
    FORMATTER_AVAILABLE = True
except ImportError:
    FORMATTER_AVAILABLE = False


@dataclass
class ProcessingResult:
    """Enhanced processing result with metadata."""
    content: str
    output_file: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    success: bool = False
    processing_time: float = 0.0
    pages_processed: int = 0
    processor_used: str = "unknown"
    structured_output: Optional[str] = None


class DoclingProcessor:
    """Document processor that prioritizes native docling capabilities."""
    
    def __init__(self):
        """Initialize the processor with optimal settings."""
        self.logger = ProcessingLogger()
        self.logger.log_section("Initializing Optimized Docling Processor")
        
        # Validate configuration
        config.validate()
        
        # Initialize docling if available
        self.docling_converter = None
        if DOCLING_AVAILABLE and config.use_native_docling:
            self._init_docling()
        
        # Initialize SmolDocling fallback if available
        self.smoldocling_engine = None
        if SMOLDOCLING_AVAILABLE:
            try:
                self.smoldocling_engine = SmolDoclingOCREngine(self.logger)
                self.logger.log_success("SmolDocling fallback initialized")
            except Exception as e:
                self.logger.log_warning(f"SmolDocling initialization failed: {e}")
        
        # Initialize formatter if available and configured
        self.formatter = None
        if FORMATTER_AVAILABLE and config.formatting_enabled and config.openai_api_key:
            try:
                self.formatter = ContentFormatter(self.logger)
                self.logger.log_success("Content formatter initialized")
            except Exception as e:
                self.logger.log_warning(f"Formatter initialization failed: {e}")
        
        # Cache for processed pages
        self.cache = {} if config.cache_enabled else None
    
    def _init_docling(self):
        """Initialize docling with optimized settings."""
        try:
            # Configure pipeline options for better extraction
            pipeline_options = PdfPipelineOptions()
            
            # Configure table extraction
            pipeline_options.table_structure_options = TableStructureOptions(
                do_table_structure=True,  # Enable table structure recognition
                mode="fast"  # Use fast mode for better performance
            )
            
            # Configure OCR options
            pipeline_options.ocr_options = OCROptions(
                use_ocr=True,  # Enable OCR for scanned documents
                force_ocr=False  # Only use OCR when necessary
            )
            
            # Initialize converter with options
            self.docling_converter = DocumentConverter(
                pipeline_options=pipeline_options,
                pdf_backend="pypdfium2"  # Faster PDF backend
            )
            
            self.logger.log_success("Docling converter initialized with optimized settings")
            
        except Exception as e:
            self.logger.log_error(f"Failed to initialize docling: {e}")
            self.docling_converter = None
    
    def _get_cache_key(self, file_path: Path, page_no: Optional[int] = None) -> str:
        """Generate cache key for a file/page."""
        if not config.cache_enabled:
            return ""
        
        # Get file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]
        
        if page_no is not None:
            return f"{file_hash}_p{page_no}"
        return file_hash
    
    def _process_with_docling(self, file_path: Path) -> Optional[ProcessingResult]:
        """Process document using native docling."""
        if not self.docling_converter:
            return None
        
        try:
            self.logger.log_step("Docling", "Processing with native converter")
            start_time = time.time()
            
            # Check cache
            cache_key = self._get_cache_key(file_path)
            if self.cache and cache_key in self.cache:
                self.logger.log_success("Using cached docling result")
                return self.cache[cache_key]
            
            # Convert document
            result = self.docling_converter.convert(str(file_path))
            
            # Extract content in requested format
            content = ""
            structured = None
            metadata = {}
            
            if config.output_format == "markdown":
                content = result.document.export_to_markdown()
            elif config.output_format == "doctags":
                try:
                    content = result.document.export_to_doctags()
                    structured = content
                except AttributeError:
                    # Fallback to markdown if doctags not available
                    content = result.document.export_to_markdown()
                    self.logger.log_warning("DocTags export not available, using markdown")
            elif config.output_format == "json":
                content = json.dumps(result.document.export_to_dict(), indent=2)
                structured = content
            else:
                content = result.document.export_to_markdown()
            
            # Extract metadata if requested
            if config.include_metadata:
                metadata = {
                    "title": getattr(result.document, 'title', None),
                    "page_count": len(result.document.pages) if hasattr(result.document, 'pages') else 0,
                    "tables_found": len(result.document.tables) if hasattr(result.document, 'tables') else 0,
                    "processing_backend": "docling",
                    "format": config.output_format
                }
            
            # Apply formatting if enabled
            if self.formatter and config.formatting_enabled:
                try:
                    formatted_content = self.formatter.format_content(
                        content, 
                        page_no=1,  # Treat as single document
                        document_title=metadata.get('title', file_path.stem)
                    )
                    content = formatted_content
                    self.logger.log_success("Content formatting applied")
                except Exception as e:
                    self.logger.log_warning(f"Formatting failed, using raw content: {e}")
            
            processing_time = time.time() - start_time
            
            # Create result
            result_obj = ProcessingResult(
                content=content,
                metadata=metadata,
                status="Complete",
                success=True,
                processing_time=processing_time,
                pages_processed=metadata.get('page_count', 0),
                processor_used="docling",
                structured_output=structured
            )
            
            # Cache result
            if self.cache:
                self.cache[cache_key] = result_obj
            
            self.logger.log_success(f"Docling processing complete in {processing_time:.1f}s")
            return result_obj
            
        except Exception as e:
            self.logger.log_error(f"Docling processing failed: {e}")
            return None
    
    def _process_with_smoldocling(self, file_path: Path, page_ranges: Optional[List[int]] = None) -> Optional[ProcessingResult]:
        """Fallback to SmolDocling for processing."""
        if not self.smoldocling_engine:
            return None
        
        try:
            self.logger.log_step("SmolDocling", "Processing with fallback OCR")
            start_time = time.time()
            
            with fitz.open(file_path) as doc:
                total_pages = len(doc)
                pages_to_process = page_ranges if page_ranges else list(range(total_pages))
                
                # Process pages
                page_contents = []
                for page_idx in pages_to_process:
                    if page_idx >= total_pages:
                        continue
                    
                    page = doc[page_idx]
                    page_no = page_idx + 1
                    
                    # Check cache
                    cache_key = self._get_cache_key(file_path, page_no)
                    if self.cache and cache_key in self.cache:
                        page_contents.append(self.cache[cache_key])
                        continue
                    
                    # Extract text
                    text = self.smoldocling_engine.extract_page_text(
                        page, page_no, str(file_path)
                    )
                    
                    # Cache page result
                    if self.cache:
                        self.cache[cache_key] = text
                    
                    page_contents.append(text)
            
            # Combine pages
            content = "\n\n---\n\n".join(page_contents)
            
            # Apply formatting if enabled
            if self.formatter and config.formatting_enabled:
                try:
                    content = self.formatter.format_content(
                        content, 
                        page_no=1,
                        document_title=file_path.stem
                    )
                except Exception as e:
                    self.logger.log_warning(f"Formatting failed: {e}")
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                content=content,
                status="Complete",
                success=True,
                processing_time=processing_time,
                pages_processed=len(page_contents),
                processor_used="smoldocling",
                metadata={"fallback_reason": "docling_unavailable_or_failed"}
            )
            
        except Exception as e:
            self.logger.log_error(f"SmolDocling processing failed: {e}")
            return None
    
    def process_document(
        self,
        file_path: str,
        page_ranges: Optional[List[int]] = None,
        progress_callback: Optional[Callable] = None
    ) -> ProcessingResult:
        """
        Main entry point for document processing.
        
        Args:
            file_path: Path to the document file
            page_ranges: Optional list of page indices to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessingResult with extracted content and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return ProcessingResult(
                content="File not found",
                status="Error",
                success=False
            )
        
        self.logger.log_section(f"Processing: {file_path.name}")
        
        if progress_callback:
            progress_callback(f"Starting processing of {file_path.name}")
        
        # Try native docling first
        if config.use_native_docling and DOCLING_AVAILABLE:
            result = self._process_with_docling(file_path)
            if result and result.success:
                if progress_callback:
                    progress_callback("Processing complete with Docling")
                return self._save_outputs(result, file_path)
        
        # Fallback to SmolDocling
        if SMOLDOCLING_AVAILABLE:
            result = self._process_with_smoldocling(file_path, page_ranges)
            if result and result.success:
                if progress_callback:
                    progress_callback("Processing complete with SmolDocling")
                return self._save_outputs(result, file_path)
        
        # Final fallback - basic PyMuPDF extraction
        try:
            self.logger.log_step("PyMuPDF", "Using basic text extraction")
            with fitz.open(file_path) as doc:
                content = ""
                for page in doc:
                    content += page.get_text() + "\n\n"
            
            result = ProcessingResult(
                content=content,
                status="Complete (basic extraction)",
                success=True,
                processor_used="pymupdf",
                pages_processed=len(doc)
            )
            
            if progress_callback:
                progress_callback("Processing complete with basic extraction")
            
            return self._save_outputs(result, file_path)
            
        except Exception as e:
            self.logger.log_error(f"All processing methods failed: {e}")
            return ProcessingResult(
                content=f"Processing failed: {str(e)}",
                status="Error",
                success=False
            )
    
    def _save_outputs(self, result: ProcessingResult, file_path: Path) -> ProcessingResult:
        """Save processing outputs to files."""
        try:
            temp_dir = tempfile.gettempdir()
            base_name = file_path.stem
            
            # Save main output
            if config.output_format == "markdown":
                ext = ".md"
            elif config.output_format == "doctags":
                ext = ".doctags"
            elif config.output_format == "json":
                ext = ".json"
            else:
                ext = ".txt"
            
            output_file = os.path.join(temp_dir, f"{base_name}_processed{ext}")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.content)
            
            result.output_file = output_file
            
            # Save structured output if different
            if result.structured_output and result.structured_output != result.content:
                struct_file = os.path.join(temp_dir, f"{base_name}_structured.txt")
                with open(struct_file, 'w', encoding='utf-8') as f:
                    f.write(result.structured_output)
            
            # Save metadata if requested
            if config.include_metadata and result.metadata:
                meta_file = os.path.join(temp_dir, f"{base_name}_metadata.json")
                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump(result.metadata, f, indent=2)
            
            self.logger.log_success(f"Outputs saved: {output_file}")
            
        except Exception as e:
            self.logger.log_error(f"Failed to save outputs: {e}")
        
        return result
    
    def clear_cache(self):
        """Clear the processing cache."""
        if self.cache:
            self.cache.clear()
            self.logger.log_success("Cache cleared")
    
    def get_logs(self) -> str:
        """Get processing logs."""
        return self.logger.get_logs()
    
    def add_log_callback(self, callback: Callable[[str], None]):
        """Add a callback for real-time log updates."""
        self.logger.add_callback(callback)
