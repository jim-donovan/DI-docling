#!/usr/bin/env python3
"""
OCR Processor - Main Application
Clean, modular OCR processing with vision AI
"""

import os
import sys
import traceback
from config import config
from ui import create_ui



def check_dependencies():
    """Check if all required dependencies are available."""
    required_modules = [
        'fitz', # PyMuPDF
        'PIL',
        'numpy',
        'pytesseract',
        'gradio',
        'openai',
        'dotenv'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def validate_environment():
    """Validate environment configuration."""
    if not config.validate():
        print("❌ OPENAI_API_KEY not found. Please set it in .env file.")
        print("Create a .env file with: OPENAI_API_KEY=your_key_here")
        return False
    
    return True

def main():
    """Main application entry point."""
    print("🎯 OCR Processor - Starting Application")
    print("=" * 50)

    if not check_dependencies():
        sys.exit(1)
    
    if not validate_environment():
        sys.exit(1)
    
    print(f"📋 Vision threshold: {config.vision_corruption_threshold}")
    print(f"🔧 Max vision calls: {config.max_vision_calls_per_doc}")
    print(f"🖼️  DPI: {config.dpi}")
    print(f"🤖 Vision model: {config.openai_model}")
    print(f"📝 Temperature: {config.temperature}")
    print("💡 Focus: Vision OCR priority, accuracy, speed, transparency")
    print("📄 Page ranges: Supports formats like '1-5, 10, 15-20'")
    print("=" * 50)
    
    try:
        demo = create_ui()
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=True,
            show_error=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Launch failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()