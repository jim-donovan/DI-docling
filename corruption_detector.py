"""
Text Corruption Detection
Aggressive detection of OCR corruption patterns
"""

import re
from typing import Tuple, List
from config import config

class CorruptionDetector:
    """Aggressive corruption detection for OCR text."""
    
    @classmethod
    def should_use_vision(cls, text: str, vision_calls_used: int) -> Tuple[bool, str]:
        """
        Determine if vision OCR should be used based on corruption analysis.
        
        Args:
            text: Text to analyze
            vision_calls_used: Number of vision calls already made
            
        Returns:
            Tuple of (should_use_vision, reason)
        """
        
        # Check limits first
        if vision_calls_used >= config.max_vision_calls_per_doc:
            return False, f"Vision limit reached ({config.max_vision_calls_per_doc})"
        
        if len(text.strip()) < config.min_text_length:
            return False, f"Text too short ({len(text.strip())})"
        
        corruption_score = 0.0
        issues = []
        
        # Run all corruption checks
        corruption_score += cls._check_character_spacing(text, issues)
        corruption_score += cls._check_reversed_words(text, issues)
        corruption_score += cls._check_single_chars(text, issues)
        corruption_score += cls._check_encoding_issues(text, issues)
        corruption_score += cls._check_financial_corruption(text, issues)
        corruption_score += cls._check_punctuation_spam(text, issues)
        corruption_score += cls._check_fragmented_text(text, issues)
        corruption_score += cls._check_table_structure(text, issues)
        corruption_score += cls._check_word_length(text, issues)
        corruption_score += cls._check_content_density(text, issues)
        corruption_score += cls._check_symbols(text, issues)
        corruption_score += cls._check_content_sparsity(text, issues)
        
        should_use = (corruption_score >= config.vision_corruption_threshold or 
                     len(text.strip()) < config.min_content_length)
        
        reason = "; ".join(issues) if should_use else f"clean_text(score:{corruption_score:.2f})"
        
        return should_use, reason
    
    @classmethod
    def _check_character_spacing(cls, text: str, issues: List[str]) -> float:
        """Check for character spacing corruption."""
        space_count = text.count(' ')
        char_count = len(text.replace(' ', '').replace('\n', ''))
        
        if char_count > 0:
            space_ratio = space_count / char_count
            if space_ratio > 0.5:
                issues.append(f"character_spacing_corruption(ratio:{space_ratio:.2f})")
                return 0.8
        return 0.0
    
    @classmethod
    def _check_reversed_words(cls, text: str, issues: List[str]) -> float:
        """Check for reversed word patterns."""
        words = text.split()
        reversed_count = 0
        
        reversed_patterns = {
            'prefixes': ['gni', 'noi', 'eci', 'de', 'er'],
            'suffixes': ['erp', 'bus', 'noc', 'red'],
            'known_reversed': ['synapmoc', 'ecnarusni', 'dradnats']
        }
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if len(clean_word) >= 3:
                if (any(clean_word.startswith(p) for p in reversed_patterns['prefixes']) or
                    any(clean_word.endswith(s) for s in reversed_patterns['suffixes']) or
                    clean_word in reversed_patterns['known_reversed']):
                    reversed_count += 1
        
        if len(words) > 0 and reversed_count / len(words) > 0.05:
            issues.append(f"reversed_words({reversed_count}/{len(words)})")
            return 0.6
        return 0.0
    
    @classmethod
    def _check_single_chars(cls, text: str, issues: List[str]) -> float:
        """Check for excessive single character words."""
        words = text.split()
        single_chars = len([w for w in words if len(w) == 1 and w.isalpha()])
        
        if len(words) > 0 and single_chars / len(words) > 0.1:
            issues.append(f"single_char_words({single_chars})")
            return 0.7
        return 0.0
    
    @classmethod
    def _check_encoding_issues(cls, text: str, issues: List[str]) -> float:
        """Check for encoding corruption."""
        weird_chars = len(re.findall(r'[^\w\s.,!?;:()\-$%/€£¥\'"&@#*]', text))
        
        if weird_chars > len(text) * 0.01:
            issues.append(f"encoding_issues({weird_chars})")
            return 0.3
        return 0.0
    
    @classmethod
    def _check_financial_corruption(cls, text: str, issues: List[str]) -> float:
        """Check for financial pattern corruption."""
        suspicious_money = len(re.findall(r'\$\d*0{2,},\d{1,2}', text))
        
        if suspicious_money > 0:
            issues.append(f"financial_corruption({suspicious_money})")
            return 0.5
        return 0.0
    
    @classmethod
    def _check_punctuation_spam(cls, text: str, issues: List[str]) -> float:
        """Check for excessive punctuation."""
        question_spam = text.count('?')
        
        if question_spam > len(text) * 0.008:
            issues.append(f"question_spam({question_spam})")
            return 0.3
        return 0.0
    
    @classmethod
    def _check_fragmented_text(cls, text: str, issues: List[str]) -> float:
        """Check for fragmented sentences."""
        sentences = re.split(r'[.!?]\s+', text)
        short_sentences = len([s for s in sentences if len(s.split()) < 3 and len(s.strip()) > 0])
        
        if len(sentences) > 1 and short_sentences / len(sentences) > 0.3:
            issues.append(f"fragmented_text({short_sentences}/{len(sentences)})")
            return 0.4
        return 0.0
    
    @classmethod
    def _check_table_structure(cls, text: str, issues: List[str]) -> float:
        """Check for missing table structure."""
        pipe_count = text.count('|')
        table_words = ['condition', 'additional', 'topical', 'fluoride', 'cleaning', 'benefit']
        table_indicators = sum(1 for word in table_words if word.lower() in text.lower())
        
        if table_indicators >= 3 and pipe_count == 0:
            issues.append(f"missing_table_structure(indicators:{table_indicators})")
            return 0.6
        return 0.0
    
    @classmethod
    def _check_word_length(cls, text: str, issues: List[str]) -> float:
        """Check average word length."""
        words = text.split()
        if words:
            avg_word_length = sum(len(w) for w in words) / len(words)
            if avg_word_length < 2.5:
                issues.append(f"short_words(avg:{avg_word_length:.1f})")
                return 0.5
        return 0.0
    
    @classmethod
    def _check_content_density(cls, text: str, issues: List[str]) -> float:
        """Check content density."""
        sentences = re.split(r'[.!?]\n', text)
        if len(sentences) > 2:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_sentence_length < 5:
                issues.append(f"sparse_content(avg_sent:{avg_sentence_length:.1f})")
                return 0.3
        return 0.0
    
    @classmethod
    def _check_symbols(cls, text: str, issues: List[str]) -> float:
        """Check for symbols that need conversion."""
        checkmark_indicators = text.count('✓') + text.count('✔') + text.count('√')
        
        if checkmark_indicators > 0:
            issues.append(f"checkmark_symbols({checkmark_indicators})")
            return 0.7
        
        # Check for table structure words with symbols
        table_structure_words = ['eligible', 'condition', 'benefit', 'coverage', 'yes', 'no']
        table_word_count = sum(1 for word in table_structure_words if word.lower() in text.lower())
        
        if table_word_count >= 2 and ('|' not in text or checkmark_indicators > 0):
            issues.append(f"table_structure_needs_conversion(words:{table_word_count})")
            return 0.6
        
        return 0.0
    
    @classmethod
    def _check_content_sparsity(cls, text: str, issues: List[str]) -> float:
        """Check for sparse content."""
        lines = text.split('\n')
        substantial_lines = [line for line in lines if len(line.strip()) > 20]
        
        if len(substantial_lines) < config.min_substantial_lines:
            issues.append(f"sparse_content(substantial_lines:{len(substantial_lines)})")
            return 0.4
        return 0.0