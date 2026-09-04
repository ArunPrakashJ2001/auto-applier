"""
scheduler.py — Python-based scheduler as an alternative to cron.

Runs run_pipeline.py on a configurable interval (default: 30 minutes).
Use this if you prefer not to configure a cron job.

Usage:
  python scheduler.py               # Start scheduler (30-minute interval)
  python scheduler.py --interval 15 # Override interval to 15 minutes
  python scheduler.py --once        # Run once immediately and exit
"""

import argparse
import logging
import sys
import time
import signal
from datetime import datetime

import schedule
from dotenv import load_dotenv

load_dotenv()

import config
from run_pipeline import run_pipeline, _setup_logging

logger = logging.getLogger("scheduler")

_shutdown_flag = False


def _handle_signal(sig, frame):
    """Graceful shutdown on SIGINT / SIGTERM."""
    global _shutdown_flag
    logger.info("Shutdown signal received. Stopping after current run completes...")
    _shutdown_flag = True


def _scheduled_job():
    """Wrapper called by the schedule library on each tick."""
    logger.info(f"⏰ Scheduled run triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        run_pipeline(dry_run=False)
    except Exception as exc:
        logger.error(f"Pipeline error during scheduled run: {exc}", exc_info=True)


def start_scheduler(interval_minutes: int) -> None:
    """
    Starts the scheduler loop.

    Runs the pipeline immediately on start, then every `interval_minutes` minutes.
    """
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("=" * 60)
    logger.info(f"Auto Applier Scheduler started")
    logger.info(f"Run interval: every {interval_minutes} minute(s)")
    logger.info(f"Press Ctrl+C to stop gracefully")
    logger.info("=" * 60)

    # Run immediately on start
    _scheduled_job()

    # Schedule recurring runs
    schedule.every(interval_minutes).minutes.do(_scheduled_job)

    while not _shutdown_flag:
        schedule.run_pending()
        time.sleep(30)  # Check every 30 seconds

    logger.info("Scheduler stopped cleanly.")


def main():
    parser = argparse.ArgumentParser(
        description="Auto Applier Scheduler — keeps the pipeline running on a timer"
    )
    parser.add_argument(
        "--interval", type=int, default=config.SCHEDULE_INTERVAL_MINUTES,
        metavar="MINUTES",
        help=f"Run interval in minutes (default: {config.SCHEDULE_INTERVAL_MINUTES})"
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run once immediately and exit (no scheduling)"
    )
    args = parser.parse_args()

    _setup_logging()

    if args.once:
        logger.info("Running pipeline once...")
        run_pipeline(dry_run=False)
    else:
        start_scheduler(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
