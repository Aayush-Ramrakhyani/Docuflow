"""
File validation utilities.
Validates magic bytes (not client-supplied MIME), enforces size/type limits.
"""

import mimetypes
import struct
from io import BytesIO

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

settings = get_settings()

# Magic byte signatures for allowed file types
_MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "application/pdf": [b"%PDF"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/tiff": [b"II*\x00", b"MM\x00*"],  # Little-endian and big-endian TIFF
    "image/webp": [],  # Checked separately via RIFF header
}

_EXTENSION_TO_MIME = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "webp": "image/webp",
}


def _detect_mime_from_bytes(header: bytes) -> str | None:
    for mime, signatures in _MAGIC_SIGNATURES.items():
        for sig in signatures:
            if header.startswith(sig):
                return mime

    # WebP: RIFF????WEBP
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"

    return None


async def validate_upload(file: UploadFile) -> tuple[bytes, str]:
    """
    Read the full file, validate magic bytes and size.
    Returns (file_bytes, detected_mime_type).
    Raises HTTPException on any validation failure.
    """
    # Read up to max_upload_bytes + 1 to detect oversized files in one pass
    max_bytes = settings.max_upload_bytes
    content = await file.read(max_bytes + 1)

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    if len(content) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is too small to be a valid document",
        )

    detected_mime = _detect_mime_from_bytes(content[:16])
    if not detected_mime:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported file type. Allowed: PDF, JPEG, PNG, TIFF, WebP",
        )

    if detected_mime not in set(settings.ALLOWED_MIME_TYPES):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{detected_mime}' is not allowed",
        )

    return content, detected_mime


def safe_filename_extension(filename: str) -> str:
    """
    Extract and validate file extension.
    Returns a safe lowercase extension (without dot).
    Falls back to 'bin' for unrecognized extensions.
    """
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in _EXTENSION_TO_MIME:
            return ext
    return "bin"
