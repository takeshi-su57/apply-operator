"""PDF resume parsing using PyMuPDF."""

from pathlib import Path

import fitz  # PyMuPDF


def extract_text(pdf_path: str) -> str:
    """Extract all text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Concatenated text from all pages.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        ValueError: If the file is not a valid PDF.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise ValueError(f"Failed to open PDF: {pdf_path}") from exc

    try:
        pages = [page.get_text() for page in doc]
        return "\n".join(pages)
    finally:
        doc.close()
