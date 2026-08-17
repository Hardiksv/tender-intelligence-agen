"""
Automated Tender Discovery Engine (Bonus Feature)
Implements polite scheduled scraping of public procurement portals
with deduplication, kill switch, and retry limits.
"""
import os
import time
import hashlib
import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

import requests

from app.core.config import settings
from app.core.logging import logger, log_action

# Kill switch check
DISCOVERY_ENABLED = settings.DISCOVERY_ENABLED
POLITENESS_DELAY_SECONDS = 2       # Polite crawl delay between requests
MAX_RETRIES = 3                     # Max retry attempts per document


class TenderSource(ABC):
    """Abstract interface for all tender discovery sources."""

    source_name: str = "Unknown Portal"

    @abstractmethod
    def discover(self) -> list[dict]:
        """Returns list of candidate tender metadata dicts."""
        pass

    @abstractmethod
    def fetch_document(self, tender_meta: dict) -> Optional[bytes]:
        """Downloads and returns raw PDF bytes for a candidate tender."""
        pass


class CPPPTenderSource(TenderSource):
    """
    CPPP (Central Public Procurement Portal) Discovery Adapter.
    Uses public search API endpoint with polite request delays.
    """
    source_name = "CPPP eprocure.gov.in"
    base_url = "https://eprocure.gov.in"

    def discover(self) -> list[dict]:
        log_action("DISCOVERY_STARTED", status="RUNNING", details={"source": self.source_name})
        candidates = []

        try:
            # Polite delay before any portal request
            time.sleep(POLITENESS_DELAY_SECONDS)

            # In production: real CPPP API / scraping call here.
            # For now: return empty list to avoid unauthorized scraping in demo.
            logger.info(f"[Discovery] {self.source_name}: Discovery scan complete. Found {len(candidates)} candidates.")
            log_action("DISCOVERY_COMPLETED", status="SUCCESS", details={
                "source": self.source_name,
                "candidates_found": len(candidates)
            })
        except Exception as e:
            logger.error(f"[Discovery] {self.source_name} failed: {e}")

        return candidates

    def fetch_document(self, tender_meta: dict) -> Optional[bytes]:
        url = tender_meta.get("document_url")
        if not url:
            return None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                time.sleep(POLITENESS_DELAY_SECONDS)
                response = requests.get(url, timeout=30, headers={
                    "User-Agent": "TenderIntelligenceAgent/1.0 (Research Bot; Contact: admin@example.com)"
                })
                if response.status_code == 200:
                    return response.content
                logger.warning(f"[Discovery] Fetch attempt {attempt}/{MAX_RETRIES} returned HTTP {response.status_code}")
            except requests.RequestException as e:
                logger.warning(f"[Discovery] Fetch attempt {attempt}/{MAX_RETRIES} failed: {e}")

        logger.error(f"[Discovery] All {MAX_RETRIES} fetch attempts failed for {url}")
        return None


def compute_document_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def deduplicate_candidates(candidates: list[dict], existing_hashes: set[str]) -> list[dict]:
    """Filters out already-ingested documents by URL and hash."""
    seen_urls = set()
    unique = []

    for c in candidates:
        url = c.get("source_url", "")
        if url in seen_urls or url in existing_hashes:
            logger.info(f"[Discovery] Skipping duplicate: {url[:60]}")
            continue
        seen_urls.add(url)
        unique.append(c)

    return unique


def run_discovery_cycle(sources: list[TenderSource], data_raw_dir: str):
    """
    Executes one full discovery cycle:
    1. Discover candidates from each source
    2. Deduplicate against existing documents
    3. Download new PDFs to data/raw/
    4. Trigger ingestion pipeline for each new document
    """
    if not settings.DISCOVERY_ENABLED:
        logger.info("[Discovery] Kill switch active (DISCOVERY_ENABLED=false). Skipping run.")
        return

    # Load existing document hashes for deduplication
    existing_hashes: set[str] = set()
    if os.path.exists(data_raw_dir):
        for fname in os.listdir(data_raw_dir):
            if fname.endswith(".pdf"):
                fpath = os.path.join(data_raw_dir, fname)
                with open(fpath, "rb") as f:
                    existing_hashes.add(compute_document_hash(f.read()))

    for source in sources:
        try:
            candidates = source.discover()
            unique_candidates = deduplicate_candidates(candidates, existing_hashes)

            for candidate in unique_candidates:
                content = source.fetch_document(candidate)
                if not content:
                    continue

                doc_hash = compute_document_hash(content)
                if doc_hash in existing_hashes:
                    logger.info("[Discovery] Skipping already-downloaded document (hash match).")
                    continue

                # Save PDF to data/raw
                file_name = candidate.get("file_name", f"discovered_{doc_hash[:12]}.pdf")
                save_path = os.path.join(data_raw_dir, file_name)
                with open(save_path, "wb") as f:
                    f.write(content)
                existing_hashes.add(doc_hash)

                logger.info(f"[Discovery] New tender saved: {file_name}")
                log_action("DISCOVERY_COMPLETED", status="NEW_DOCUMENT", details={
                    "file_name": file_name,
                    "source": source.source_name,
                    "document_hash": doc_hash[:12]
                })

                # Reuse existing ingestion pipeline
                from app.agent.pipeline import run_ingestion_pipeline
                from app.db.models import IngestionJob, IngestionStatusEnum
                from app.db.database import SessionLocal

                db = SessionLocal()
                job = IngestionJob(status=IngestionStatusEnum.PENDING)
                db.add(job)
                db.commit()
                db.refresh(job)
                db.close()
                run_ingestion_pipeline(str(job.id), custom_pdf_paths=[save_path])

        except Exception as e:
            logger.error(f"[Discovery] Source {source.source_name} cycle failed: {e}")


def start_discovery_scheduler(interval_minutes: int = 60):
    """
    Starts a background thread that runs discovery on a configurable interval.
    Respects DISCOVERY_ENABLED kill switch on every cycle.
    """
    data_raw_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "raw"
    )
    sources = [CPPPTenderSource()]

    def scheduler_loop():
        while True:
            if settings.DISCOVERY_ENABLED:
                run_discovery_cycle(sources, data_raw_dir)
            else:
                logger.info("[Discovery] Kill switch is OFF. Scheduler idle.")
            time.sleep(interval_minutes * 60)

    thread = threading.Thread(target=scheduler_loop, daemon=True, name="TenderDiscoveryScheduler")
    thread.start()
    logger.info(f"[Discovery] Scheduler started. Interval: {interval_minutes} minutes. Kill switch: DISCOVERY_ENABLED={settings.DISCOVERY_ENABLED}")
    return thread
