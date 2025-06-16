"""
OCR Processing Engine
Core OCR functionality with vision and traditional OCR
"""

import io
import time
import base64
import hashlib
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance
import openai
import google.generativeai as genai
from typing import Dict

from config import config
from logger import ProcessingLogger
from corruption_detector import CorruptionDetector
from text_processor import TextRepair

class OCREngine:
    """Core OCR processing engine with vision and traditional OCR."""
    
    def __init__(self, logger: ProcessingLogger):
        self.logger = logger
        genai.configure(api_key=config.openai_api_key)
        self.vision_cache: Dict[str, str] = {}
        self.vision_calls_used = 0
    
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
    
    def extract_with_vision(self, page, page_no: int, pdf_text: str) -> str:
        """Extract text using OpenAI Vision API with caching."""
        text_hash = hashlib.md5(pdf_text.encode()).hexdigest()[:16]
        
        if text_hash in self.vision_cache:
            self.logger.log_step(f"Page {page_no}", "Using cached vision result")
            return self.vision_cache[text_hash]
        
        self.logger.log_step(f"Page {page_no}", "Applying vision OCR")
        start_time = time.time()
        
        try:
            pix = page.get_pixmap(dpi=config.dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Vision prompt
            prompt = """
# Document Text Extraction and Transcription

Extract ALL text from this document image exactly as it appears:
- Original text order and hierarchy
- All numerical data, dates, and financial information
- Contact information and legal notices
- Do not skip content that appears repetitive or administrative
- Include all legal disclaimers and regulatory language

Table Structure:
- Detect spans using whitespace analysis and text positioning
- Ensure each row and column has a consistent number of cells
- Return cell text in reading order (left-to-right, top-to-bottom)
- **Propagate merged cell content to all constituent cells**

Output only the extracted text - no commentary, formatting, or interpretation.
"""
            
            client = openai.OpenAI(api_key=config.openai_api_key)
            response = client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {"role": "system", "content": "You are an AI vision specialist focused on complete, accurate text recognition from document images. Your primary mission is to capture ALL textual content exactly as it appears while organizing it in a logical, digestible format that preserves every piece of information."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Please extract all text from this document image, preserving structure and accuracy."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=config.temperature,
            )
            
            result = response.choices[0].message.content.strip()
            processing_time = time.time() - start_time
            
            # Cache result
            self.vision_cache[text_hash] = result
            self.logger.log_success(f"Page {page_no} vision OCR completed in {processing_time:.1f}s - {len(result)} chars")
            
            return result
            
        except Exception as e:
            self.logger.log_error(f"Page {page_no} vision OCR failed: {e}")
            return TextRepair.basic_cleanup(pdf_text)
    
    def extract_with_traditional_ocr(self, page, page_no: int) -> str:
        """Extract text using traditional OCR (Tesseract)."""
        try:
            self.logger.log_step(f"Page {page_no}", "Using traditional OCR")
            
            pix = page.get_pixmap(dpi=config.dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            processed_img = self.preprocess_image(img)
            ocr_text = pytesseract.image_to_string(processed_img, config='--oem 3 --psm 3')
            
            result = TextRepair.basic_cleanup(ocr_text)
            self.logger.log_success(f"Page {page_no} traditional OCR completed - {len(result)} chars")
            return result
            
        except Exception as e:
            self.logger.log_error(f"Page {page_no} traditional OCR failed: {e}")
            return f"OCR extraction failed for page {page_no}"
    
    def extract_page_text(self, page, page_no: int) -> str:
        """Main text extraction method with intelligent OCR selection."""
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
                    f"Text length: {len(cleaned_text)}, Vision decision: {should_use_vision} ({reason})"
                )
                
                if should_use_vision:
                    vision_result = self.extract_with_vision(page, page_no, cleaned_text)
                    
                    # Validate vision result
                    if len(vision_result.strip()) > 30:
                        self.vision_calls_used += 1
                        self.logger.log_success(f"Page {page_no} using vision result ({len(vision_result)} chars)")
                        return vision_result
                    else:
                        self.logger.log_warning(f"Page {page_no} vision result too minimal")
                        return cleaned_text
                
                return cleaned_text
                
        except Exception as e:
            self.logger.log_error(f"Page {page_no} PDF extraction failed: {e}")
        
        # Fallback to traditional OCR
        return self.extract_with_traditional_ocr(page, page_no)
    
    def get_vision_calls_used(self) -> int:
        """Get the number of vision API calls used."""
        return self.vision_calls_used
    
    def reset_vision_counter(self) -> None:
        """Reset the vision calls counter."""
        self.vision_calls_used = 0