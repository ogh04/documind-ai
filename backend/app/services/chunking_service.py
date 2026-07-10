import re
from dataclasses import dataclass
from typing import Optional


DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50


@dataclass
class TextChunk:
    text: str
    page_number: Optional[int]
    chunk_index: int


def split_text_into_words(text: str) -> list[str]:
    return text.split()


def clean_chunk_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_page_number(line: str) -> Optional[int]:
    match = re.match(r"---\s*(?:OCR\s*)?Page\s+(\d+)\s*---", line.strip())

    if match:
        return int(match.group(1))

    return None


def split_extracted_text_by_pages(extracted_text: str) -> list[tuple[Optional[int], str]]:
    pages: list[tuple[Optional[int], str]] = []

    current_page_number: Optional[int] = None
    current_lines: list[str] = []

    for line in extracted_text.splitlines():
        detected_page_number = detect_page_number(line)

        if detected_page_number is not None:
            if current_lines:
                pages.append(
                    (
                        current_page_number,
                        "\n".join(current_lines).strip(),
                    )
                )

            current_page_number = detected_page_number
            current_lines = []
            continue

        current_lines.append(line)

    if current_lines:
        pages.append(
            (
                current_page_number,
                "\n".join(current_lines).strip(),
            )
        )

    return [
        (page_number, page_text)
        for page_number, page_text in pages
        if page_text
    ]


def chunk_text(
    text: str,
    page_number: Optional[int],
    starting_chunk_index: int,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[TextChunk]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    words = split_text_into_words(text)

    chunks: list[TextChunk] = []
    start = 0
    chunk_index = starting_chunk_index

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text_value = clean_chunk_text(" ".join(chunk_words))

        if chunk_text_value:
            chunks.append(
                TextChunk(
                    text=chunk_text_value,
                    page_number=page_number,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

        if end >= len(words):
            break

        start = end - chunk_overlap

    return chunks


def create_chunks_from_extracted_text(
    extracted_text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[TextChunk]:
    pages = split_extracted_text_by_pages(extracted_text)

    all_chunks: list[TextChunk] = []
    next_chunk_index = 0

    for page_number, page_text in pages:
        page_chunks = chunk_text(
            text=page_text,
            page_number=page_number,
            starting_chunk_index=next_chunk_index,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        all_chunks.extend(page_chunks)
        next_chunk_index += len(page_chunks)

    return all_chunks