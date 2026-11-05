import io
import re
from PIL import Image, ImageFilter, ImageStat
from typing import Dict, Any, Optional

class ImageQualityResult:
    def __init__(
        self,
        is_readable: bool,
        quality_state: str,
        metrics: Dict[str, Any],
        action_message: str | None = None
    ):
        self.is_readable = is_readable
        self.quality_state = quality_state
        self.metrics = metrics
        self.action_message = action_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_readable": self.is_readable,
            "quality_state": self.quality_state,
            "metrics": self.metrics,
            "action_message": self.action_message
        }

def assess_image_quality(
    image_bytes: bytes,
    extracted_text_sample: Optional[str] = None
) -> ImageQualityResult:
    """
    Evaluates image quality for blur, resolution, glare and edge cropping.
    Combines low-level visual heuristics with actual text extraction signals:
    - Never rejects documents solely on a simplistic blur threshold if readable
      words are successfully deciphered by OCR.
    - If OCR yields 0 readable words due to blur/defocus, marks BLURRED.
    - If extreme aspect ratio indicates a cropped sliver, marks CROPPED_EDGE.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        
        # 1. Resolution Check
        min_dim = min(width, height)
        max_dim = max(width, height)
        is_low_res = (width * height) < (320 * 240)
        
        # 2. Blur / Sharpness Estimation
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        edge_variance = edge_stat.var[0] if edge_stat.var else 0.0
        
        # 3. Glare Check
        left = int(width * 0.2)
        top = int(height * 0.2)
        right = int(width * 0.8)
        bottom = int(height * 0.8)
        center_crop = gray.crop((left, top, right, bottom))
        hist = center_crop.histogram()
        total_pixels = (right - left) * (bottom - top)
        glare_pixels = sum(hist[252:]) if len(hist) >= 256 else 0
        glare_ratio = glare_pixels / total_pixels if total_pixels > 0 else 0.0
        is_high_glare = glare_ratio > 0.88 and edge_variance < 100.0
        
        # 4. Aspect Ratio & Edge Cropping
        aspect_ratio = max_dim / min_dim if min_dim > 0 else 1.0
        is_extreme_aspect = aspect_ratio > 4.5
        
        # 5. Semantic readability check via OCR text sample
        has_readable_words = False
        readable_token_count = 0
        if extracted_text_sample is not None:
            tokens = re.findall(r'[A-Za-z0-9\u0C00-\u0C7F\u0900-\u097F]{3,}', extracted_text_sample)
            readable_token_count = len(tokens)
            has_readable_words = readable_token_count >= 2

        metrics = {
            "width": width,
            "height": height,
            "edge_variance": round(edge_variance, 2),
            "glare_ratio": round(glare_ratio, 3),
            "aspect_ratio": round(aspect_ratio, 2),
            "readable_token_count": readable_token_count,
            "has_readable_words": has_readable_words,
            "is_low_res": is_low_res,
            "is_high_glare": is_high_glare,
            "is_extreme_aspect": is_extreme_aspect
        }
        
        # Hard failure: Resolution is too low to extract anything
        if is_low_res and not has_readable_words:
            return ImageQualityResult(
                is_readable=False,
                quality_state="LOW_RESOLUTION",
                metrics=metrics,
                action_message="The image resolution is too low to read text. Please take a closer photo."
            )
            
        # Hard failure: Extreme aspect ratio sliver / cropped edge
        if is_extreme_aspect:
            return ImageQualityResult(
                is_readable=False,
                quality_state="CROPPED_EDGE",
                metrics=metrics,
                action_message="The document seems cropped or cut off. Please frame the entire page."
            )
            
        # Severe glare washing out page
        if is_high_glare and not has_readable_words:
            return ImageQualityResult(
                is_readable=False,
                quality_state="HIGH_GLARE",
                metrics=metrics,
                action_message="High glare or bright light is reflecting off the page. Please angle the camera away from direct lights."
            )

        # Blur failure: When OCR was run and yielded 0 readable words
        if extracted_text_sample is not None and not has_readable_words:
            return ImageQualityResult(
                is_readable=False,
                quality_state="BLURRED",
                metrics=metrics,
                action_message="The text appears blurry and could not be clearly read. Please hold the camera steady and take a sharper photo."
            )
            
        return ImageQualityResult(
            is_readable=True,
            quality_state="READABLE",
            metrics=metrics,
            action_message=None
        )
        
    except Exception as e:
        return ImageQualityResult(
            is_readable=True,
            quality_state="READABLE",
            metrics={"error": str(e)},
            action_message=None
        )
