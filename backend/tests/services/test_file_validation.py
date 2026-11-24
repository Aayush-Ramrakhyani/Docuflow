"""File validation unit tests."""

import pytest
from fastapi import HTTPException, UploadFile
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

from app.utils.file_validation import validate_upload, safe_filename_extension


def _make_upload(content: bytes, filename: str = "test.pdf") -> UploadFile:
    mock = MagicMock(spec=UploadFile)
    mock.filename = filename
    mock.read = AsyncMock(return_value=content)
    return mock


@pytest.mark.asyncio
async def test_valid_pdf_accepted():
    pdf_header = b"%PDF-1.4" + b"\x00" * 100
    upload = _make_upload(pdf_header, "invoice.pdf")
    content, mime = await validate_upload(upload)
    assert mime == "application/pdf"
    assert len(content) > 0


@pytest.mark.asyncio
async def test_valid_jpeg_accepted():
    jpeg_header = b"\xff\xd8\xff" + b"\x00" * 100
    upload = _make_upload(jpeg_header, "scan.jpg")
    content, mime = await validate_upload(upload)
    assert mime == "image/jpeg"


@pytest.mark.asyncio
async def test_invalid_file_rejected():
    # Pretend to be a PDF but isn't (magic bytes don't match)
    fake_content = b"This is not a valid file at all, definitely not a PDF"
    upload = _make_upload(fake_content, "malicious.pdf")
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(upload)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_oversized_file_rejected():
    # 51 MB of PDF-looking content
    large_content = b"%PDF" + b"\x00" * (51 * 1024 * 1024)
    upload = _make_upload(large_content, "big.pdf")
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(upload)
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_empty_file_rejected():
    upload = _make_upload(b"\x00\x00", "empty.pdf")
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(upload)
    assert exc_info.value.status_code == 422


def test_safe_filename_extension_basic():
    assert safe_filename_extension("document.pdf") == "pdf"
    assert safe_filename_extension("scan.JPEG") == "jpeg"
    assert safe_filename_extension("image.PNG") == "png"


def test_safe_filename_extension_unknown():
    assert safe_filename_extension("script.exe") == "bin"
    assert safe_filename_extension("config.sh") == "bin"
    assert safe_filename_extension("noextension") == "bin"


def test_safe_filename_no_path_traversal():
    # Extensions should not contain path separators
    result = safe_filename_extension("../../etc/passwd")
    assert "/" not in result
    assert "\\" not in result
    assert result == "bin"
