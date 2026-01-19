import io
from fastapi import UploadFile

# PDF
try:
    from PyPDF2 import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

# DOCX
try:
    from docx import Document
except Exception:  # pragma: no cover
    Document = None


class ResumeExtractionError(Exception):
    pass


def _safe_decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore").strip()


def extract_text_from_upload(filename: str, content_type: str | None, data: bytes) -> str:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()

    # TXT
    if name.endswith(".txt") or "text/plain" in ctype:
        text = _safe_decode_text(data)
        if not text:
            raise ResumeExtractionError("Empty text file.")
        return text

    # PDF
    if name.endswith(".pdf") or "application/pdf" in ctype:
        if PdfReader is None:
            raise ResumeExtractionError("PDF extractor is not available (PyPDF2 missing).")
        try:
            reader = PdfReader(io.BytesIO(data))
            parts: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(page_text)
            text = "\n".join(parts).strip()
        except Exception as e:
            raise ResumeExtractionError(f"Failed to parse PDF: {e}") from e

        if not text:
            raise ResumeExtractionError("No text extracted from PDF (maybe scanned image).")
        return text

    # DOCX
    if name.endswith(".docx") or "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in ctype:
        if Document is None:
            raise ResumeExtractionError("DOCX extractor is not available (python-docx missing).")
        try:
            doc = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs if p.text and p.text.strip()).strip()
        except Exception as e:
            raise ResumeExtractionError(f"Failed to parse DOCX: {e}") from e

        if not text:
            raise ResumeExtractionError("No text extracted from DOCX.")
        return text

    raise ResumeExtractionError("Unsupported file type. Please upload PDF or TXT (DOCX optional).")


async def read_upload_bytes(file: UploadFile, max_bytes: int = 2_000_000) -> bytes:
    data = await file.read()
    if not data:
        raise ResumeExtractionError("Uploaded file is empty.")
    if len(data) > max_bytes:
        raise ResumeExtractionError("File is too large.")
    return data
