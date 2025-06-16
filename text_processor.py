"""
Text Processing and Repair
OCR text cleanup and repair functions
"""

import re
import json
from typing import Dict, List
from dataclasses import dataclass, field
from openai import OpenAI
from config import config
from logger import ProcessingLogger


@dataclass
class DocumentContext:
    """Document context information."""
    companies: List[str] = field(default_factory=list)
    document_type: str = "Document"
    key_info: Dict[str, List[str]] = field(default_factory=dict)

class TextRepair:
    """Basic text repair for common OCR errors."""
    BASIC_FIXES = { 'rn': 'm', 'vv': 'w', 'cl': 'd', '½': '1/2', '¼': '1/4', '¾': '3/4'}
    FINANCIAL_FIXES = { r'\$005,(\d)': r'$\1,500', r'\$000,(\d+)': r'$\1,000', r'\$51\b': '$15', r'\$09\b': '$90'}

    @classmethod
    def basic_cleanup(cls, text: str) -> str:
        if not text: return text
        for wrong, correct in cls.BASIC_FIXES.items(): text = text.replace(wrong, correct)
        for pattern, replacement in cls.FINANCIAL_FIXES.items(): text = re.sub(pattern, replacement, text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1\n\n\2', text)
        return text.strip()

class ContextExtractor:
    """Extract document context and metadata."""

    def __init__(self, logger: ProcessingLogger):
        self.logger = logger
        self.client = OpenAI(
            api_key=config.openai_api_key
        )

    def extract_context(self, text: str) -> DocumentContext:
        self.logger.log_step("Extracting document context")

        try:
            prompt = f"""Extract key information from this document as JSON:

{text[:2000]}

Return JSON with:
- companies: List of company names
- document_type: Type of document
- key_info: Dict with "plans", "policies", "phones", "websites" as keys

Keep it simple and accurate. Ensure the output is ONLY the JSON object.
"""
            
            response = self.client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert context extractor. Extract information as valid JSON. Be concise and accurate."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=getattr(config, 'temperature', 0.1),
                max_tokens=getattr(config, 'max_output_tokens', 800)
            )

            content = response.choices[0].message.content.strip()

            if content.startswith("```json"):
                content = content[7:-3] if content.endswith("```") else content[7:]
            elif content.startswith("```"):
                content = content[3:-3] if content.endswith("```") else content[3:]

            data = json.loads(content)

            context = DocumentContext(
                companies=data.get("companies", []),
                document_type=data.get("document_type", "Document"),
                key_info=data.get("key_info", {})
            )

            self.logger.log_success(f"Context extracted: {context.document_type}")
            return context
            
        except json.JSONDecodeError as je:
            self.logger.log_error(f"Context extraction failed - JSONDecodeError: {je}. Raw LLM output: '{content}'")
            return DocumentContext()
        except Exception as e:
            self.logger.log_error(f"Context extraction failed: {type(e).__name__} - {e}")
            return DocumentContext()

class ContentFormatter:
    """Format extracted content into clean markdown."""

    def __init__(self, logger: ProcessingLogger):
        self.logger = logger

        self.client = OpenAI(
            api_key=config.openai_api_key
        )

    def format_content(self, text: str, page_no: int, context: DocumentContext) -> str:
        try:
            self.logger.log_step(f"Formatting page {page_no}")

            prompt = f"""Transform the extracted text using ONLY these specific formatting rules:

**1. Markdown Headers (# ## ###)**
- Apply ONLY to text that was clearly a header/title in the original document
- Use hierarchy that matches document structure (main sections #, subsections ##, etc.)

**2. Strategic Bold Formatting (**text**)**
Bold these specific data types for LLM attention, for example:
- Dollar amounts, example: **$3,300**, **$6,600**
- Percentages, example: **20%**, **40%**
- Phone numbers, example: **1-800-826-9781**
- Key dates, example: **01/01/2025 – 12/31/2025**
- Plan identifiers and important codes, example: **A1234567890**
- Maximum/minimum values and limits, example: **$3,300**, **$6,600**

**3. Table Structure Enhancement**
- Preserve the relationship between main categories and their sub-items
- Maintain the connection between row labels and their corresponding data across columns
- Treat text that wraps within cells as a single cell
- Preserve formatting indicators like asterisks and parentheses

**4. Special Handling Rules**
- Convert JSON structures at document start to clean bullet points
- Maintain table structure but choose ONE format consistently throughout

**Strict Preservation Rules:**
- Maintain exact text sequence from extraction
- Keep all original content including legal language
- Preserve paragraph breaks and document flow
- Do not add explanatory text or reorganize sections
- Do not interpret abbreviations or expand terms
- Keep all contact information and regulatory notices

**Output Requirements:**
- Apply formatting to enhance readability while preserving original structure
- Ensure all numerical data remains easily scannable by LLMs
- Maintain document integrity for accurate information retrieval
- Use consistent table formatting throughout the document

{text}
"""
            
            response = self.client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert document analysis AI. Format text as clean Markdown. Preserve all content exactly."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=getattr(config, 'temperature', 0.1),
                max_tokens=getattr(config, 'max_output_tokens', 2048)
            )

            result = response.choices[0].message.content.strip()

            if len(result) > 20:
                self.logger.log_success(f"Page {page_no} formatted ({len(result)} chars)")
                return result
            else:
                self.logger.log_warning(f"Page {page_no} formatting minimal, using basic format. LLM output: '{result}'")
                return self._basic_format(text, page_no)
                
        except Exception as e:
            self.logger.log_error(f"Page {page_no} formatting failed: {type(e).__name__} - {e}")
            return self._basic_format(text, page_no)

    def _basic_format(self, text: str, page_no: int) -> str:
        text = TextRepair.basic_cleanup(text)
        return f"## Page {page_no}\n\n{text}"

    def build_header(self, context: DocumentContext) -> str:
        parts = [f"# {context.document_type}"]
        if context.companies: parts.append(f"**Companies:** {', '.join(str(c) for c in context.companies)}")
        for key, values in context.key_info.items():
            if values:
                str_val_list = [str(v) for v in values if v] if isinstance(values, (list, tuple)) else ([str(values)] if values else [])
                if str_val_list: parts.append(f"**{key.title()}:** {', '.join(str_val_list)}")
        return "\n\n".join(parts)