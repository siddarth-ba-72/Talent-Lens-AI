from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi import UploadFile
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


async def extract_text_from_upload(file: UploadFile) -> str:
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Allowed: .txt, .pdf, .docx")

    payload = await file.read()
    if not payload:
        raise ValueError("Uploaded file is empty")

    if extension == ".txt":
        text = payload.decode("utf-8", errors="ignore")
    elif extension == ".pdf":
        text = _extract_pdf(payload)
    else:
        text = _extract_docx(payload)

    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        raise ValueError("Could not extract readable text from the uploaded file")
    return normalized


def _extract_pdf(payload: bytes) -> str:
    reader = PdfReader(BytesIO(payload))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_docx(payload: bytes) -> str:
    document = Document(BytesIO(payload))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    return "\n".join(paragraphs)
