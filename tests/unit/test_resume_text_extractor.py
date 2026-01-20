import pytest

from src.tools.resume_text_extractor import (
    extract_text_from_upload,
    read_upload_bytes,
    ResumeExtractionError,
)

# -------------------------
# extract_text_from_upload
# -------------------------

def test_extract_txt_by_extension():
    data = b"  Hello resume  \n"
    text = extract_text_from_upload("cv.txt", "application/octet-stream", data)
    assert text == "Hello resume"

def test_extract_txt_by_content_type():
    data = b"Text\n"
    text = extract_text_from_upload("whatever.bin", "text/plain", data)
    assert text == "Text"

def test_extract_txt_empty_raises():
    with pytest.raises(ResumeExtractionError, match="Empty text file"):
        extract_text_from_upload("cv.txt", "text/plain", b"   \n\t")

def test_unsupported_type_raises():
    with pytest.raises(ResumeExtractionError, match="Unsupported file type"):
        extract_text_from_upload("cv.png", "image/png", b"abc")


# -------------------------
# read_upload_bytes
# -------------------------

class _FakeUploadFile:
    def __init__(self, data: bytes):
        self._data = data

    async def read(self) -> bytes:
        return self._data


@pytest.mark.anyio
async def test_read_upload_bytes_ok():
    f = _FakeUploadFile(b"abc")
    data = await read_upload_bytes(f, max_bytes=10)
    assert data == b"abc"

@pytest.mark.anyio
async def test_read_upload_bytes_empty_raises():
    f = _FakeUploadFile(b"")
    with pytest.raises(ResumeExtractionError, match="Uploaded file is empty"):
        await read_upload_bytes(f)

@pytest.mark.anyio
async def test_read_upload_bytes_too_large_raises():
    f = _FakeUploadFile(b"a" * 11)
    with pytest.raises(ResumeExtractionError, match="File is too large"):
        await read_upload_bytes(f, max_bytes=10)
