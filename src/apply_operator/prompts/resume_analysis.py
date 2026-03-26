"""Prompts for resume parsing and analysis."""

PARSE_RESUME = """Extract structured data from the following resume text.

Return a JSON object with these fields:
- name: full name
- email: email address
- phone: phone number
- skills: list of ALL technical and professional skills mentioned
- experience: list of ALL positions, each with {{title, company, duration, description}}
- education: list of ALL entries, each with {{degree, institution, year}}
- summary: 2-3 sentence professional summary

If a field is not present in the resume, use null for that field.

Resume text:
{resume_text}

Return ONLY valid JSON, no other text."""
