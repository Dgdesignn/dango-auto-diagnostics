"""Bounded, session-local samples; unsuccessful attempts are explicit gaps."""

from collections import deque
from datetime import datetime
from math import isfinite

from scanner_outo.models import AVAILABLE


class ReadingSeries:
    def __init__(self, limit: int = 300):
        if limit < 2:
            raise ValueError("O limite deve ser pelo menos dois.")
        self.limit = limit
        self.session_id = None
        self.samples = {}
        self.last_attempt = {}
        self.interrupted = set()

    def interrupt(self, pids=None) -> None:
        self.interrupted.update(key for key in self.samples if pids is None or key[0] in pids)

    def ingest(self, session: dict) -> None:
        if session.get("created_at") != self.session_id:
            self.session_id = session.get("created_at")
            self.samples.clear()
            self.last_attempt.clear()
            self.interrupted.clear()
        for reading in session.get("readings", []):
            key = (reading["pid"], reading["ecu"])
            timestamp = reading.get("attempted_at")
            if not timestamp or self.last_attempt.get(key) == timestamp:
                continue
            try:
                instant = datetime.fromisoformat(timestamp).timestamp() * 1000
            except (ValueError, TypeError):
                continue
            value = reading.get("value")
            valid = (reading.get("status") == AVAILABLE and not reading.get("stale")
                     and value is not None and isfinite(value) and reading.get("timestamp") == timestamp)
            samples = self.samples.setdefault(key, deque(maxlen=self.limit))
            if key in self.interrupted:
                samples.append((instant, None))
                self.interrupted.discard(key)
            samples.append((instant, value if valid else None))
            self.last_attempt[key] = timestamp

    def segments(self, pid: str) -> dict:
        result = {}
        for (sample_pid, ecu), samples in self.samples.items():
            if sample_pid != pid:
                continue
            segments, current = [], []
            for instant, value in samples:
                if value is None:
                    if current:
                        segments.append(current)
                        current = []
                else:
                    current.append((instant, value))
            if current:
                segments.append(current)
            result[ecu] = segments
        return result
