"""
OCR Processing Engine with SmolDocling-256M-preview
Optimized document processing using SmolDocling model
Fixed for Idefics3Processor API compatibility
"""

import io
import time
import base64
import hashlib
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq
from typing import Dict, Tuple, List
import gc

from config import config
from logger import ProcessingLogger
from corruption_detector import CorruptionDetector
from text_processor import TextRepair
from document_analyzer import DocumentAnalyzer


class SmolDoclingOCREngine:
    """Optimized OCR processing engine using SmolDocling-256M-preview."""

    def __init__(self, logger: ProcessingLogger):
        self.logger = logger
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu")
        self.logger.log_section(f"Using device: {self.device}")

        # Initialize SmolDocling model
        self._initialize_model()
        
        # Initialize document analyzer
        self.document_analyzer = DocumentAnalyzer(self.logger)
        
        self.extraction_cache: Dict[str, str] = {}
        self.vision_calls_used = 0
        self.document_type = None  # Store document type after first page

    def _initialize_model(self):
        """Initialize the SmolDocling model with optimizations."""
        try:
            self.logger.log_step("Model initialization",
                                 "Loading SmolDocling-256M-preview")

            # Load the processor and model
            model_name = "ds4sd/SmolDocling-256M-preview"

            # Load processor
            self.processor = AutoProcessor.from_pretrained(model_name)

            # Load model with optimizations
            self.model = AutoModelForVision2Seq.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )

            # Move to device and set to evaluation mode
            if not torch.cuda.is_available():
                self.model = self.model.to(self.device)
            self.model.eval()

            self.logger.log_success("SmolDocling model loaded successfully")

        except Exception as e:
            self.logger.log_error(f"Failed to load SmolDocling model: {e}")
            raise

    def preprocess_image(self, img: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        # Convert to grayscale and enhance
        img_gray = img.convert('L')
        enhancer = ImageEnhance.Contrast(img_gray)
        img_enhanced = enhancer.enhance(1.5)

        img_array = np.array(img_enhanced)
        threshold = np.mean(img_array) * 0.85
        img_binary = np.where(img_array > threshold, 255, 0).astype(np.uint8)

        return Image.fromarray(img_binary)

    def extract_with_smoldocling(self, page, page_no: int, document_context: Tuple[str, str] = None) -> Tuple[str, Dict]:
        """Extract text and structure using SmolDocling model with contextual prompts."""
        self.logger.log_step(f"Page {page_no}", "Processing with SmolDocling")
        start_time = time.time()

        try:
            # Render page to image
            pix = page.get_pixmap(dpi=config.dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Generate hash for caching
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_hash = hashlib.md5(img_bytes.getvalue()).hexdigest()[:16]

            if img_hash in self.extraction_cache:
                self.logger.log_step(
                    f"Page {page_no}", "Using cached SmolDocling result")
                return self.extraction_cache[img_hash], {}

            # Process with SmolDocling
            with torch.no_grad():
                # Use contextual prompt based on document analysis
                if document_context:
                    prompt = self.document_analyzer.create_contextual_prompt(
                        page, page_no, document_context
                    )
                else:
                    # Fallback to basic prompt
                    prompt = """# Document Text Extraction

Extract ALL text from this document maintaining its layout.

For regular text:
- All headers, body text, footnotes, numbers, dates
- Legal text, contact information, disclaimers

For tables:
- Keep column headers clearly separated from data rows
- For multi-line cells, keep lines together with clear cell boundaries
- Empty cells should be represented with appropriate spacing
- Maintain visual column structure so data aligns under headers

Output text exactly as it appears with spatial relationships intact."""
                
                self.logger.log_step(f"Page {page_no}", f"Using {document_context[0] if document_context else 'general'} document prompt")

                # For Idefics3Processor, we need to use the correct format
                # Based on the model architecture, it expects a messages format with proper content structure
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image"},  # Image placeholder - processor will handle this
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]

                # Apply chat template and process inputs
                # The key fix: pass images separately to the processor
                text_inputs = self.processor.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    return_text=True  # Get text only first
                )
                
                # Now process with both text and images
                inputs = self.processor(
                    text=text_inputs,
                    images=[img],  # Pass as list of images
                    return_tensors="pt",
                    truncation=True,  # Explicitly enable truncation
                    max_length=2048  # Set reasonable max length
                ).to(self.device)

                # Generate text
                generation_kwargs = {
                    "max_new_tokens": 8000,
                    "do_sample": False,
                    "temperature": 0.1,
                    "pad_token_id": self.processor.tokenizer.pad_token_id,
                    "eos_token_id": self.processor.tokenizer.eos_token_id,
                }
                
                outputs = self.model.generate(
                    **inputs,
                    **generation_kwargs
                )

                # Decode the output
                # Get only the generated tokens (skip the input tokens)
                input_length = inputs['input_ids'].shape[-1]
                generated_tokens = outputs[0][input_length:]
                
                extracted_text = self.processor.decode(
                    generated_tokens,
                    skip_special_tokens=True
                )

            processing_time = time.time() - start_time

            # Cache result
            self.extraction_cache[img_hash] = extracted_text

            self.logger.log_success(
                f"Page {page_no} SmolDocling processing completed in {processing_time:.1f}s - {len(extracted_text)} chars"
            )

            # Increment vision calls counter
            self.vision_calls_used += 1

            # Clear GPU cache if using CUDA
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            return extracted_text, {}

        except Exception as e:
            self.logger.log_error(
                f"Page {page_no} SmolDocling processing failed: {e}")
            # Try a simpler fallback approach
            try:
                # Simple direct processing without chat template
                simple_prompt = "Extract all text from this document image:"
                inputs = self.processor(
                    text=simple_prompt,
                    images=img,
                    return_tensors="pt",
                    truncation=True,
                    max_length=8200
                ).to(self.device)
                
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=8200,
                    do_sample=False
                )
                
                # Decode all tokens since we don't know the exact input length
                extracted_text = self.processor.decode(
                    outputs[0],
                    skip_special_tokens=True
                )
                
                # Remove the prompt from the output if it appears
                if simple_prompt in extracted_text:
                    extracted_text = extracted_text.replace(simple_prompt, "").strip()
                
                self.logger.log_warning(
                    f"Page {page_no} used fallback processing method"
                )
                
                return extracted_text, {}
                
            except Exception as fallback_error:
                self.logger.log_error(
                    f"Page {page_no} fallback processing also failed: {fallback_error}"
                )
                return "", {}

    def extract_with_traditional_ocr(self, page, page_no: int) -> str:
        """Extract text using traditional OCR (Tesseract) as fallback."""
        try:
            self.logger.log_step(
                f"Page {page_no}", "Using traditional OCR (fallback)")

            pix = page.get_pixmap(dpi=config.dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            processed_img = self.preprocess_image(img)
            ocr_text = pytesseract.image_to_string(
                processed_img, config='--oem 3 --psm 3')

            result = TextRepair.basic_cleanup(ocr_text)
            self.logger.log_success(
                f"Page {page_no} traditional OCR completed - {len(result)} chars")
            return result

        except Exception as e:
            self.logger.log_error(
                f"Page {page_no} traditional OCR failed: {e}")
            return f"OCR extraction failed for page {page_no}"

    def extract_page_text(self, page, page_no: int, pdf_path: str = None) -> str:
        """Main text extraction method with intelligent processing selection."""
        # Analyze document type on first page
        if page_no == 1 and pdf_path and not self.document_type:
            self.document_type = self.document_analyzer.quick_analyze(pdf_path)
        try:
            # Try PDF text extraction first
            pdf_text = page.get_text("text")

            if pdf_text and len(pdf_text.strip()) > 30:
                cleaned_text = TextRepair.basic_cleanup(pdf_text.strip())

                should_use_vision, reason = CorruptionDetector.should_use_vision(
                    cleaned_text, self.vision_calls_used
                )

                self.logger.log_step(
                    f"Page {page_no}",
                    f"Text length: {len(cleaned_text)}, SmolDocling decision: {should_use_vision} ({reason})"
                )

                if should_use_vision:
                    # Use SmolDocling for complex documents
                    smoldocling_result, layout_info = self.extract_with_smoldocling(
                        page, page_no, self.document_type)

                    # Validate SmolDocling result
                    if len(smoldocling_result.strip()) > 30:
                        self.logger.log_success(
                            f"Page {page_no} using SmolDocling result ({len(smoldocling_result)} chars)"
                        )
                        return smoldocling_result
                    else:
                        self.logger.log_warning(
                            f"Page {page_no} SmolDocling result too minimal, using PDF text")
                        return cleaned_text

                return cleaned_text

        except Exception as e:
            self.logger.log_error(f"Page {page_no} PDF extraction failed: {e}")

        # Try SmolDocling first for pages without extractable text
        smoldocling_result, _ = self.extract_with_smoldocling(page, page_no, self.document_type)
        if smoldocling_result and len(smoldocling_result.strip()) > 30:
            return smoldocling_result

        # Fallback to traditional OCR
        return self.extract_with_traditional_ocr(page, page_no)

    def get_vision_calls_used(self) -> int:
        """Get the number of SmolDocling calls used."""
        return self.vision_calls_used

    def reset_vision_counter(self) -> None:
        """Reset the vision calls counter and document type."""
        self.vision_calls_used = 0
        self.document_type = None

    def cleanup(self):
        """Clean up resources and free memory."""
        try:
            # Clear cache
            self.extraction_cache.clear()

            # Delete model and processor
            if hasattr(self, 'model'):
                del self.model
            if hasattr(self, 'processor'):
                del self.processor

            # Clear GPU cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Force garbage collection
            gc.collect()

            self.logger.log_success("Resources cleaned up successfully")

        except Exception as e:
            self.logger.log_error(f"Error during cleanup: {e}")
