"""Playwright subprocess isolation layer for GTU Academic Engine V2.

Runs ASPXProvider inside a dedicated child process (spawn context) so that
sync_playwright() is NEVER called inside the parent web-server process.

Why multiprocessing.Process instead of threading or ThreadPoolExecutor:
  - Render (Linux) injects an asyncio event loop into the process at startup.
  - Playwright's sync API calls asyncio.get_running_loop() internally and
    raises "Sync API inside the asyncio loop" if it finds one.
  - A threading.Thread shares the parent's event loop state.
  - A multiprocessing.Process('spawn') starts a FRESH Python interpreter:
    no asyncio, no event loop, no inherited state — sync_playwright() works.

Communication protocol:
  - Parent → Child: (task_id, method_name, args, kwargs) tuple via Queue
  - Child → Parent: (task_id, success: bool, result_or_error) tuple via Queue
  - Shutdown: parent puts None into the request queue
"""

from __future__ import annotations

import logging
import multiprocessing
import multiprocessing.queues
import os
from typing import Any

logger = logging.getLogger(__name__)

# Always use 'spawn' so the child gets a clean Python interpreter.
# fork would inherit the parent's asyncio event loop.
_MP_CTX = multiprocessing.get_context("spawn")


# ── Child process entry point ─────────────────────────────────────────────────

def _worker_main(
    req_q: "multiprocessing.queues.Queue",
    res_q: "multiprocessing.queues.Queue",
) -> None:
    """Runs inside the spawned child process.

    Has its own Python interpreter — no asyncio event loop is present.
    Loads ASPXProvider lazily on the first request and keeps it alive.
    Resets the provider if any method raises an exception.
    """
    # Configure logging in the child (it doesn't inherit the parent's handlers)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    log = logging.getLogger("gtu_academic_engine.pw_subprocess")
    log.info("[PW-PROC] Worker started in PID=%s", os.getpid())

    provider = None

    while True:
        # Block waiting for the next task (or stop signal)
        try:
            item = req_q.get(timeout=600)  # 10-min idle → exit cleanly
        except Exception:
            log.info("[PW-PROC] Idle timeout — worker exiting.")
            break

        if item is None:
            log.info("[PW-PROC] Stop signal — worker exiting.")
            break

        task_id, method, args, kwargs = item

        try:
            # Lazy-init: create provider on first real request
            if provider is None:
                log.info("[PW-PROC] Importing and starting ASPXProvider…")
                # Import inside the child so nothing is accidentally shared
                from gtu_academic_engine.provider.aspx_provider import ASPXProvider
                provider = ASPXProvider(headless=True)
                provider._start()
                log.info("[PW-PROC] ASPXProvider ready.")

            result = getattr(provider, method)(*args, **kwargs)
            res_q.put((task_id, True, result))

        except Exception as exc:
            log.exception("[PW-PROC] Error in %s: %s", method, exc)
            res_q.put((task_id, False, str(exc)))

            # Reset provider — the browser might be in a broken state
            if provider is not None:
                try:
                    provider.close()
                except Exception:
                    pass
                provider = None

    # Graceful cleanup
    if provider is not None:
        try:
            provider.close()
        except Exception:
            pass
    log.info("[PW-PROC] Worker shut down cleanly.")


# ── Parent-side wrapper ───────────────────────────────────────────────────────

class PlaywrightSubprocessWorker:
    """Manages a child process that owns the Playwright browser.

    Usage (in server.py)::

        _PW_PROC = PlaywrightSubprocessWorker()
        result = _PW_PROC.call("fetch_branches", "BE")
        _PW_PROC.stop()   # on shutdown

    All data passed through the queues must be pickle-able.
    ASPXProvider return values (lists/dicts of strings) satisfy this.
    """

    def __init__(self) -> None:
        self._req_q: "multiprocessing.queues.Queue" = _MP_CTX.Queue()
        self._res_q: "multiprocessing.queues.Queue" = _MP_CTX.Queue()
        self._task_counter = 0
        self._process = _MP_CTX.Process(
            target=_worker_main,
            args=(self._req_q, self._res_q),
            daemon=True,
            name="playwright-subprocess",
        )
        self._process.start()
        logger.info(
            "[PW-PROC] Subprocess started (PID=%s).", self._process.pid
        )

    # ------------------------------------------------------------------

    def call(self, method: str, *args: Any, timeout: float = 120.0, **kwargs: Any) -> Any:
        """Call ASPXProvider.<method>(*args, **kwargs) in the child process.

        Blocks the calling thread until the result is available.
        Re-raises any exception that occurred in the child.

        Args:
            method:  Name of the ASPXProvider method to call.
            timeout: Maximum seconds to wait (default 120 = 2 min).

        Returns:
            Whatever the method returns.

        Raises:
            RuntimeError: If the child reported an exception.
            TimeoutError: If the child didn't respond within *timeout* seconds.
        """
        # Restart dead worker transparently
        if not self._process.is_alive():
            logger.warning("[PW-PROC] Worker process died — restarting.")
            self._restart()

        self._task_counter += 1
        task_id = self._task_counter

        self._req_q.put((task_id, method, args, kwargs))

        # Collect the matching response (discard stale ones)
        while True:
            try:
                resp_id, ok, value = self._res_q.get(timeout=timeout)
            except Exception as exc:
                raise TimeoutError(
                    f"Playwright subprocess did not respond for {method!r} "
                    f"within {timeout}s"
                ) from exc

            if resp_id == task_id:
                if not ok:
                    raise RuntimeError(
                        f"Playwright subprocess error in {method!r}: {value}"
                    )
                return value

            # Stale response from a previous (possibly failed) task — discard
            logger.debug(
                "[PW-PROC] Discarding stale response task_id=%s (wanted %s)",
                resp_id, task_id,
            )

    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Shut down the worker process gracefully."""
        logger.info("[PW-PROC] Sending stop signal to worker process.")
        if self._process.is_alive():
            try:
                self._req_q.put(None)          # stop sentinel
                self._process.join(timeout=10)
            except Exception:
                pass
            if self._process.is_alive():
                logger.warning("[PW-PROC] Process did not exit — terminating.")
                self._process.terminate()
                self._process.join(timeout=5)
        logger.info("[PW-PROC] Worker stopped.")

    def _restart(self) -> None:
        """Replace the worker process with a fresh one."""
        try:
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=5)
        except Exception:
            pass

        self._req_q  = _MP_CTX.Queue()
        self._res_q  = _MP_CTX.Queue()
        self._process = _MP_CTX.Process(
            target=_worker_main,
            args=(self._req_q, self._res_q),
            daemon=True,
            name="playwright-subprocess",
        )
        self._process.start()
        logger.info(
            "[PW-PROC] Worker restarted (PID=%s).", self._process.pid
        )
