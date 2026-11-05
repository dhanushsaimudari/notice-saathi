import hashlib
import uuid
from pathlib import Path
from fastapi import HTTPException, status
from backend.config import settings

MAGIC_SIGNATURES = {
    "application/pdf": [b"%PDF-"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
}

def validate_upload_bytes(content: bytes, declared_filename: str, declared_media_type: str | None = None) -> dict:
    # 1. Size check
    file_size = len(content)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_FILE",
                "message": "Uploaded file is empty.",
                "recoverable": True
            }
        )
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB.",
                "recoverable": True
            }
        )
        
    # 2. Extension validation
    ext = Path(declared_filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"Allowed extensions are {', '.join(settings.ALLOWED_EXTENSIONS)}. Received: {ext}",
                "recoverable": True
            }
        )
        
    # 3. Magic signature verification
    matched_type = None
    for mime_type, signatures in MAGIC_SIGNATURES.items():
        for sig in signatures:
            if content.startswith(sig):
                matched_type = mime_type
                break
        if matched_type:
            break
            
    if not matched_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_SIGNATURE",
                "message": "The file signature does not match allowed types (PDF, JPEG, PNG). File may be corrupted or disguised.",
                "recoverable": True
            }
        )
        
    # 4. Generate safe unique internal storage key (no client path traversal possible)
    random_id = str(uuid.uuid4())
    safe_storage_key = f"{random_id}{ext}"
    
    # 5. Compute SHA-256 Checksum
    checksum = hashlib.sha256(content).hexdigest()
    
    return {
        "verified_media_type": matched_type,
        "extension": ext,
        "storage_key": safe_storage_key,
        "checksum": checksum,
        "file_size": file_size
    }

