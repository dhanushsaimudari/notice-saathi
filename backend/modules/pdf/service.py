import io
from typing import List, Dict, Any, Optional
from pypdf import PdfReader

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

class ExtractedPdfPage:
    def __init__(self, page_index: int, text: str, width: int = 600, height: int = 800, is_scanned: bool = False):
        self.page_index = page_index
        self.text = text
        self.width = width
        self.height = height
        self.is_scanned = is_scanned

def extract_pdf_data(pdf_bytes: bytes) -> List[ExtractedPdfPage]:
    """
    Extracts text and page metadata natively from PDF bytes.
    Detects whether pages have digital native text or are scanned images.
    """
    pages: List[ExtractedPdfPage] = []
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            width = 600
            height = 800
            if page.mediabox:
                try:
                    width = int(float(page.mediabox.width))
                    height = int(float(page.mediabox.height))
                except Exception:
                    pass
            
            clean_text = page_text.strip()
            # If extracted text has fewer than 15 characters, page is likely a scan
            is_scanned = len(clean_text) < 15
            
            pages.append(
                ExtractedPdfPage(
                    page_index=idx + 1,
                    text=clean_text,
                    width=width,
                    height=height,
                    is_scanned=is_scanned
                )
            )
    except Exception:
        # Graceful fallback: return single page entry marked as scanned for OCR
        pages.append(
            ExtractedPdfPage(
                page_index=1,
                text="",
                width=600,
                height=800,
                is_scanned=True
            )
        )
        
    return pages

def render_pdf_page_to_png(pdf_bytes: bytes, page_index: int = 1, dpi: int = 150) -> Optional[bytes]:
    """
    Renders a specific PDF page to PNG image bytes for OCR processing.
    Uses PyMuPDF for reliable high-resolution rasterization.
    """
    if pymupdf is None:
        return None
        
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        if page_index < 1 or page_index > len(doc):
            return None
        page = doc.load_page(page_index - 1)
        pix = page.get_pixmap(dpi=dpi)
        png_bytes = pix.tobytes("png")
        doc.close()
        return png_bytes
    except Exception:
        return None
