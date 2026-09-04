"""
config.py — Central configuration for the Auto Applier pipeline.

Edit this file to:
  - Add/remove target job URLs
  - Configure board-specific CSS selectors
  - Adjust scheduling and output settings
"""

import os
from pathlib import Path

# ─────────────────────────────────────────────
#   Directory Paths
# ─────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.resolve()
OUTPUT_DIR  = BASE_DIR / "output"
LOG_DIR     = BASE_DIR / "logs"
RESUME_PATH = BASE_DIR / "master_resume.md"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
#   MongoDB
# ─────────────────────────────────────────────
# Override via MONGODB_URI / MONGODB_DB_NAME in .env
MONGODB_URI     = os.environ.get("MONGODB_URI",     "mongodb://localhost:27017")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "auto_applier")
MONGODB_COLLECTION = "processed_jobs"

# ─────────────────────────────────────────────
#   Target Job URLs
#   Add the full URLs of job postings you want
#   the pipeline to process each run.
# ─────────────────────────────────────────────
JOB_URLS: list[str] = [
    # Example Greenhouse posting:
    # "https://boards.greenhouse.io/company/jobs/1234567",

    # Example Lever posting:
    # "https://jobs.lever.co/company/job-id",

    # Example Indeed posting:
    # "https://www.indeed.com/viewjob?jk=JOBID",

    # Example LinkedIn posting:
    # "https://www.linkedin.com/jobs/view/JOB_ID",

    # ← Add your target job URLs here
]

# ─────────────────────────────────────────────
#   Board-Specific CSS Selectors
#   Keyed by hostname fragment.
#   Each entry must have: title, company, description
# ─────────────────────────────────────────────
BOARD_SELECTORS: dict[str, dict[str, str]] = {
    "greenhouse.io": {
        "title":       "h1.app-title",
        "company":     "h2.company-name",
        "description": "#content",
    },
    "lever.co": {
        "title":       ".posting-headline h2",
        "company":     ".main-header-text .posting-headline",
        "description": ".posting-requirements",
    },
    "indeed.com": {
        "title":       '[data-testid="jobsearch-JobInfoHeader-title"]',
        "company":     '[data-testid="inlineHeader-companyName"]',
        "description": '#jobDescriptionText',
    },
    "linkedin.com": {
        "title":       "h1.top-card-layout__title",
        "company":     "a.topcard__org-name-link",
        "description": ".description__text",
    },
    # Generic fallback — adjust if your target board isn't listed
    "default": {
        "title":       ".job-title",
        "company":     ".company-name",
        "description": ".job-description",
    },
}

# ─────────────────────────────────────────────
#   Gemini Model Configuration
# ─────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"

# ─────────────────────────────────────────────
#   Playwright Settings
# ─────────────────────────────────────────────
PLAYWRIGHT_TIMEOUT_MS = 30_000   # Max page load wait
PLAYWRIGHT_HEADLESS   = True

# ─────────────────────────────────────────────
#   Scheduling
# ─────────────────────────────────────────────
SCHEDULE_INTERVAL_MINUTES = 30
