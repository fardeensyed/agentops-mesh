from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from queue import Empty, Queue
from typing import TYPE_CHECKING, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# TYPE_CHECKING is False at runtime — this import only exists for
# type hints so we avoid a circular import between tracer and exporter
if TYPE_CHECKING:
    from .span import Span

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# JSON serialization helper
# datetime objects are not JSON-serializable by default.
# This custom encoder converts them to ISO 8601 strings automatically.
# ─────────────────────────────────────────────────────────────────────────────

class _DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# ─────────────────────────────────────────────────────────────────────────────
# SpanExporter
# Runs in a background daemon thread.
# Drains spans from a queue and POSTs them to the ingestion gateway.
# ─────────────────────────────────────────────────────────────────────────────

class SpanExporter:
    """
    Background exporter that batches finished spans and sends them
    to the AgentOps Mesh ingestion gateway over HTTP.

    Usage (handled internally by Tracer — users never touch this):
        exporter = SpanExporter(
            endpoint="http://localhost:8000",
            api_key="your-key",
        )
        exporter.start()
        exporter.enqueue(span)
        exporter.shutdown()  # flushes remaining spans before exit
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        batch_size: int = 50,
        flush_interval: float = 2.0,
        max_queue_size: int = 10_000,
    ):
        self.endpoint  = endpoint.rstrip("/") + "/v1/spans"
        self.api_key   = api_key
        self.batch_size     = batch_size      # max spans per HTTP request
        self.flush_interval = flush_interval  # seconds between flushes

        # Queue is thread-safe — tracer pushes spans in,
        # background thread pulls spans out
        self._queue: Queue = Queue(maxsize=max_queue_size)

        # daemon=True means this thread dies automatically
        # when your main program exits — no hanging processes
        self._thread = threading.Thread(
            target=self._run,
            name="agentops-exporter",
            daemon=True,
        )

        # used to signal the background thread to stop cleanly
        self._stop_event = threading.Event()

        # tracks whether exporter has been started
        self._running = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background export thread."""
        if self._running:
            return
        self._running = True
        self._thread.start()
        logger.debug("SpanExporter started")

    def shutdown(self, timeout: float = 5.0) -> None:
        """
        Graceful shutdown — flushes remaining spans then stops.
        Call this when your program exits so no spans are lost.
        timeout: how long to wait for final flush (seconds)
        """
        if not self._running:
            return
        self._stop_event.set()   # signal thread to stop after next flush
        self._thread.join(timeout=timeout)
        self._running = False
        logger.debug("SpanExporter shut down")

    # ── Enqueue ───────────────────────────────────────────────────────────────

    def enqueue(self, span: "Span") -> None:
        """
        Add a finished span to the export queue.
        Called by Tracer._close_span() — never called by user code.
        Non-blocking — if queue is full, span is dropped with a warning.
        """
        try:
            self._queue.put_nowait(span.to_dict())
        except Exception:
            logger.warning(
                "SpanExporter queue full — dropping span: %s", span.name
            )

    # ── Background thread ────────────────────────────────────────────────────

    def _run(self) -> None:
        """
        Main loop of the background thread.
        Runs forever until shutdown() is called.
        Every flush_interval seconds, drains the queue and sends a batch.
        """
        while not self._stop_event.is_set():
            time.sleep(self.flush_interval)
            self._flush()

        # shutdown() was called — do one final flush so we don't lose spans
        self._flush()

    def _flush(self) -> None:
        """
        Drains up to batch_size spans from the queue and sends them.
        If queue is empty, does nothing.
        """
        batch: List[dict] = []

        # drain up to batch_size items from the queue
        # queue.get_nowait() raises Empty when nothing is left
        while len(batch) < self.batch_size:
            try:
                item = self._queue.get_nowait()
                batch.append(item)
            except Empty:
                break

        if not batch:
            return  # nothing to send

        self._send(batch)

    # ── HTTP sending with retry ───────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=False,  # don't crash the exporter if all retries fail
    )
    def _send(self, batch: List[dict]) -> None:
        """
        POST a batch of span dicts to the ingestion gateway.
        Retried up to 3 times with exponential backoff:
            attempt 1 — immediately
            attempt 2 — wait 1 second
            attempt 3 — wait 2 seconds
        If all 3 fail, logs a warning and moves on (spans are lost).
        """
        payload = json.dumps(
            {"spans": batch, "service": "agentops-sdk"},
            cls=_DatetimeEncoder,
        )

        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-SDK-Version": "0.1.0",
        }

        # timeout=(connect_timeout, read_timeout) in seconds
        with httpx.Client(timeout=(3.0, 10.0)) as client:
            response = client.post(
                self.endpoint,
                content=payload,
                headers=headers,
            )

        if response.status_code == 200:
            logger.debug("Exported %d spans successfully", len(batch))
        else:
            logger.warning(
                "Export failed: HTTP %d — %s",
                response.status_code,
                response.text[:200],
            )
            # raise so tenacity knows to retry
            response.raise_for_status()