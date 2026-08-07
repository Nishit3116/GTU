"""GTU Academic Engine V2 - Weekly Background Scheduler.

Performs automatic weekly sync of GTU academic catalog every Sunday at 00:00 Midnight.
All user queries during the week are served 100% locally from the JSON database cache.
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .cache.cache_manager import CacheManager
from .config import config

logger = logging.getLogger(__name__)

_SCHEDULER_THREAD: Optional[threading.Thread] = None
_IS_RUNNING = False


def run_weekly_sync() -> bool:
    """Execute full GTU academic data collection and update local JSON database cache."""
    logger.info("[Weekly Sync] Starting weekly GTU Academic Catalog collection...")
    try:
        from .collector.academic_collector import AcademicCollector

        cm = CacheManager()
        collector = AcademicCollector(
            headless=True,
            cache_dir=cm.cache_dir,
        )
        result = collector.run()
        subjects = result.get("subjects", [])

        # Update cache files
        cm.save("last_refresh", datetime.utcnow().isoformat())
        courses = sorted({s.get("course") for s in subjects if s.get("course")})
        cm.save("courses", [{"id": c, "name": c} for c in courses])
        cm.save("subjects", subjects)

        total = len(subjects)
        logger.info("[Weekly Sync] Successfully updated local catalog database (%d subjects).", total)
        print(f"\n[Weekly Sync] Complete! Local database updated with {total} subjects.\n")
        return True
    except Exception as exc:
        logger.exception("[Weekly Sync] Error during weekly GTU data sync: %s", exc)
        print(f"\n[Weekly Sync] WARNING: Weekly GTU sync failed: {exc}\n")
        return False


def _calculate_seconds_until_next_sunday_midnight() -> float:
    """Calculate exact seconds remaining until next Sunday at 00:00:00 UTC."""
    now = datetime.utcnow()
    # Sunday is weekday 6 in Python (Monday=0, ..., Sunday=6)
    days_ahead = 6 - now.weekday()
    if days_ahead == 0 and (now.hour > 0 or now.minute > 0 or now.second > 0):
        days_ahead = 7

    next_sunday = (now + timedelta(days=days_ahead)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    seconds_remaining = (next_sunday - now).total_seconds()
    return max(seconds_remaining, 10.0)


def _scheduler_loop() -> None:
    """Background loop that waits until Sunday midnight, runs sync, and repeats."""
    global _IS_RUNNING
    logger.info("[Scheduler] Weekly GTU background sync scheduler started.")

    while _IS_RUNNING:
        wait_seconds = _calculate_seconds_until_next_sunday_midnight()
        next_run_dt = datetime.utcnow() + timedelta(seconds=wait_seconds)
        logger.info("[Scheduler] Next weekly GTU sync scheduled for %s UTC (in %.1f hours).",
                    next_run_dt.strftime("%Y-%m-%d %H:%M:%S"), wait_seconds / 3600.0)

        # Sleep in short increments so shutdown remains fast
        slept = 0.0
        while slept < wait_seconds and _IS_RUNNING:
            sleep_chunk = min(60.0, wait_seconds - slept)
            time.sleep(sleep_chunk)
            slept += sleep_chunk

        if _IS_RUNNING:
            run_weekly_sync()


def start_background_scheduler() -> None:
    """Start the weekly Sunday background scheduler thread if not already running."""
    global _SCHEDULER_THREAD, _IS_RUNNING
    if _IS_RUNNING and _SCHEDULER_THREAD and _SCHEDULER_THREAD.is_alive():
        logger.info("[Scheduler] Background scheduler is already running.")
        return

    _IS_RUNNING = True
    _SCHEDULER_THREAD = threading.Thread(
        target=_scheduler_loop,
        name="GTU-Weekly-Scheduler",
        daemon=True
    )
    _SCHEDULER_THREAD.start()
    logger.info("[Scheduler] Background Sunday weekly sync thread launched.")


def stop_background_scheduler() -> None:
    """Stop the background scheduler thread cleanly."""
    global _IS_RUNNING
    _IS_RUNNING = False
    logger.info("[Scheduler] Background scheduler stopped.")
