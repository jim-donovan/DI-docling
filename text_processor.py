"""
Text Processing and Formatting
Text cleanup and markdown formatting for OCR output
"""

import re
from typing import Dict, List
from openai import OpenAI
from config import config
from logger import ProcessingLogger


class TextRepair:
    """Basic text repair for common OCR errors."""
    BASIC_FIXES = {
        'rn': 'm',
        'vv': 'w',
        'cl': 'd',
        '½': '1/2',
        '¼': '1/4',
        '¾': '3/4'
    }

    FINANCIAL_FIXES = {
        r'\$005,(\d)': r'$\1,500',
        r'\$000,(\d+)': r'$\1,000',
        r'\$51\b': '$15',
        r'\$09\b': '$90'
    }

    @classmethod
    def basic_cleanup(cls, text: str) -> str:
        """Clean up common OCR errors in text."""
        if not text:
            return text

        # Apply basic character fixes
        for wrong, correct in cls.BASIC_FIXES.items():
            text = text.replace(wrong, correct)

        # Apply financial pattern fixes
        for pattern, replacement in cls.FINANCIAL_FIXES.items():
            text = re.sub(pattern, replacement, text)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)

        # Add paragraph breaks after sentences
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1\n\n\2', text)

        return text.strip()


class ContentFormatter:
    """Format extracted content into clean markdown."""

    def __init__(self, logger: ProcessingLogger):
        self.logger = logger
        self.client = OpenAI(api_key=config.openai_api_key)

    def format_content(self, text: str, page_no: int, document_title: str = None) -> str:
        """
        Format extracted text using OpenAI model.

        Args:
            text: Raw extracted text
            page_no: Page number
            document_title: Optional document title (not used in new flow)

        Returns:
            Formatted markdown text
        """
        try:
            self.logger.log_step(f"Formatting page {page_no}")

            prompt = f"""Transform the extracted text using these formatting rules:

**Table Transformation:**
When you encounter data that appears to be in table format (aligned columns of data):
- Treat text that wraps within cells as a single cell:
  - Identify column headers (typically the utmost top labels)
  - Identify row headers (typically the leftmost column)
- For each data value, create a **flattened structured entry** that connects it to both its row and column
- Use this format: **[Row Label, including wrapped cell content]** - **[Column Label, including wrapped cell content]**: [Value]

**Headers:**
- Apply # for main document titles
- Apply ## for major sections
- Apply ### for subsections
- Only use markdown headers for actual document headings, not data labels
- Ignore page breaks when evaluating header hierarchy

**Lists and Sections:**
- Preserve bullet points and numbered lists
- Maintain logical groupings of related information
- Keep indentation patterns and data hierarchy

**Preservation Rules:**
- Do not change the words of the original text
- Maintain all parentheses, asterisks, and special characters
- Do not expand abbreviations or add explanatory text
- Preserve all numbers, dates, and formatting indicators

{text}
"""

            response = self.client.chat.completions.create(
                model=config.formatting_model,
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
                temperature=getattr(config, 'formatting_temperature', 0.1),
                max_tokens=getattr(config, 'max_output_tokens', 4096)
            )

            result = response.choices[0].message.content.strip()

            if len(result) > 20:
                self.logger.log_success(
                    f"Page {page_no} formatted ({len(result)} chars)")
                return result
            else:
                self.logger.log_warning(
                    f"Page {page_no} formatting minimal, using basic format")
                return self._basic_format(text, page_no)

        except Exception as e:
            self.logger.log_error(
                f"Page {page_no} formatting failed: {type(e).__name__} - {e}")
            return self._basic_format(text, page_no)

    def _basic_format(self, text: str, page_no: int) -> str:
        """Basic formatting fallback."""
        text = TextRepair.basic_cleanup(text)
        return f"## Page {page_no}\n\n{text}"
