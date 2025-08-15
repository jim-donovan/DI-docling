#!/usr/bin/env python3
"""
Launcher for DI-Docling Document Processor
Streamlined launcher for the docling application
"""

import sys
import subprocess
from pathlib import Path


def print_header():
    """Print application header."""
    print("=" * 60)
    print("     DI-Docling Document Processor")
    print("     Powered by IBM Docling & SmolDocling")
    print("=" * 60)


def check_requirements():
    """Check if required packages are installed."""
    try:
        import gradio
        print("✅ Core dependencies verified")
        return True
    except ImportError as e:
        print(f"⚠️  Missing dependency: {e}")
        print("\nInstall requirements with:")
        print("  pip install -r requirements.txt")
        return False


def run_app():
    """Run the main application."""
    print("\n🚀 Starting Document Processor...")
    print("\nFeatures:")
    print("  ✅ Native Docling processing")
    print("  ✅ SmolDocling OCR fallback")
    print("  ✅ Multi-format support (PDF, DOCX, PPTX)")
    print("  ✅ Intelligent caching")
    print("  ✅ Optional AI formatting")
    print("\n" + "-" * 60)
    print("Launching web interface...")
    print("-" * 60 + "\n")
    
    try:
        subprocess.run([sys.executable, "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running application: {e}")
        print("Try installing requirements: pip install -r requirements.txt")
    except KeyboardInterrupt:
        print("\n\n✅ Application closed")


def main():
    """Main launcher logic."""
    print_header()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["--help", "-h", "help"]:
            print("\nUsage:")
            print("  python run.py          # Run the application")
            print("  python run.py --help   # Show this help")
            return
    
    # Check requirements and run app
    if check_requirements():
        run_app()
    else:
        print("\n❌ Please install missing dependencies first")
        sys.exit(1)


if __name__ == "__main__":
    main()
