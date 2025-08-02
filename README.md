---
title: DI 3.1.0
emoji: 💻
colorFrom: yellow
colorTo: blue
sdk: gradio
sdk_version: 5.34.0
app_file: app.py
pinned: false
---

SmolDocling-256M-preview reference: https://huggingface.co/ds4sd/SmolDocling-256M-preview

# Current Solution

## 1. **Native Docling Support** (when available)
- For supported formats (PDF, DOCX, PPTX), we use the native docling library
- This provides proper DocTags export and multiple format conversions
- Falls back to SmolDocling if native processing fails

## 2. **Structure-Aware SmolDocling** (main approach)
- Uses SmolDocling with prompts designed to extract document structure
- Identifies elements like:
  - Titles and headings
  - Tables with structure
  - Lists with hierarchy
  - Code blocks
  - Figures and captions
- Outputs structured text that preserves document semantics

## 3. **Dual Output**
- **Markdown**: Human-readable formatted output
- **Structured Text**: Shows document structure with tags like [TITLE], [TABLE], [LIST], etc.

## How to Use

```bash
# Run the simplified DocTags version
python app_doctags.py
```

### In the UI:
1. Upload your PDF
2. Check "Use Native Docling" to try native processing first (recommended)
3. Process the document
4. Download both Markdown and Structured outputs

## Benefits

Even with the simplified approach, you get:
- ✅ **Structure Recognition**: Document elements are identified and tagged
- ✅ **Better Than Plain OCR**: Preserves semantic meaning, not just text
- ✅ **Multiple Outputs**: Markdown for reading, structured for processing
- ✅ **Native Support**: Uses official docling when possible
- ✅ **Fallback**: Always works with SmolDocling even if docling fails

## Future Improvements

As the docling ecosystem evolves:
1. Better integration between SmolDocling-generated DocTags and docling parser
2. Full DocTags round-trip support (generate → parse → convert)
3. More sophisticated structure extraction

## Technical Note

The current implementation:
- Uses `docling.document_converter.DocumentConverter` for native conversion
- Falls back to SmolDocling with structure-aware prompts
- Outputs structured text that can be post-processed into full DocTags

This pragmatic approach gives you most of the benefits of DocTags while working within current library constraints.

