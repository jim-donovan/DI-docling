"""
Utility functions for OCR processor
Common utilities to avoid circular imports
"""

def parse_page_ranges(page_ranges_str):
    """
    Parse page ranges string into a list of page numbers.
    
    Args:
        page_ranges_str (str): Page ranges like "1-5, 10, 15-20"
        
    Returns:
        list: List of page numbers (0-indexed for internal use)
        
    Raises:
        ValueError: If page range format is invalid
    """
    if not page_ranges_str or not page_ranges_str.strip():
        return []
    
    pages = set()
    ranges = [r.strip() for r in page_ranges_str.split(',')]
    
    for range_str in ranges:
        if not range_str:
            continue
            
        if '-' in range_str:
            try:
                start, end = range_str.split('-', 1)
                start_page = int(start.strip())
                end_page = int(end.strip())
                
                if start_page < 1 or end_page < 1:
                    raise ValueError("Page numbers must be >= 1")
                if start_page > end_page:
                    raise ValueError(f"Invalid range: {range_str} (start > end)")
                
                # Convert to 0-indexed and add to set
                for page in range(start_page - 1, end_page):
                    pages.add(page)
                    
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"Invalid page range format: {range_str}")
                raise
        else:
            try:
                page_num = int(range_str.strip())
                if page_num < 1:
                    raise ValueError("Page numbers must be >= 1")
                pages.add(page_num - 1)  # Convert to 0-indexed
            except ValueError:
                raise ValueError(f"Invalid page number: {range_str}")
    
    return sorted(list(pages))

def validate_page_ranges(page_ranges_str, total_pages):
    """
    Validate page ranges against document total pages.
    
    Args:
        page_ranges_str (str): Page ranges string
        total_pages (int): Total pages in document
        
    Returns:
        tuple: (is_valid, error_message, parsed_pages)
    """
    try:
        parsed_pages = parse_page_ranges(page_ranges_str)
        
        if not parsed_pages:
            return True, "", []
        
        # Check if any pages exceed document length
        invalid_pages = [p + 1 for p in parsed_pages if p >= total_pages]  # Convert back to 1-indexed for error
        
        if invalid_pages:
            return False, f"Pages {invalid_pages} exceed document length ({total_pages} pages)", []
        
        return True, "", parsed_pages
        
    except ValueError as e:
        return False, str(e), []
