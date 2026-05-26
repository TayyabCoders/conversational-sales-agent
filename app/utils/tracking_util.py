"""
Performance Tracking Utility
==============================
Per-request performance tracking with predefined segment categories
and context-manager support for clean instrumentation.

Usage in services / mediators:
    tracker = request.state.performance

    tracker.start("database")
    result = await db.execute(query)
    tracker.end("database")

    # Or with context manager:
    with tracker.track("external"):
        resp = await httpx.get("https://api.example.com")

    # Get all timings at end of request:
    metrics = tracker.get_metrics()  # {"database": 12, "external": 84, ...}
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

# Predefined segment categories for consistent naming
SEGMENT_AUTH = "auth"
SEGMENT_VALIDATION = "validation"
SEGMENT_BUSINESS = "business"
SEGMENT_DATABASE = "database"
SEGMENT_EXTERNAL = "external"
SEGMENT_SERIALIZATION = "serialization"
SEGMENT_CACHE = "cache"


class PerformanceTracker:
    """Track timing of named segments within a single request lifecycle."""

    __slots__ = ("request", "_starts", "_durations")

    def __init__(self, request):
        self.request = request
        self._starts: Dict[str, float] = {}
        self._durations: Dict[str, int] = {}

    def start(self, name: str) -> None:
        """Mark the start of a named segment."""
        self._starts[name] = time.time()

    def end(self, name: str) -> Optional[int]:
        """Mark the end of a named segment. Returns duration in ms."""
        start = self._starts.pop(name, None)
        if start is None:
            return None
        duration_ms = int((time.time() - start) * 1000)
        # Accumulate in case the same segment is measured multiple times
        self._durations[name] = self._durations.get(name, 0) + duration_ms
        logger.debug(
            "performance_segment",
            segment=name,
            duration_ms=duration_ms,
        )
        return duration_ms

    @contextmanager
    def track(self, name: str):
        """Context-manager for clean segment tracking.

        Example:
            with tracker.track("database"):
                await db.execute(query)
        """
        self.start(name)
        try:
            yield
        finally:
            self.end(name)

    def get_metrics(self) -> Dict[str, int]:
        """Return all completed segment durations in ms."""
        return dict(self._durations)

    def has_segments(self) -> bool:
        """Check if any segments have been recorded."""
        return bool(self._durations)
