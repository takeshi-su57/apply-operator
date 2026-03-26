"""Tests for PDF parsing utilities."""

from apply_operator.state import ResumeData


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
