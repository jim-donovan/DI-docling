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

    openai_model: str = "gpt-4o"
    temperature: float = 0.0
    max_output_tokens: int = 2048

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

    def validate(self) -> bool:
        """Validate configuration settings."""
        try:
            _ = self.openai_api_key
            if not self.openai_model:
                raise ValueError("openai_model not set in Config.")
            return True
        except ValueError as e:
            print(f"Configuration validation error: {e}")
            return False

config = Config()
