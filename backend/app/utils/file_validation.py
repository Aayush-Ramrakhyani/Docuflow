"""
File upload validation.

Security rule: the client's declared MIME type and filename are UNTRUSTED. We
identify the real type by inspecting the file's magic bytes, enforce a size cap,
and derive a safe extension ourselves. A mismatched or unknown signature is rejected.
"""

import mimetypes
import struct
from io import BytesIO

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

settings = get_settings()

# Leading byte signatures ("magic numbers") for each allowed type.
_MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "application/pdf": [b"%PDF"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/tiff": [b"II*\x00", b"MM\x00*"],  # Little-endian and big-endian TIFF
    "image/webp": [],                         # WebP detected separately via RIFF header
}

# Whitelist mapping a trusted extension to its MIME — used for the storage key only.
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
    # Match the file header against each known signature
    for mime, signatures in _MAGIC_SIGNATURES.items():
        for sig in signatures:
            if header.startswith(sig):
                return mime

    # WebP has the shape: "RIFF????WEBP" — check both anchor points
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"

    return None  # Unknown/unsupported signature


async def validate_upload(file: UploadFile) -> tuple[bytes, str]:
    """
    Read the full file, validate magic bytes and size.
    Returns (file_bytes, detected_mime_type). Raises HTTPException on any failure.
    """
    # Read one byte past the limit so an oversized file is caught in a single pass
    max_bytes = settings.max_upload_bytes
    content = await file.read(max_bytes + 1)

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    if len(content) < 8:  # Too short to even contain a valid signature
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is too small to be a valid document",
        )

    # The detected type is authoritative — the client's Content-Type is ignored
    detected_mime = _detect_mime_from_bytes(content[:16])
    if not detected_mime:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported file type. Allowed: PDF, JPEG, PNG, TIFF, WebP",
        )

    # Second gate: even a correctly-detected type must be on the allowlist. set() = O(1) lookup.
    if detected_mime not in set(settings.ALLOWED_MIME_TYPES):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{detected_mime}' is not allowed",
        )

    return content, detected_mime


def safe_filename_extension(filename: str) -> str:
    """
    Derive a safe lowercase extension (no dot) from an untrusted filename.
    Falls back to 'bin' for anything unrecognized — never trusts arbitrary input.
    """
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in _EXTENSION_TO_MIME:  # Only accept known-good extensions
            return ext
    return "bin"
