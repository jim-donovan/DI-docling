"""
OCR Processor Logging System
Clean, timestamp-based logging with multiple output options
"""

import time
from typing import List, Callable, Optional

class ProcessingLogger:
    """Simple, efficient logger for OCR processing."""
    
    def __init__(self):
        self.logs: List[str] = []
        self.callbacks: List[Callable[[str], None]] = []
    
    def log(self, message: str) -> None:
        """Log a message with timestamp."""
        timestamp = time.strftime('%H:%M:%S')
        formatted = f"[{timestamp}] {message}"
        
        self.logs.append(formatted)
        
        print(formatted)
        
        for callback in self.callbacks:
            try:
                callback(formatted)
            except Exception as e:
                print(f"[{timestamp}] Logger callback error: {e}")
    
    def add_callback(self, callback: Callable[[str], None]) -> None:
        """Add a callback for real-time log updates."""
        self.callbacks.append(callback)
    
    def get_logs(self) -> str:
        """Get all logs as a single string."""
        return "\n".join(self.logs)
    
    def clear(self) -> None:
        """Clear all logs."""
        self.logs.clear()
    
    def get_recent_logs(self, count: int = 10) -> str:
        """Get the most recent N log entries."""
        return "\n".join(self.logs[-count:])
    
    def log_section(self, title: str) -> None:
        """Log a section header for better organization."""
        separator = "=" * 50
        self.log(f"\n{separator}")
        self.log(f"📋 {title}")
        self.log(separator)
    
    def log_step(self, step: str, detail: str = "") -> None:
        """Log a processing step with optional detail."""
        if detail:
            self.log(f"🔄 {step}: {detail}")
        else:
            self.log(f"🔄 {step}")
    
    def log_success(self, message: str) -> None:
        """Log a success message."""
        self.log(f"✅ {message}")
    
    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        self.log(f"⚠️  {message}")
    
    def log_error(self, message: str) -> None:
        """Log an error message."""
        self.log(f"❌ {message}")
    
    def log_metric(self, name: str, value: any) -> None:
        """Log a metric value."""
        self.log(f"📊 {name}: {value}")