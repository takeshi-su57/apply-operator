"""Tests for PDF parsing utilities."""

from pathlib import Path

import pytest

from apply_operator.state import ResumeData
from apply_operator.tools.pdf_parser import extract_text


class TestResumeData:
    """Tests for the ResumeData model."""

    def test_default_values(self) -> None:
        """ResumeData should have sensible defaults."""
        data = ResumeData()
        assert data.name == ""
        assert data.email == ""
        assert data.skills == []
        assert data.experience == []

    def test_from_dict(self) -> None:
        """ResumeData should be constructable from a dict."""
        data = ResumeData(
            name="Jane Doe",
            email="jane@example.com",
            skills=["Python", "Go"],
        )
        assert data.name == "Jane Doe"
        assert len(data.skills) == 2


class TestExtractText:
    """Tests for the extract_text function."""

    def test_extracts_text_from_valid_pdf(self, sample_pdf: Path) -> None:
        """extract_text returns text content from a valid PDF."""
        text = extract_text(str(sample_pdf))
        assert "John Doe" in text
        assert "john@example.com" in text
        assert "Python Developer" in text

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        """extract_text raises FileNotFoundError for a nonexistent path."""
        with pytest.raises(FileNotFoundError):
            extract_text(str(tmp_path / "nonexistent.pdf"))

    def test_returns_empty_for_empty_pdf(self, empty_pdf: Path) -> None:
        """extract_text returns empty string for a PDF with no text."""
        text = extract_text(str(empty_pdf))
        assert text.strip() == ""
