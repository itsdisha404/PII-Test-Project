from __future__ import annotations

from typing import Dict, Optional

from piiMask import PIIMasker


class SessionMemory:
    def __init__(self, system_prompt: str, masker_kwargs: Optional[dict] = None):
        self.system_prompt = system_prompt
        self._masker_kwargs = masker_kwargs or {}
        self._store: Dict[str, dict] = {}

    def get(self, user_id: str) -> dict:
        """Fetch (or create) this user's memory entry."""
        if user_id not in self._store:
            self._store[user_id] = {
                "messages": [{"role": "system", "content": self.system_prompt}],
                "masker": PIIMasker(**self._masker_kwargs),
            }
        return self._store[user_id]

    def reset(self, user_id: str) -> None:
        """Forget everything remembered about a user (history + PII mapping)."""
        self._store.pop(user_id, None)