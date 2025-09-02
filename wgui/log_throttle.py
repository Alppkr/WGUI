from __future__ import annotations

import threading
import time
from typing import Dict, Tuple


class _Window:
    __slots__ = ("start", "count")

    def __init__(self, start: float) -> None:
        self.start = start
        self.count = 0


class LoginFailThrottle:
    """In-process, best-effort throttle for login_failed audit logging.

    Limits the number of audit rows per (username_lower, ip) within a time window.
    This does NOT block authentication; it only reduces noisy audit writes.
    """

    def __init__(self, window_seconds: int, max_per_window: int) -> None:
        self.window = float(window_seconds)
        self.max = int(max_per_window)
        self._lock = threading.Lock()
        self._buckets: Dict[Tuple[str, str], _Window] = {}

    def allow(self, username: str | None, ip: str | None) -> bool:
        k = (str(username or '').lower(), str(ip or ''))
        now = time.monotonic()
        with self._lock:
            w = self._buckets.get(k)
            if (w is None) or (now - w.start >= self.window):
                # reset window
                self._buckets[k] = w = _Window(start=now)
                w.count = 0
            if w.count < self.max:
                w.count += 1
                self._cleanup(now)
                return True
            # over the limit: deny logging
            self._cleanup(now)
            return False

    def _cleanup(self, now: float) -> None:
        # Periodically remove stale keys to prevent unbounded growth
        # Cheap sweep: when dict grows large, drop entries older than 2x window
        if len(self._buckets) < 1024:
            return
        cutoff = now - (self.window * 2)
        stale = [k for k, w in self._buckets.items() if w.start < cutoff]
        for k in stale:
            self._buckets.pop(k, None)


_throttle_instance: LoginFailThrottle | None = None


def should_log_login_failure(app, username: str | None, ip: str | None) -> bool:
    """Return True if we should write a login_failed audit row for this (username, ip).

    Uses app config:
      - LOGIN_FAIL_LOG_WINDOW_SECONDS (default 60)
      - LOGIN_FAIL_LOG_MAX_PER_WINDOW (default 5)
    """
    global _throttle_instance
    if _throttle_instance is None:
        window = int(app.config.get('LOGIN_FAIL_LOG_WINDOW_SECONDS', 60))
        maxn = int(app.config.get('LOGIN_FAIL_LOG_MAX_PER_WINDOW', 5))
        _throttle_instance = LoginFailThrottle(window, maxn)
    return _throttle_instance.allow(username, ip)

