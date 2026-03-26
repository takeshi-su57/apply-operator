"""Prompts for resume parsing and analysis."""

PARSE_RESUME = """Extract structured data from the following resume text.

Return a JSON object with these fields:
- name: full name
- email: email address
- phone: phone number
- skills: list of technical and professional skills
- experience: list of objects with {title, company, duration, description}
- education: list of objects with {degree, institution, year}
- summary: 2-3 sentence professional summary

Resume text:
{resume_text}

Return ONLY valid JSON, no other text."""
