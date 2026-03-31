"""Tests for job site adapters and registry."""

from unittest.mock import AsyncMock

import pytest

from apply_operator.state import JobListing, ResumeData
from apply_operator.tools.adapters import get_adapter
from apply_operator.tools.adapters.indeed import IndeedAdapter
from apply_operator.tools.adapters.linkedin import LinkedInAdapter


class TestAdapterRegistry:
    """Tests for get_adapter URL matching."""

    def test_returns_linkedin_adapter(self) -> None:
        adapter = get_adapter("https://www.linkedin.com/jobs/search?keywords=python")
        assert isinstance(adapter, LinkedInAdapter)

    def test_returns_indeed_adapter(self) -> None:
        adapter = get_adapter("https://www.indeed.com/jobs?q=python")
        assert isinstance(adapter, IndeedAdapter)

    def test_returns_none_for_unknown_site(self) -> None:
        adapter = get_adapter("https://www.example.com/jobs")
        assert adapter is None

    def test_returns_none_for_generic_url(self) -> None:
        adapter = get_adapter("https://careers.startup.com/apply")
        assert adapter is None

    def test_linkedin_matches_subdomain(self) -> None:
        adapter = get_adapter("https://uk.linkedin.com/jobs/view/123")
        assert isinstance(adapter, LinkedInAdapter)

    def test_indeed_matches_subdomain(self) -> None:
        adapter = get_adapter("https://uk.indeed.com/viewjob?jk=abc")
        assert isinstance(adapter, IndeedAdapter)


class TestLinkedInAdapter:
    """Tests for LinkedIn adapter."""

    def test_matches_linkedin_url(self) -> None:
        adapter = LinkedInAdapter()
        assert adapter.matches("https://www.linkedin.com/jobs") is True
        assert adapter.matches("https://linkedin.com/jobs/view/123") is True
        assert adapter.matches("https://www.indeed.com/jobs") is False

    @pytest.mark.asyncio
    async def test_search_jobs_extracts_cards(self) -> None:
        adapter = LinkedInAdapter()
        mock_page = AsyncMock()

        # Mock job card elements
        mock_card = AsyncMock()
        title_el = AsyncMock()
        title_el.inner_text.return_value = "Python Developer"
        company_el = AsyncMock()
        company_el.inner_text.return_value = "TechCo"
        location_el = AsyncMock()
        location_el.inner_text.return_value = "Remote"
        link_el = AsyncMock()
        link_el.get_attribute.return_value = "/jobs/view/123"

        mock_card.query_selector.side_effect = lambda sel: {
            ".job-card-list__title, .artdeco-entity-lockup__title": title_el,
            ".artdeco-entity-lockup__subtitle, .job-card-container__company-name": company_el,
            ".artdeco-entity-lockup__caption, .job-card-container__metadata-wrapper": location_el,
            "a[href*='/jobs/view/']": link_el,
        }.get(sel)

        mock_page.query_selector_all.return_value = [mock_card]

        jobs = await adapter.search_jobs(mock_page, "https://linkedin.com/jobs")
        assert len(jobs) == 1
        assert jobs[0].title == "Python Developer"
        assert jobs[0].company == "TechCo"

    @pytest.mark.asyncio
    async def test_search_jobs_returns_empty_when_no_cards(self) -> None:
        adapter = LinkedInAdapter()
        mock_page = AsyncMock()
        mock_page.query_selector_all.return_value = []

        jobs = await adapter.search_jobs(mock_page, "https://linkedin.com/jobs")
        assert jobs == []

    @pytest.mark.asyncio
    async def test_fill_application_returns_false_when_no_easy_apply(self) -> None:
        adapter = LinkedInAdapter()
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None

        resume = ResumeData(name="Jane", email="jane@example.com")
        job = JobListing(url="https://linkedin.com/jobs/view/123", title="Dev")

        result = await adapter.fill_application(mock_page, resume, job)
        assert result is False

    @pytest.mark.asyncio
    async def test_find_next_page_clicks_button(self) -> None:
        adapter = LinkedInAdapter()
        mock_page = AsyncMock()
        mock_btn = AsyncMock()
        mock_btn.is_visible.return_value = True
        mock_page.query_selector.return_value = mock_btn

        result = await adapter.find_next_page(mock_page)
        assert result is True
        mock_btn.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_next_page_returns_false_when_no_button(self) -> None:
        adapter = LinkedInAdapter()
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None

        result = await adapter.find_next_page(mock_page)
        assert result is False

    def test_resolve_field_email(self) -> None:
        adapter = LinkedInAdapter()
        resume = ResumeData(name="Jane Doe", email="jane@test.com", phone="555-0100")
        field = {"label": "Email", "name": "email"}
        assert adapter._resolve_field_value(field, resume) == "jane@test.com"

    def test_resolve_field_phone(self) -> None:
        adapter = LinkedInAdapter()
        resume = ResumeData(name="Jane Doe", phone="555-0100")
        field = {"label": "Phone Number", "name": "phone"}
        assert adapter._resolve_field_value(field, resume) == "555-0100"

    def test_resolve_field_name(self) -> None:
        adapter = LinkedInAdapter()
        resume = ResumeData(name="Jane Doe")
        field = {"label": "Full Name", "name": "name"}
        assert adapter._resolve_field_value(field, resume) == "Jane Doe"

    def test_resolve_field_unknown_returns_empty(self) -> None:
        adapter = LinkedInAdapter()
        resume = ResumeData(name="Jane")
        field = {"label": "Favorite Color", "name": "color"}
        assert adapter._resolve_field_value(field, resume) == ""


