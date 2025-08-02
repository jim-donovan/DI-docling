"""
Document Context Analyzer for SmolDocling
Analyzes document type and creates targeted extraction prompts
"""

import re
from typing import Dict, Tuple
from PIL import Image
import fitz
from logger import ProcessingLogger

class DocumentAnalyzer:
    """Analyze documents to create context-aware extraction prompts."""
    
    def __init__(self, logger: ProcessingLogger):
        self.logger = logger
        
        # Document type patterns
        self.document_patterns = {
            'financial': {
                'keywords': ['balance sheet', 'income statement', 'profit', 'loss', 'revenue', 
                           'expense', 'asset', 'liability', 'cash flow', 'financial statement',
                           'quarterly report', 'annual report', '10-k', '10-q'],
                'prompt_focus': "Pay special attention to numerical data, financial tables, currency amounts, percentages, and date ranges. Preserve all decimal places and number formatting."
            },
            'insurance': {
                'keywords': ['policy', 'coverage', 'deductible', 'premium', 'benefit', 'claim',
                           'insurance', 'copay', 'coinsurance', 'out-of-pocket', 'network'],
                'prompt_focus': "Focus on preserving benefit details, coverage amounts, policy numbers, and plan structures. Tables often contain tiered benefits that must maintain their relationships."
            },
            'legal': {
                'keywords': ['agreement', 'contract', 'whereas', 'herein', 'thereof', 'pursuant',
                           'obligation', 'party', 'terms and conditions', 'governing law'],
                'prompt_focus': "Preserve all legal language exactly, including section numbers, clause references, and formal terminology. Maintain document hierarchy and numbering systems."
            },
            'medical': {
                'keywords': ['patient', 'diagnosis', 'treatment', 'medication', 'prescription',
                           'symptoms', 'medical history', 'lab results', 'vital signs'],
                'prompt_focus': "Accurately capture medical terminology, dosages, test results, and clinical data. Preserve all abbreviations and medical codes exactly as written."
            },
            'technical': {
                'keywords': ['specification', 'requirement', 'implementation', 'architecture',
                           'api', 'endpoint', 'configuration', 'parameter', 'function'],
                'prompt_focus': "Maintain code formatting, technical specifications, and hierarchical structures. Preserve all technical abbreviations and version numbers."
            },
            'invoice': {
                'keywords': ['invoice', 'bill', 'payment due', 'subtotal', 'tax', 'total',
                           'item', 'quantity', 'unit price', 'po number', 'invoice number'],
                'prompt_focus': "Focus on line items, quantities, prices, and totals. Maintain the relationship between items and their corresponding amounts. Preserve all invoice identifiers."
            },
            'report': {
                'keywords': ['executive summary', 'findings', 'recommendations', 'analysis',
                           'methodology', 'conclusion', 'results', 'data', 'statistics'],
                'prompt_focus': "Preserve document structure including headings, subheadings, and bullet points. Maintain data relationships in charts and tables."
            }
        }
        
        # Table detection patterns
        self.table_patterns = [
            r'\s{2,}\S+\s{2,}\S+',  # Multiple spaces between text
            r'\|.*\|.*\|',          # Pipe-delimited
            r'\t.*\t',              # Tab-delimited
            r'^\s*\d+\.\d+\s+.*$',  # Numbered rows
        ]
    
    def analyze_document_type(self, first_page_text: str) -> Tuple[str, str]:
        """
        Analyze the document type based on first page content.
        
        Returns:
            tuple: (document_type, specialized_prompt_focus)
        """
        text_lower = first_page_text.lower()
        
        # Score each document type
        scores = {}
        for doc_type, config in self.document_patterns.items():
            score = sum(1 for keyword in config['keywords'] if keyword in text_lower)
            if score > 0:
                scores[doc_type] = score
        
        # Get the highest scoring type
        if scores:
            best_type = max(scores, key=scores.get)
            self.logger.log_success(f"Detected document type: {best_type} (confidence: {scores[best_type]})")
            return best_type, self.document_patterns[best_type]['prompt_focus']
        
        # Default
        return 'general', "Extract all text maintaining original layout and structure."
    
    def detect_table_complexity(self, page_text: str) -> str:
        """
        Detect if the page has complex tables and provide specific guidance.
        """
        # Count potential table indicators
        table_indicators = 0
        for pattern in self.table_patterns:
            matches = re.findall(pattern, page_text, re.MULTILINE)
            table_indicators += len(matches)
        
        if table_indicators > 10:
            return "\n\nThis page appears to contain complex tables. Ensure columns align properly and multi-line cells are kept together."
        elif table_indicators > 5:
            return "\n\nThis page contains tabular data. Maintain column alignment and relationships."
        
        return ""
    
    def create_contextual_prompt(self, page, page_no: int, first_page_analysis: Tuple[str, str] = None) -> str:
        """
        Create a context-aware prompt for SmolDocling based on document analysis.
        
        Args:
            page: The PDF page object
            page_no: Page number
            first_page_analysis: Optional pre-computed analysis from first page
            
        Returns:
            str: Customized extraction prompt
        """
        # Get page text for analysis
        try:
            page_text = page.get_text("text")[:1000]  # First 1000 chars for analysis
        except:
            page_text = ""
        
        # Base prompt
        base_prompt = """# Document Text Extraction

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
        
        # Add document type context
        if first_page_analysis:
            doc_type, focus = first_page_analysis
            if doc_type != 'general':
                base_prompt += f"\n\n**Document Type: {doc_type.title()}**\n{focus}"
        
        # Add table complexity guidance
        table_guidance = self.detect_table_complexity(page_text)
        if table_guidance:
            base_prompt += table_guidance
        
        # Add page-specific guidance
        if page_no == 1:
            base_prompt += "\n\nThis is the first page. Pay special attention to document headers, titles, and identifying information."
        elif "continued" in page_text.lower() or "page" in page_text.lower():
            base_prompt += "\n\nThis appears to be a continuation page. Maintain consistency with previous pages."
        
        return base_prompt
    
    def quick_analyze(self, pdf_path: str) -> Tuple[str, str]:
        """
        Quickly analyze a PDF's first page to determine document type.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            tuple: (document_type, specialized_prompt_focus)
        """
        try:
            with fitz.open(pdf_path) as doc:
                if len(doc) > 0:
                    first_page = doc[0]
                    first_page_text = first_page.get_text("text")
                    return self.analyze_document_type(first_page_text)
        except Exception as e:
            self.logger.log_error(f"Quick analysis failed: {e}")
        
        return 'general', "Extract all text maintaining original layout and structure."
