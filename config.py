# config.py
"""
OCR Processor Configuration
Simple, centralized configuration management
"""

import os
from dataclasses import dataclass

if not os.getenv("SPACE_ID"):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


@dataclass
class Config:
    """Centralized configuration for OCR processing."""

    # Vision OCR Settings
    vision_corruption_threshold: float = 0.10
    max_vision_calls_per_doc: int = 100
    dpi: int = 300

    # Model Selection
    # For extraction/OCR (SmolDocling)
    extraction_model: str = "ds4sd/SmolDocling-256M-preview"

    # For formatting and context extraction (OpenAI)
    # Options: "gpt-4o", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "o1-preview", "o1-mini"
    formatting_model: str = "gpt-5"  # Change this to "gpt-4" or other models
    context_model: str = "gpt-5"     # Can be different from formatting model

    # Model parameters
    temperature: float = 0.0
    # Slightly higher for more creative formatting
    formatting_temperature: float = 0.1
    max_output_tokens: int = 8000  # Increased for better formatting

    # Fallback model for when SmolDocling fails
    fallback_vision_model: str = "gpt-4o"  # For OpenAI Vision API fallback

    # Processing Settings
    min_text_length: int = 10
    min_substantial_lines: int = 2
    min_content_length: int = 100

    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key from environment."""
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables."
            )
        return key

    @property
    def openai_model(self) -> str:
        """Legacy property for backward compatibility."""
        return self.formatting_model

    def validate(self) -> bool:
        """Validate configuration settings."""
        try:
            _ = self.openai_api_key
            if not self.formatting_model:
                raise ValueError("formatting_model not set in Config.")
            return True
        except ValueError as e:
            print(f"Configuration validation error: {e}")
            return False


config = Config()
