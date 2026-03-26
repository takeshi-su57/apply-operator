"""Prompts for application form field mapping."""

MAP_FORM_FIELDS = """You are filling out a job application form. Given the form fields and candidate data, determine the best value for each field.

## Form Fields (label: field_type)
{form_fields}

## Candidate Data
Name: {name}
Email: {email}
Phone: {phone}
Skills: {skills}
Experience: {experience}
Education: {education}

## Instructions
For each form field, return the appropriate value from the candidate data.
If a field asks for information not available in the candidate data, return an empty string.
For dropdown/select fields, choose the closest matching option.

Return a JSON object mapping field labels to values.
Return ONLY valid JSON, no other text."""
