from pathlib import Path
import re

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
}


def clean_text(text: str) -> str:
    """
    Clean extracted document text while preserving sentence structure.
    """

    if not text:
        return ""

    text = text.replace("\x00", " ")

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces around newlines.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_text(file_path: str) -> str:
    path = Path(file_path)

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            "Supported types: PDF, DOCX, TXT."
        )

    if extension == ".pdf":
        return extract_pdf(path)

    if extension == ".docx":
        return extract_docx(path)

    if extension == ".txt":
        return extract_txt(path)

    raise ValueError("Unable to process document.")


def extract_pdf(path: Path) -> str:
    """
    Extract text from every PDF page while preserving
    page boundaries.
    """

    reader = PdfReader(str(path))

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        text = clean_text(text)

        if text:
            pages.append(
                f"[PAGE {page_number}]\n{text}"
            )

    return "\n\n".join(pages).strip()


def extract_docx(path: Path) -> str:
    """
    Extract DOCX paragraphs and headings.
    """

    document = Document(str(path))

    blocks = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if not text:
            continue

        style_name = ""

        if paragraph.style:
            style_name = paragraph.style.name or ""

        if "heading" in style_name.lower():
            blocks.append(
                f"[HEADING] {text}"
            )
        else:
            blocks.append(text)

    return clean_text(
        "\n\n".join(blocks)
    )


def extract_txt(path: Path) -> str:
    """
    Read UTF-8 text while tolerating malformed characters.
    """

    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    return clean_text(text)
