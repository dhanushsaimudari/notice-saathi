import io
import re
import uuid
from typing import List, Dict, Any, Optional
import numpy as np
from PIL import Image

try:
    from rapidocr_onnxruntime import RapidOCR
    _ocr_engine: Optional[RapidOCR] = RapidOCR()
except Exception:
    _ocr_engine = None

class ExtractedBlock:
    def __init__(
        self,
        block_id: str,
        page_index: int,
        text_original: str,
        text_normalized: str,
        bbox: List[float],
        confidence: float = 0.95,
        engine: str = "rapidocr"
    ):
        self.block_id = block_id
        self.page_index = page_index
        self.text_original = text_original
        self.text_normalized = text_normalized
        self.bbox = bbox  # [ymin, xmin, ymax, xmax] normalized 0.0 - 1.0
        self.confidence = round(confidence, 4)
        self.engine = engine

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "page_index": self.page_index,
            "text_original": self.text_original,
            "text_normalized": self.text_normalized,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "engine": self.engine
        }

def get_ocr_engine() -> Optional[Any]:
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        except Exception:
            _ocr_engine = None
    return _ocr_engine

def extract_text_blocks_from_image(image_bytes: bytes, page_index: int = 1) -> List[ExtractedBlock]:
    """
    Executes real OCR on image bytes using RapidOCR ONNX runtime.
    Preserves real page indices, text spans, exact normalized bounding boxes,
    and actual model confidence scores. Never fabricates text.
    """
    engine = get_ocr_engine()
    if engine is None:
        return []

    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = pil_img.size
        if width <= 0 or height <= 0:
            return []

        img_np = np.array(pil_img)
        ocr_result, _ = engine(img_np)
        
        if not ocr_result:
            return []

        blocks: List[ExtractedBlock] = []
        for idx, item in enumerate(ocr_result):
            # item format: [polygon_box, text, confidence]
            # polygon_box: [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
            box, text, conf = item
            if not text or not str(text).strip():
                continue

            xs = [pt[0] for pt in box]
            ys = [pt[1] for pt in box]
            
            xmin = max(0.0, min(xs)) / width
            xmax = min(width, max(xs)) / width
            ymin = max(0.0, min(ys)) / height
            ymax = min(height, max(ys)) / height

            normalized_text = re.sub(r'\s+', ' ', str(text)).strip()
            
            blocks.append(
                ExtractedBlock(
                    block_id=f"tb_{page_index}_{idx+1}_{uuid.uuid4().hex[:6]}",
                    page_index=page_index,
                    text_original=str(text).strip(),
                    text_normalized=normalized_text,
                    bbox=[round(ymin, 4), round(xmin, 4), round(ymax, 4), round(xmax, 4)],
                    confidence=float(conf),
                    engine="rapidocr_onnx"
                )
            )
        return blocks
    except Exception as e:
        # Graceful failure handling without crashing
        return []

def segment_text_into_blocks(raw_text: str, page_index: int) -> List[ExtractedBlock]:
    """
    Splits digital/native PDF page text into logical paragraph/line blocks.
    Uses proportional vertical bounds for native text streams.
    """
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n|\r\n\s*\r\n', raw_text) if p.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in raw_text.splitlines() if line.strip()]
        
    blocks: List[ExtractedBlock] = []
    total = max(len(paragraphs), 1)
    
    for idx, para in enumerate(paragraphs):
        ymin = round(0.08 + (idx / total) * 0.82, 3)
        ymax = round(ymin + min(0.82 / total, 0.15), 3)
        xmin = 0.08
        xmax = 0.92
        
        normalized = re.sub(r'\s+', ' ', para).strip()
        
        blocks.append(
            ExtractedBlock(
                block_id=f"tb_{page_index}_{idx+1}_{uuid.uuid4().hex[:6]}",
                page_index=page_index,
                text_original=para,
                text_normalized=normalized,
                bbox=[ymin, xmin, ymax, xmax],
                confidence=1.0,
                engine="pdf_native"
            )
        )
        
    return blocks
