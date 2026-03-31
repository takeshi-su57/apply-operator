"""Prompts for application form field mapping."""

MAP_FORM_FIELDS = """You are filling out a job application form.
Position: {job_title} at {company}.
Given the form fields and candidate data, determine the best value for each field.

## Form Fields
Each field has: name, label, field_type, required, and options (for dropdowns).
{form_fields}

## Candidate Data
Name: {name}
Email: {email}
Phone: {phone}
Summary: {summary}
Skills: {skills}
Experience: {experience}
Education: {education}
{cover_letter}

## Instructions
Return a JSON object mapping each field's **name** attribute to the value to fill in.

Rules:
- For text/email/tel/url/textarea fields: return the appropriate string value.
- For select/dropdown fields: return the **exact option text** from the available options list.
- For checkbox/radio fields: return "true" or "false".
- For file upload fields: return "RESUME_FILE".
- If a field asks for a cover letter or "why do you want to work here", use the Cover Letter \
provided above. If no cover letter is provided, compose a brief 2-3 sentence answer.
- If a field asks for information not available in the candidate data, return an empty string.
- Do NOT invent information that is not in the candidate data.

Return ONLY valid JSON, no other text."""

DETECT_FORM_PAGE_TYPE = """Analyze the following page text and determine what type of page it is.

## Page Text
{page_text}

## Instructions
Classify this page as one of:
- "form": The page contains an application form with fillable fields.
- "confirmation": The page confirms a successful submission \
(e.g., "thank you", "application received").
- "error": The page shows an error or failure message.
- "other": The page does not fit any of the above categories.

Return ONLY valid JSON in this format: {{"page_type": "<type>"}}"""
