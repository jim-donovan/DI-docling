#!/usr/bin/env python3
"""
OCR Processor
Vision-first OCR with intelligent corruption detection
"""

import os
import sys
import traceback
import gradio as gr
from config import config
from ui import create_ui

def main():
    """Kickoff DI processor."""
    print("🎯 Document Ingestion 3.0")
    print("=" * 50)
    
    # Validate environment
    if not config.validate():
        print("❌ Configuration validation failed!")
        print("Make sure OPENAI_API_KEY is set in Space secrets")
        # Create a simple error interface
        with gr.Blocks() as error_demo:
            gr.Markdown("""
            # ❌ Configuration Error
            
            **OPENAI_API_KEY not found**
            """)
        return error_demo
    
    print(f"📋 Vision threshold: {config.vision_corruption_threshold}")
    print(f"🔧 Max vision calls: {config.max_vision_calls_per_doc}")
    print(f"🖼️  DPI: {config.dpi}")
    print(f"🤖 Vision model: {config.openai_model}")
    print(f"📝 Temperature: {config.temperature}")
    print("💡 Focus: Vision OCR priority, accuracy, speed")
    print("📄 Page ranges: Supports formats like '1-5, 10, 15-20'")
    print("=" * 50)
    
    try:
        demo = create_ui()
        return demo
        
    except Exception as e:
        print(f"❌ Interface creation failed: {e}")
        traceback.print_exc()
        
        with gr.Blocks() as error_demo:
            gr.Markdown(f"""
            # ❌ Application Error
            
            **Failed to start OCR Processor:**
            
            ```
            {str(e)}
            ```
            
            Please check the logs for more details.
            """)
        return error_demo

demo = main()

if __name__ == "__main__":
    demo.launch()