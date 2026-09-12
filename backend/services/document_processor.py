from pathlib import Path
import re

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Never allow words to become accidentally joined.
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
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

    return extract_txt(path)


def extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")

        if text:
            pages.append(f"[PAGE {page_number}]\n{text}")

    return "\n\n".join(pages).strip()


def extract_docx(path: Path) -> str:
    document = Document(str(path))
    blocks = []

    for paragraph in document.paragraphs:
        text = clean_text(paragraph.text)

        if not text:
            continue

        style_name = paragraph.style.name if paragraph.style else ""

        if "heading" in style_name.lower():
            blocks.append(f"[HEADING] {text}")
        else:
            blocks.append(text)

    return "\n\n".join(blocks).strip()


def extract_txt(path: Path) -> str:
    return clean_text(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    )
