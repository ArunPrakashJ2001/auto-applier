"""
modules/tailor.py — Resume tailoring via Google Gemini API.

Analyzes the job description and adapts the master resume to align with
exact keywords and requirements. Enforces strict factual truthfulness —
no hallucinated experience is ever introduced.
"""

import os
import logging
from google import genai
from google.genai import types

import config

logger = logging.getLogger(__name__)

# Initialize Gemini client once at module load
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Lazily initializes and returns the Gemini client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY environment variable is not set. "
                "Check your .env file."
            )
        _client = genai.Client(api_key=api_key)
    return _client


_SYSTEM_INSTRUCTION = """
You are an expert professional resume writer specializing in ATS (Applicant Tracking System) optimization.

Your task is to tailor the provided master resume for a specific job posting.

STRICT RULES — violating any of these is unacceptable:
1. NEVER invent, fabricate, or hallucinate any experience, skills, technologies, companies, dates, or achievements.
2. Only use information that is explicitly present in the master resume.
3. You MAY reorder bullet points, rename section headers, emphasize existing skills, and adjust phrasing to better match job keywords.
4. You MAY strengthen weak phrasing using synonyms or active voice, but the underlying facts must remain unchanged.
5. Output must be clean, professional Markdown with clear section headers.
6. Preserve all contact information, dates, and company names exactly as provided.
7. Do not add a preamble, explanation, or closing commentary — output only the tailored resume text.
""".strip()


def tailor_resume(job_data: dict, base_resume_text: str, dry_run: bool = False) -> str:
    """
    Calls the Gemini API to tailor the master resume for the given job.

    Args:
        job_data: Dict with keys: title, company, description
        base_resume_text: Raw text of the master resume (Markdown)
        dry_run: If True, skips the API call and returns a placeholder

    Returns:
        Tailored resume as a Markdown string
    """
    if dry_run:
        logger.info("[DRY RUN] Skipping Gemini API call. Returning base resume.")
        return f"[DRY RUN — TAILORED FOR: {job_data['title']} @ {job_data['company']}]\n\n{base_resume_text}"

    prompt = f"""
Tailor the following master resume for the job posting below.

─── JOB DETAILS ───────────────────────────────────────────
Role:    {job_data['title']}
Company: {job_data['company']}

Job Description:
{job_data['description'][:6000]}  ← (truncated to 6000 chars if very long)

─── MASTER RESUME ─────────────────────────────────────────
{base_resume_text}

─── INSTRUCTIONS ──────────────────────────────────────────
Produce the tailored resume now. Output ONLY the resume text in Markdown.
Do not explain your changes. Do not add a cover letter.
""".strip()

    logger.info(f"Calling Gemini ({config.GEMINI_MODEL}) to tailor resume for "
                f"'{job_data['title']}' at '{job_data['company']}'...")

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                temperature=0.3,          # Low temp = factual, consistent output
                max_output_tokens=8192,
            ),
        )
        tailored = response.text.strip()
        logger.info("Gemini tailoring complete.")
        return tailored

    except Exception as exc:
        logger.error(f"Gemini API error: {exc}")
        raise
