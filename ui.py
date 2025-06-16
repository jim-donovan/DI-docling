"""
Gradio User Interface
Clean, modern UI for the OCR processor
"""

import gradio as gr
from processor import DocumentProcessor
from config import config
from utils import validate_page_ranges

class OCRInterface:
    """Gradio interface for OCR processing."""
    
    def __init__(self):
        self.processor = DocumentProcessor()
    
    def get_css(self) -> str:
        """Get CSS styling for the interface."""
        return """
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&family=Montserrat+Alternates:wght@400;500;600;700;800&display=swap');
        
        .gradio-container { 
            max-width: 1500px !important; 
            margin: 0 auto !important;
            font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
            background: linear-gradient(135deg, #1a1b2e 0%, #16213e 100%) !important;
            min-height: 100vh !important;
        }
        
        .main-header { 
            background: linear-gradient(135deg, #4c1d95 0%, #6b21a8 50%, #7c3aed 100%);
            padding: 2.5rem 2rem; 
            border-radius: 16px; 
            color: #f8fafc; 
            text-align: center; 
            margin-bottom: 2rem;
            box-shadow: 0 8px 25px rgba(76, 29, 149, 0.3);
            border: 1px solid rgba(139, 92, 246, 0.2);
        }
        
        .main-header h1 {
            margin: 0 0 1rem 0;
            font-size: 2.5rem;
            font-weight: 800;
            font-family: 'Montserrat Alternates', sans-serif !important;
            background: linear-gradient(135deg, #ffffff 0%, #e0e7ff 100%);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .left-panel {
            background: rgba(30, 41, 59, 0.6) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(139, 92, 246, 0.1) !important;
        }
        
        .section-header {
            font-family: 'Montserrat Alternates', sans-serif !important;
            font-size: 1.2rem;
            font-weight: 600;
            color: #e0e7ff;
            margin: 1.5rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid rgba(139, 92, 246, 0.3);
        }
        
        .status-box { 
            background: rgba(30, 41, 59, 0.8); 
            border: 1px solid rgba(139, 92, 246, 0.2); 
            border-radius: 10px; 
            padding: 1rem 1.25rem; 
            margin: 1rem 0;
            font-weight: 500;
            color: #f1f5f9;
        }
        
        .status-success { 
            background: rgba(22, 101, 52, 0.2); 
            color: #86efac; 
            border-color: rgba(34, 197, 94, 0.4);
        }
        .status-error { 
            background: rgba(127, 29, 29, 0.2); 
            color: #fca5a5; 
            border-color: rgba(239, 68, 68, 0.4);
        }
        .status-processing { 
            background: rgba(146, 64, 14, 0.2); 
            color: #fbbf24; 
            border-color: rgba(245, 158, 11, 0.4);
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
            margin: 1rem 0;
        }
        
        .metric-card {
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid rgba(139, 92, 246, 0.2);
            border-radius: 10px;
            padding: 1.25rem;
            text-align: center;
        }
        
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #e0e7ff;
            margin-bottom: 0.25rem;
        }
        
        .metric-label {
            font-size: 0.875rem;
            color: #94a3b8;
            font-weight: 500;
        }
        
        .console { 
            background: #0f172a !important; 
            color: #e2e8f0 !important; 
            font-family: 'Fira Code', 'Courier New', monospace !important;
            border: 1px solid rgba(139, 92, 246, 0.3) !important;
            border-radius: 8px !important;
        }
        
        .primary-btn {
            background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%) !important;
            border: none !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 15px rgba(124, 58, 237, 0.3) !important;
        }
        """
    
    def process_wrapper(self, uploaded_file, user_threshold, page_ranges_str):
        """Wrapper for document processing with UI updates."""
        config.vision_corruption_threshold = user_threshold
        self.processor.logger.log_section(f"Vision threshold set to: {user_threshold}")
        
        if not uploaded_file:
            return self._no_file_response()
        
        if page_ranges_str and page_ranges_str.strip():
            try:
                import fitz
                with fitz.open(uploaded_file.name) as doc:
                    total_pages = len(doc)
                    
                is_valid, error_msg, parsed_pages = validate_page_ranges(page_ranges_str, total_pages)
                if not is_valid:
                    return self._error_response(f"Invalid page ranges: {error_msg}")
                    
                self.processor.logger.log_section(f"Processing pages: {page_ranges_str}")
            except Exception as e:
                return self._error_response(f"Error validating page ranges: {str(e)}")
        
        yield self._processing_state()
        
        try:
            result = self.processor.process_document(uploaded_file, page_ranges_str if page_ranges_str and page_ranges_str.strip() else None)

            metrics_html = self._generate_metrics(result)
            analytics_html = self._generate_analytics(result)
            status_html = self._generate_status(result)
            
            yield (
                result.content,
                result.logs,
                status_html,
                metrics_html,
                result.output_file,
                analytics_html,
                gr.update(visible=True)
            )
            
        except Exception as e:
            yield self._error_response(str(e))
    
    def _no_file_response(self):
        """Response when no file is uploaded."""
        return (
            "*Please upload a PDF file to begin processing.*",
            "",
            "<div class='status-box status-error'>❌ No file uploaded</div>",
            "<div class='status-box'>No metrics available</div>",
            None,
            "<div class='status-box status-error'>Please upload a PDF file</div>",
            gr.update(visible=False)
        )
    
    def _processing_state(self):
        """Response during processing."""
        return (
            "*🚀 Processing started...*",
            "🚀 Initializing OCR processor...\n",
            "<div class='status-box status-processing'>⏳ Processing document...</div>",
            "<div class='status-box status-processing'>⏳ Processing in progress...</div>",
            None,
            "<div class='status-box status-processing'>Processing in progress...</div>",
            gr.update(visible=True)
        )
    
    def _error_response(self, error_msg):
        """Response for processing errors."""
        return (
            f"*❌ Processing Error: {error_msg}*",
            f"ERROR: {error_msg}",
            f"<div class='status-box status-error'>❌ Error: {error_msg}</div>",
            "<div class='status-box status-error'>❌ Processing failed</div>",
            None,
            f"<div class='status-box status-error'>Error: {error_msg}</div>",
            gr.update(visible=True)
        )
    
    def _generate_metrics(self, result):
        """Generate metrics HTML."""
        return f"""
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{result.processing_time:.1f}s</div>
                <div class="metric-label">Total Time</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{result.vision_calls_used}</div>
                <div class="metric-label">Vision Calls</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{"✓" if result.success else "✗"}</div>
                <div class="metric-label">Status</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{len(result.content.split()) if result.content else 0}</div>
                <div class="metric-label">Words</div>
            </div>
        </div>
        """
    
    def _generate_analytics(self, result):
        """Generate detailed analytics HTML."""
        vision_efficiency = f"{(result.vision_calls_used / max(result.pages_processed, 1)):.1f}" if result.pages_processed > 0 else "0"
        
        return f"""
        <div class="status-box {'status-success' if result.success else 'status-error'}">
            <h4>📊 Processing Analytics</h4>
            <p><strong>Pages:</strong> {result.pages_processed}</p>
            <p><strong>Vision calls:</strong> {result.vision_calls_used} ({vision_efficiency} per page)</p>
            <p><strong>Words extracted:</strong> {len(result.content.split()) if result.content else 0}</p>
            <p><strong>Status:</strong> {"Success" if result.success else "Failed"}</p>
        </div>
        """
    
    def _generate_status(self, result):
        """Generate status HTML."""
        if result.success:
            return "<div class='status-box status-success'>✅ Processing completed successfully!</div>"
        else:
            return f"<div class='status-box status-error'>❌ Processing failed: {result.status}</div>"
    
    def clear_all(self):
        """Clear all interface elements."""
        self.processor.clear_logs()
        return (
            "*Processed document content will appear here after processing...*",
            "",
            "<div class='status-box'>⏳ Ready to process document...</div>",
            "<div class='status-box'>Metrics will appear during processing...</div>",
            None,
            "<div class='status-box'>Analytics will appear after processing...</div>",
            gr.update(visible=False)
        )
    
    def create_interface(self):
        """Create the Gradio interface."""
        with gr.Blocks(title="OCR Processor", css=self.get_css()) as demo:
            
            # Header
            gr.HTML("""
                <div class="main-header">
                    <h1>🎯 OCR Processor</h1>
                    <p>Vision-first OCR with intelligent corruption detection and complete information preservation.</p>
                </div>
            """)
            
            with gr.Row():
                # Left Panel - Controls
                with gr.Column(scale=1, elem_classes="left-panel"):
                    
                    gr.HTML('<div class="section-header">📁 Upload Document</div>')
                    pdf_input = gr.File(label="PDF File", file_types=[".pdf"])
                    
                    # Page ranges input
                    page_ranges_input = gr.Textbox(
                        label="Page Ranges (Optional)",
                        placeholder="e.g., 1-5, 10, 15-20 (leave blank for all pages)",
                        info="Specify pages to process. Examples: '1-5' for pages 1-5, '1,3,5' for specific pages, '1-3,10-15' for multiple ranges"
                    )
                    
                    with gr.Row():
                        process_btn = gr.Button("🚀 Process", variant="primary", elem_classes="primary-btn")
                        clear_btn = gr.Button("🗑️ Clear", variant="secondary", visible=False)
                    
                    gr.HTML('<div class="section-header">📊 Status</div>')
                    status_output = gr.HTML(value="<div class='status-box'>⏳ Ready to process document...</div>")
                    
                    gr.HTML('<div class="section-header">📈 Metrics</div>')
                    metrics_output = gr.HTML(value="<div class='status-box'>Metrics will appear during processing...</div>")
                    
                    gr.HTML('<div class="section-header">⚙️ Configuration</div>')
                    gr.HTML(f"""
                        <div class="status-box">
                            <p><strong>Vision threshold:</strong> {config.vision_corruption_threshold}</p>
                            <p><strong>Max vision calls:</strong> {config.max_vision_calls_per_doc}</p>
                            <p><strong>DPI:</strong> {config.dpi}</p>
                            <p><strong>Model Used:</strong> {config.openai_model}</p>
                        </div>
                    """)
                    
                    vision_threshold_slider = gr.Slider(
                        minimum=0.01,
                        maximum=0.5,
                        value=config.vision_corruption_threshold,
                        step=0.01,
                        label="Vision Model Threshold (Corruption Score)",
                        info="Lower = more aggressive vision usage. Higher = less vision usage."
                    )
                
                # Right Panel - Results
                with gr.Column(scale=2):
                    
                    with gr.Tabs():
                        with gr.Tab("📄 Document"):
                            content_output = gr.Markdown(
                                value="*Processed document content will appear here...*", 
                                show_copy_button=True
                            )
                        
                        with gr.Tab("🔍 Logs"):
                            logs_output = gr.Textbox(
                                label="Processing Logs", 
                                lines=28, 
                                interactive=False, 
                                elem_classes="console",
                                show_copy_button=True
                            )
                        
                        with gr.Tab("💾 Download"):
                            file_output = gr.File(label="Processed File", interactive=False)
                            analytics_output = gr.HTML(value="<div class='status-box'>Analytics will appear after processing...</div>")
            
            gr.Markdown("""
            **Vision Model Threshold:**  
            This controls how sensitive the system is to possible text corruption.  
            - **Lower values (e.g., 0.05):** More aggressive, vision model will be used more often (higher cost, higher accuracy).
            - **Higher values (e.g., 0.3):** Less aggressive, vision model used less often (lower cost, may miss subtle issues).
            
            **Page Ranges:**  
            Supports formats like '1-5, 10, 15-20'. Leave blank to process all pages.
            """)
            
            process_btn.click(
                fn=self.process_wrapper,
                inputs=[pdf_input, vision_threshold_slider, page_ranges_input],
                outputs=[content_output, logs_output, status_output, metrics_output, file_output, analytics_output, clear_btn],
                show_progress="full"
            )
            
            clear_btn.click(
                fn=self.clear_all,
                outputs=[content_output, logs_output, status_output, metrics_output, file_output, analytics_output, clear_btn]
            )
        
        return demo

def create_ui():
    """Factory function to create the UI."""
    interface = OCRInterface()
    return interface.create_interface()