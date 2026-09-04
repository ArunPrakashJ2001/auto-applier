"""
modules/state_manager.py — MongoDB-backed job deduplication tracker.

Tracks which job URLs have already been processed to prevent duplicate
resume generation across pipeline runs.

Collection: auto_applier.processed_jobs
Document schema:
  {
    "_id":          ObjectId,
    "url":          str,        ← unique index
    "title":        str,
    "company":      str,
    "pdf_path":     str,
    "processed_at": datetime
  }
"""

import logging
import os
from datetime import datetime, timezone

from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, ConnectionFailure, ServerSelectionTimeoutError

import config

logger = logging.getLogger(__name__)

_client: MongoClient | None = None


def _get_collection() -> Collection:
    """
    Returns the MongoDB collection, creating the client and index on first call.
    Reads MONGODB_URI / MONGODB_DB_NAME from config (which reads from env).
    """
    global _client
    if _client is None:
        uri = config.MONGODB_URI
        logger.debug(f"Connecting to MongoDB: {uri}")
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)

    db = _client[config.MONGODB_DB_NAME]
    collection = db[config.MONGODB_COLLECTION]
    return collection


def initialize_db() -> None:
    """
    Ensures the collection and unique index on 'url' exist.
    Safe to call multiple times (idempotent).
    """
    try:
        col = _get_collection()
        col.create_index([("url", ASCENDING)], unique=True, name="url_unique")
        logger.debug(
            f"MongoDB ready — "
            f"{config.MONGODB_DB_NAME}.{config.MONGODB_COLLECTION}"
        )
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        logger.error(f"Cannot connect to MongoDB at {config.MONGODB_URI}: {exc}")
        raise


def is_processed(url: str) -> bool:
    """
    Returns True if the given job URL has already been processed.
    """
    try:
        col = _get_collection()
        return col.find_one({"url": url}, {"_id": 1}) is not None
    except Exception as exc:
        logger.error(f"MongoDB read error in is_processed: {exc}")
        return False


def mark_processed(url: str, job_data: dict, pdf_path: str) -> None:
    """
    Records a processed job URL in MongoDB.

    Args:
        url:      The job posting URL
        job_data: Dict with keys: title, company
        pdf_path: Absolute path to the generated PDF
    """
    doc = {
        "url":          url,
        "title":        job_data.get("title", ""),
        "company":      job_data.get("company", ""),
        "pdf_path":     pdf_path,
        "processed_at": datetime.now(timezone.utc),
    }
    try:
        col = _get_collection()
        col.insert_one(doc)
        logger.info(f"Marked as processed in MongoDB: {url}")
    except DuplicateKeyError:
        logger.warning(f"URL already exists in MongoDB (skipping insert): {url}")
    except Exception as exc:
        logger.error(f"MongoDB write error in mark_processed: {exc}")
        raise


def list_processed_jobs() -> list[dict]:
    """
    Returns all processed jobs as a list of dicts, newest first.
    Useful for auditing what's been done.
    """
    try:
        col = _get_collection()
        docs = col.find({}, {"_id": 0}).sort("processed_at", -1)
        return [
            {**doc, "processed_at": doc["processed_at"].isoformat()}
            if isinstance(doc.get("processed_at"), datetime) else doc
            for doc in docs
        ]
    except Exception as exc:
        logger.error(f"MongoDB read error in list_processed_jobs: {exc}")
        return []


def reset_url(url: str) -> bool:
    """
    Removes a URL from the processed set so it will be re-processed next run.
    Returns True if deleted, False if not found.
    """
    try:
        col = _get_collection()
        result = col.delete_one({"url": url})
        if result.deleted_count:
            logger.info(f"Reset processed state for: {url}")
            return True
        else:
            logger.warning(f"URL not found in MongoDB (nothing to reset): {url}")
            return False
    except Exception as exc:
        logger.error(f"MongoDB delete error in reset_url: {exc}")
        return False
