from pathlib import Path

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_text(file_path: str) -> str:
    """
    Extract text from a supported document.

    Supported formats:
    - PDF
    - DOCX
    - TXT
    """

    path = Path(file_path)

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types: PDF, DOCX, TXT."
        )

    if extension == ".pdf":
        return extract_pdf(path)

    if extension == ".docx":
        return extract_docx(path)

    if extension == ".txt":
        return extract_txt(path)

    raise ValueError("Unable to process the document.")


def extract_pdf(path: Path) -> str:
    """Extract text from a PDF."""

    reader = PdfReader(str(path))

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n\n".join(pages).strip()


def extract_docx(path: Path) -> str:
    """Extract text from a DOCX document."""

    document = Document(str(path))

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return "\n\n".join(paragraphs).strip()


def extract_txt(path: Path) -> str:
    """Extract text from a TXT file."""

    return path.read_text(
        encoding="utf-8",
        errors="ignore"
    ).strip()