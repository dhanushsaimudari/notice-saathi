import re
from datetime import datetime

def normalize_whitespace(text: str) -> str:
    """Safely collapses multiple spaces/newlines while preserving sentence boundaries."""
    return re.sub(r'[ \t]+', ' ', text).strip()

def normalize_currency(raw_val: str) -> str:
    """Standardizes Indian currency representations to ₹ format without changing amount."""
    cleaned = raw_val.strip()
    # Match patterns like Rs. 50,000/- or INR 50000 or ₹ 50,000 or plain 6,250.00
    m = re.search(r'(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)(?:\s*/-)?', cleaned, re.IGNORECASE)
    if m:
        num_part = m.group(1).strip()
        if num_part and any(c.isdigit() for c in num_part):
            return f"₹{num_part}"
    return raw_val

def normalize_date(raw_val: str) -> str:
    """Attempts to normalize date string to standard DD/MM/YYYY format."""
    cleaned = raw_val.strip()
    # Format 1: DD/MM/YYYY or DD-MM-YYYY
    m1 = re.search(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b', cleaned)
    if m1:
        d, m, y = m1.groups()
        return f"{int(d):02d}/{int(m):02d}/{y}"
        
    # Format 2: YYYY-MM-DD
    m2 = re.search(r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b', cleaned)
    if m2:
        y, m, d = m2.groups()
        return f"{int(d):02d}/{int(m):02d}/{y}"
        
    # Format 3: DD Month YYYY (e.g., 18 November 2026)
    m3 = re.search(r'\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b', cleaned)
    if m3:
        d, month_name, y = m3.groups()
        try:
            dt = datetime.strptime(f"{d} {month_name[:3]} {y}", "%d %b %Y")
            return dt.strftime("%d/%m/%Y")
        except Exception:
            pass
            
    return raw_val

