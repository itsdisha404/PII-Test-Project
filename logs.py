from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import List


@dataclass
class LogEntry:
    id: int
    timestamp: str
    user_id: str
    action: str  # "mask" | "unmask"
    context: str
    before: str
    after: str


class MaskingLog:
    """In-memory, process-wide log of masking/unmasking events, for the /view page."""

    def __init__(self) -> None:
        self._entries: List[LogEntry] = []
        self._lock = Lock()
        self._counter = itertools.count(1)

    def record(self, *, user_id: str, action: str, context: str, before: str, after: str) -> None:
        entry = LogEntry(
            id=next(self._counter),
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            user_id=user_id,
            action=action,
            context=context,
            before=before,
            after=after,
        )
        with self._lock:
            self._entries.append(entry)

    def all(self) -> List[LogEntry]:
        with self._lock:
            return list(self._entries)


masking_log = MaskingLog()
