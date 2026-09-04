"""
run_pipeline.py — Main orchestrator for the Auto Applier pipeline.

Execution order per job URL:
  1. Check deduplication (skip if already processed)
  2. Scrape job listing (Playwright + BeautifulSoup)
  3. Tailor resume (Gemini API)
  4. Build PDF (ReportLab)
  5. Send WhatsApp notification (Twilio)
  6. Mark URL as processed (SQLite)

Usage:
  python run_pipeline.py              # Full pipeline run
  python run_pipeline.py --dry-run   # Skips API calls, uses mock data
  python run_pipeline.py --list      # Lists all processed jobs
  python run_pipeline.py --reset URL # Resets a URL so it re-processes
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Load .env before importing modules that need env vars
from dotenv import load_dotenv
load_dotenv()

import config
from modules import scraper, tailor, pdf_builder, notifier, state_manager

# ─────────────────────────────────────────────
#   Logging Setup
# ─────────────────────────────────────────────
def _setup_logging(dry_run: bool = False) -> None:
    log_level = logging.DEBUG if dry_run else logging.INFO
    log_file  = config.LOG_DIR / "execution.log"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ]

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


logger = logging.getLogger("pipeline")


# ─────────────────────────────────────────────
#   Per-Job Processing
# ─────────────────────────────────────────────
def process_job(url: str, base_resume: str, dry_run: bool = False) -> bool:
    """
    Runs the full pipeline for a single job URL.

    Returns True on success, False if an error occurred (pipeline continues).
    """
    logger.info(f"{'─' * 60}")
    logger.info(f"Processing: {url}")

    # 1. Deduplication check
    if not dry_run and state_manager.is_processed(url):
        logger.info("⏭  Already processed — skipping.")
        return True

    # 2. Scrape
    job_data = scraper.scrape_job_listing(url)
    if job_data is None:
        logger.error("❌ Scraping failed — skipping this URL.")
        return False

    logger.info(f"✅ Scraped: '{job_data['title']}' at '{job_data['company']}'")

    # 3. Tailor resume
    try:
        tailored_text = tailor.tailor_resume(job_data, base_resume, dry_run=dry_run)
    except Exception as exc:
        logger.error(f"❌ Tailoring failed: {exc}")
        return False

    logger.info("✅ Resume tailored by Gemini.")

    # 4. Build PDF
    try:
        pdf_path = pdf_builder.build_pdf(tailored_text, job_data, dry_run=dry_run)
    except Exception as exc:
        logger.error(f"❌ PDF generation failed: {exc}")
        return False

    logger.info(f"✅ PDF saved: {pdf_path}")

    # 5. Send WhatsApp notification
    notifier.send_whatsapp_alert(pdf_path, job_data, dry_run=dry_run)

    # 6. Mark as processed
    if not dry_run:
        state_manager.mark_processed(url, job_data, pdf_path)

    logger.info(f"🎉 Done: {job_data['title']} @ {job_data['company']}")
    return True


# ─────────────────────────────────────────────
#   Main Pipeline Run
# ─────────────────────────────────────────────
def run_pipeline(dry_run: bool = False) -> None:
    """Runs the full pipeline over all configured JOB_URLS."""
    run_start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Auto Applier Pipeline — {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # Initialize the state database
    state_manager.initialize_db()

    # Load master resume
    resume_path = config.RESUME_PATH
    if not resume_path.exists():
        logger.error(f"Master resume not found at: {resume_path}")
        logger.error("Please create master_resume.md in the project root.")
        sys.exit(1)

    base_resume = resume_path.read_text(encoding="utf-8")
    logger.info(f"Loaded master resume: {resume_path.name} ({len(base_resume)} chars)")

    # Check for configured URLs
    if not config.JOB_URLS:
        logger.warning("No job URLs configured. Add URLs to JOB_URLS in config.py.")
        return

    logger.info(f"Jobs to process: {len(config.JOB_URLS)}")

    # Process each URL
    results = {"success": 0, "skipped": 0, "failed": 0}
    for url in config.JOB_URLS:
        success = process_job(url.strip(), base_resume, dry_run=dry_run)
        if success:
            results["success"] += 1
        else:
            results["failed"] += 1

    # Summary
    elapsed = (datetime.now() - run_start).total_seconds()
    logger.info("=" * 60)
    logger.info(
        f"Pipeline complete in {elapsed:.1f}s — "
        f"✅ {results['success']} succeeded  "
        f"❌ {results['failed']} failed"
    )
    logger.info("=" * 60)


# ─────────────────────────────────────────────
#   CLI Entry Point
# ─────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto Applier — Automated Resume Tailoring Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                   Run the full pipeline
  python run_pipeline.py --dry-run         Test without API calls
  python run_pipeline.py --list            Show all processed jobs
  python run_pipeline.py --reset URL       Re-process a specific URL
        """
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run pipeline without making API calls (uses mock data)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all processed job URLs and exit"
    )
    parser.add_argument(
        "--reset", metavar="URL",
        help="Remove a URL from the processed set so it re-runs next time"
    )

    args = parser.parse_args()
    _setup_logging(dry_run=args.dry_run)

    if args.list:
        state_manager.initialize_db()
        jobs = state_manager.list_processed_jobs()
        if not jobs:
            print("No processed jobs found.")
        else:
            print(f"\n{'─'*80}")
            print(f"{'#':<4} {'Title':<35} {'Company':<25} {'Processed At'}")
            print(f"{'─'*80}")
            for i, job in enumerate(jobs, 1):
                print(f"{i:<4} {job['title'][:34]:<35} {job['company'][:24]:<25} {job['processed_at']}")
            print(f"{'─'*80}")
            print(f"Total: {len(jobs)} processed jobs\n")
        return

    if args.reset:
        state_manager.initialize_db()
        state_manager.reset_url(args.reset)
        return

    run_pipeline(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
