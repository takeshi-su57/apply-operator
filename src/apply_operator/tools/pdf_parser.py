"""PDF resume parsing using PyMuPDF."""

import fitz  # PyMuPDF


def extract_text(pdf_path: str) -> str:
    """Extract all text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Concatenated text from all pages.
    """
    doc = fitz.open(pdf_path)
    try:
        pages = [page.get_text() for page in doc]
        return "\n".join(pages)
    finally:
        doc.close()
