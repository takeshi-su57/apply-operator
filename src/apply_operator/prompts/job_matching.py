"""Prompts for job fit analysis."""

ANALYZE_FIT = """Analyze how well this candidate matches the job posting.

## Candidate Profile
Name: {name}
Skills: {skills}
Experience Summary: {experience}

## Job Posting
Title: {job_title}
Company: {company}
Description: {job_description}

## Instructions
Rate the fit on a scale of 0.0 to 1.0 where:
- 0.0-0.3: Poor fit (missing most requirements)
- 0.4-0.5: Partial fit (some relevant skills)
- 0.6-0.7: Good fit (most requirements met)
- 0.8-1.0: Excellent fit (strong match)

Return a JSON object with:
- score: float between 0.0 and 1.0
- reasoning: brief explanation (1-2 sentences)

Return ONLY valid JSON, no other text."""

EXTRACT_JOBS = """Extract job listings from the following web page text.

## Page Text
{page_text}

## Source URL
{url}

## Instructions
Identify every distinct job listing visible on the page. For each job, extract:
- title: job title
- company: company name (if visible)
- description: brief description or summary (first 200 characters)
- location: job location (if visible)
- apply_url: direct link to apply or view the job (if visible, otherwise use the source URL)

Return a JSON array of objects. If no job listings are found, return an empty array [].

Return ONLY valid JSON, no other text."""
