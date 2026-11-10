import os
from pathlib import Path
from fastapi import HTTPException
from backend.config import settings

class StorageService:
    def __init__(self, base_dir: str = settings.STORAGE_LOCAL_DIR):
        self.base_dir = Path(base_dir).resolve()
        self.originals_dir = (self.base_dir / "originals").resolve()
        self.pages_dir = (self.base_dir / "pages").resolve()
        self.audio_dir = (self.base_dir / "audio").resolve()
        
        self.originals_dir.mkdir(parents=True, exist_ok=True)
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
    def _safe_resolve(self, parent: Path, filename: str) -> Path:
        resolved = (parent / filename).resolve()
        parent_resolved = parent.resolve()
        if not (resolved == parent_resolved or resolved.is_relative_to(parent_resolved)):
            raise HTTPException(status_code=400, detail="Invalid storage path detected.")
        return resolved

    def save_original(self, storage_key: str, content: bytes) -> str:
        dest = self._safe_resolve(self.originals_dir, storage_key)
        dest.write_bytes(content)
        return str(dest)

    def read_original(self, storage_key: str) -> bytes:
        dest = self._safe_resolve(self.originals_dir, storage_key)
        if not dest.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")
        return dest.read_bytes()

    def save_page_image(self, page_image_key: str, content: bytes) -> str:
        dest = self._safe_resolve(self.pages_dir, page_image_key)
        dest.write_bytes(content)
        return str(dest)

    def read_page_image(self, page_image_key: str) -> bytes:
        dest = self._safe_resolve(self.pages_dir, page_image_key)
        if not dest.exists():
            raise FileNotFoundError(f"Page image not found: {page_image_key}")
        return dest.read_bytes()

    def save_audio(self, audio_key: str, content: bytes) -> str:
        dest = self._safe_resolve(self.audio_dir, audio_key)
        dest.write_bytes(content)
        return str(dest)

    def read_audio(self, audio_key: str) -> bytes:
        dest = self._safe_resolve(self.audio_dir, audio_key)
        if not dest.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_key}")
        return dest.read_bytes()

    def delete_document_assets(self, storage_key: str, page_keys: list[str] = None, audio_keys: list[str] = None):
        failed_files = []
        # 1. Original
        try:
            dest = self._safe_resolve(self.originals_dir, storage_key)
            if dest.exists():
                dest.unlink()
        except Exception as e:
            failed_files.append((storage_key, str(e)))

        # 2. Pages
        if page_keys:
            for pk in page_keys:
                try:
                    p = self._safe_resolve(self.pages_dir, pk)
                    if p.exists():
                        p.unlink()
                except Exception as e:
                    failed_files.append((pk, str(e)))

        # 3. Audio
        if audio_keys:
            for ak in audio_keys:
                try:
                    a = self._safe_resolve(self.audio_dir, ak)
                    if a.exists():
                        a.unlink()
                except Exception as e:
                    failed_files.append((ak, str(e)))

        if failed_files:
            raise IOError(f"Failed to delete {len(failed_files)} asset file(s): {[f[0] for f in failed_files]}")

storage_service = StorageService()

