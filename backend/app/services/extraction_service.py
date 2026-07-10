from pathlib import Path

import fitz
import pytesseract
from docx import Document as DocxDocument
from PIL import Image


SUPPORTED_EXTRACTION_TYPES = {
    "pdf",
    "docx",
    "png",
    "jpg",
    "jpeg",
}


OCR_LANGUAGES = "eng+fra+ara"


def extract_text_from_pdf(file_path: str) -> str:
    text_parts: list[str] = []

    with fitz.open(file_path) as pdf_document:
        for page_index, page in enumerate(pdf_document, start=1):
            page_text = page.get_text("text").strip()

            if page_text:
                text_parts.append(
                    f"\n\n--- Page {page_index} ---\n{page_text}"
                )

    return "\n".join(text_parts).strip()


def extract_text_from_scanned_pdf(file_path: str) -> str:
    text_parts: list[str] = []

    with fitz.open(file_path) as pdf_document:
        for page_index, page in enumerate(pdf_document, start=1):
            pixmap = page.get_pixmap(dpi=200)
            image = Image.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples,
            )

            page_text = pytesseract.image_to_string(
                image,
                lang=OCR_LANGUAGES,
            ).strip()

            if page_text:
                text_parts.append(
                    f"\n\n--- OCR Page {page_index} ---\n{page_text}"
                )

    return "\n".join(text_parts).strip()


def extract_text_from_docx(file_path: str) -> str:
    docx_document = DocxDocument(file_path)

    text_parts: list[str] = []

    for paragraph in docx_document.paragraphs:
        paragraph_text = paragraph.text.strip()

        if paragraph_text:
            text_parts.append(paragraph_text)

    return "\n".join(text_parts).strip()


def extract_text_from_image(file_path: str) -> str:
    image = Image.open(file_path)

    text = pytesseract.image_to_string(
        image,
        lang=OCR_LANGUAGES,
    )

    return text.strip()


def extract_text_from_document(
    file_path: str,
    file_type: str,
) -> str:
    normalized_file_type = file_type.lower().strip()

    if normalized_file_type == "pdf":
        pdf_text = extract_text_from_pdf(file_path)

        if pdf_text:
            return pdf_text

        return extract_text_from_scanned_pdf(file_path)

    if normalized_file_type == "docx":
        return extract_text_from_docx(file_path)

    if normalized_file_type in {"png", "jpg", "jpeg"}:
        return extract_text_from_image(file_path)

    raise ValueError(
        f"Unsupported extraction type: {file_type}. "
        f"Supported types: {', '.join(SUPPORTED_EXTRACTION_TYPES)}"
    )


def validate_file_exists(file_path: str) -> None:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {file_path}"
        )