class TestIndeedAdapter:
    """Tests for Indeed adapter."""

    def test_matches_indeed_url(self) -> None:
        adapter = IndeedAdapter()
        assert adapter.matches("https://www.indeed.com/jobs") is True
        assert adapter.matches("https://indeed.com/viewjob?jk=abc") is True
        assert adapter.matches("https://www.linkedin.com/jobs") is False

    @pytest.mark.asyncio
    async def test_search_jobs_extracts_cards(self) -> None:
        adapter = IndeedAdapter()
        mock_page = AsyncMock()

        mock_card = AsyncMock()
        title_el = AsyncMock()
        title_el.inner_text.return_value = "Backend Developer"
        company_el = AsyncMock()
        company_el.inner_text.return_value = "StartupCo"
        location_el = AsyncMock()
        location_el.inner_text.return_value = "New York"
        link_el = AsyncMock()
        link_el.get_attribute.return_value = "/viewjob?jk=abc123"

        mock_card.query_selector.side_effect = lambda sel: {
            "h2.jobTitle a, .jobTitle span, [data-testid='job-title']": title_el,
            "[data-testid='company-name'], .companyName, .company": company_el,
            "[data-testid='text-location'], .companyLocation, .location": location_el,
            "h2.jobTitle a, a[data-jk], a.jcs-JobTitle": link_el,
        }.get(sel)

        mock_page.query_selector_all.return_value = [mock_card]

        jobs = await adapter.search_jobs(mock_page, "https://indeed.com/jobs")
        assert len(jobs) == 1
        assert jobs[0].title == "Backend Developer"
        assert jobs[0].company == "StartupCo"

    @pytest.mark.asyncio
    async def test_search_jobs_returns_empty_when_no_cards(self) -> None:
        adapter = IndeedAdapter()
        mock_page = AsyncMock()
        mock_page.query_selector_all.return_value = []

        jobs = await adapter.search_jobs(mock_page, "https://indeed.com/jobs")
        assert jobs == []

    @pytest.mark.asyncio
    async def test_fill_application_returns_false_when_no_apply_button(self) -> None:
        adapter = IndeedAdapter()
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None

        resume = ResumeData(name="Jane", email="jane@example.com")
        job = JobListing(url="https://indeed.com/viewjob?jk=abc", title="Dev")

        result = await adapter.fill_application(mock_page, resume, job)
        assert result is False

    @pytest.mark.asyncio
    async def test_find_next_page_returns_false_when_no_button(self) -> None:
        adapter = IndeedAdapter()
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None

        result = await adapter.find_next_page(mock_page)
        assert result is False
