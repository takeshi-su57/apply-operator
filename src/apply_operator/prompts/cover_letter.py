"""Prompts for cover letter generation."""

GENERATE_COVER_LETTER = """Write a professional cover letter for this job application.

## Candidate Profile
Name: {name}
Summary: {summary}
Skills: {skills}
Experience: {experience}

## Job Posting
Title: {job_title}
Company: {company}
Description: {job_description}

## Instructions
Write a concise, professional cover letter (2-3 paragraphs) that:
- Opens with enthusiasm for the specific role and company
- Highlights the candidate's most relevant skills and experience for this position
- Closes with a call to action

Do NOT invent qualifications or experience not present in the candidate data.
Use a professional but warm tone.

Return a JSON object with:
- cover_letter: the full cover letter text as a single string

Return ONLY valid JSON, no other text."""
