"""
Streamlit-style Gradio UI for DocTags Document Processor
Uses SmolDocling with DocTags format for document structure understanding
"""

import gradio as gr
import tempfile
import time
from pathlib import Path
from typing import Optional

from processor_doctags_simple import SimplifiedDocTagsProcessor


class DocTagsDocumentUI:
    def __init__(self):
        self.processor = SimplifiedDocTagsProcessor()
        self.current_logs = []

    def process_document(
        self,
        file,
        page_ranges: str,
        batch_size: int,
        export_doctags: bool,
        progress=gr.Progress()
    ):
        """Process uploaded document with progress tracking."""
        if file is None:
            return "Please upload a PDF file.", "", None, None

        def progress_callback(message: str):
            progress(0.5, desc=message)

        def log_callback(log_entry: str):
            self.current_logs.append(log_entry)

        # Clear previous logs
        self.current_logs = []
        self.processor.clear_logs()
        self.processor.add_log_callback(log_callback)

        # Process the document
        result = self.processor.process_document(
            uploaded_file=file,
            page_ranges_str=page_ranges if page_ranges.strip() else None,
            progress_callback=progress_callback,
            batch_size=batch_size,
            use_native_docling=export_doctags  # Use native docling if checkbox is checked
        )

        # Prepare outputs
        logs_text = "\n".join(self.current_logs)

        # Get download files
        download_files = []
        if result.output_file:
            download_files.append(result.output_file)

        # Check for structured output file
        if result.output_file:
            base_path = Path(result.output_file)
            struct_path = base_path.parent / \
                (base_path.stem.replace(
                    '_processed_doctags_style', '_structured') + '.txt')
            if struct_path.exists():
                download_files.append(str(struct_path))

        return result.content, logs_text, download_files[0] if download_files else None, download_files[1] if len(download_files) > 1 else None

    def create_interface(self):
        """Create the Gradio interface."""
        with gr.Blocks(
            title="DocTags Document Processor",
            theme=gr.themes.Soft(),
            css="""
            .gradio-container {
                font-family: 'Inter', sans-serif;
            }
            .output-markdown {
                max-height: 600px;
                overflow-y: auto;
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 8px;
                font-family: 'Fira Code', monospace;
                font-size: 14px;
                line-height: 1.6;
            }
            .log-output {
                max-height: 400px;
                overflow-y: auto;
                padding: 15px;
                background-color: #1e1e1e;
                color: #d4d4d4;
                border-radius: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                line-height: 1.4;
            }
            """
        ) as app:
            # Header
            gr.Markdown(
                """
                # 🚀 DocTags Document Processor
                
                Transform your PDFs using **SmolDocling-256M** with **IBM DocTags** format for semantic document understanding.
                
                ### 🎯 Key Features:
                - **📊 DocTags Format**: Semantic markup designed for LLMs
                - **🧠 Structure Understanding**: Tables, lists, headings, figures, and more
                - **⚡ Local Processing**: No API calls, runs on your infrastructure
                - **🔍 Smart Detection**: Automatically identifies document elements
                """
            )

            with gr.Row():
                with gr.Column(scale=1):
                    # Input controls
                    file_input = gr.File(
                        label="📄 Upload PDF Document",
                        file_types=[".pdf"],
                        type="filepath"
                    )

                    with gr.Accordion("⚙️ Advanced Options", open=False):
                        page_ranges = gr.Textbox(
                            label="Page Ranges",
                            placeholder="e.g., 1-3, 5, 7-10",
                            value="",
                            info="Leave empty to process all pages"
                        )

                        batch_size = gr.Slider(
                            minimum=1,
                            maximum=20,
                            value=5,
                            step=1,
                            label="Batch Size",
                            info="Pages processed per batch (adjust based on memory)"
                        )

                        export_doctags = gr.Checkbox(
                            label="Use Native Docling (if available)",
                            value=True,
                            info="Try native docling for supported formats (PDF, DOCX, PPTX)"
                        )

                    process_btn = gr.Button(
                        "🔄 Process Document",
                        variant="primary",
                        size="lg"
                    )

                with gr.Column(scale=2):
                    # Output displays
                    with gr.Tabs():
                        with gr.TabItem("📝 Processed Content"):
                            output_text = gr.Textbox(
                                label="Extracted Content (Markdown)",
                                lines=20,
                                max_lines=30,
                                elem_classes=["output-markdown"]
                            )

                        with gr.TabItem("📊 Processing Logs"):
                            logs_output = gr.Textbox(
                                label="Processing Logs",
                                lines=15,
                                max_lines=20,
                                elem_classes=["log-output"]
                            )

            # Download section
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 📥 Downloads")
                    download_md = gr.File(
                        label="Download Markdown",
                        visible=True
                    )
                    download_dt = gr.File(
                        label="Download Structured Output",
                        visible=True
                    )

            # Information section
            with gr.Accordion("ℹ️ About DocTags", open=False):
                gr.Markdown(
                    """
                    ### What are DocTags?
                    
                    DocTags is a semantic markup format designed by IBM specifically for LLMs to understand document structure:
                    
                    - **🏷️ Semantic Tags**: Elements like `<title>`, `<table>`, `<list>`, `<figure>`, etc.
                    - **📍 Location Info**: Preserves spatial relationships and page positions
                    - **🔗 Relationships**: Maintains connections between captions and figures, headers and content
                    - **📊 Table Structure**: Uses OTSL (Optimized Table-Structure Language) notation
                    - **🧩 Nested Structure**: Preserves document hierarchy and relationships
                    
                    ### Benefits over Traditional OCR:
                    
                    1. **Structure-Aware**: Understands document layout, not just text
                    2. **LLM-Optimized**: Designed for efficient tokenization and understanding
                    3. **Lossless**: Preserves all document information and relationships
                    4. **Standardized**: Consistent format across different document types
                    
                    ### Processing Pipeline:
                    
                    1. **SmolDocling Vision Model** → Generates DocTags from document images
                    2. **Docling Parser** → Converts DocTags to structured DoclingDocument
                    3. **Export Formats** → Markdown, HTML, JSON, or raw DocTags
                    """
                )

            # Examples section
            with gr.Accordion("📚 Examples", open=False):
                gr.Examples(
                    examples=[
                        ["Process first 5 pages", "1-5", 5, True],
                        ["Process entire document", "", 10, True],
                        ["Extract without DocTags export", "", 5, False],
                    ],
                    inputs=[page_ranges, page_ranges,
                            batch_size, export_doctags],
                )

            # Event handlers
            process_btn.click(
                fn=self.process_document,
                inputs=[
                    file_input,
                    page_ranges,
                    batch_size,
                    export_doctags
                ],
                outputs=[
                    output_text,
                    logs_output,
                    download_md,
                    download_dt
                ],
                show_progress=True
            )

            # Footer
            gr.Markdown(
                """
                ---
                <div style='text-align: center; color: #666; font-size: 0.9em;'>
                    Powered by <b>SmolDocling-256M-preview</b> and <b>IBM Docling</b> | 
                    DocTags format for semantic document understanding
                </div>
                """
            )

        return app


def main():
    ui = DocTagsDocumentUI()
    app = ui.create_interface()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=True,
        show_error=True
    )


if __name__ == "__main__":
    main()
