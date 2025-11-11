from __future__ import annotations

import json
from typing import Optional

try:
    import redis
except Exception:  # pragma: no cover - optional
    redis = None


class ConversationStorage:
    def __init__(self, redis_url: Optional[str] = None):
        self._memory: dict[str, dict] = {}
        self._client = None
        if redis and redis_url:
            try:
                self._client = redis.Redis.from_url(redis_url)
            except Exception:
                self._client = None

    def load(self, key: str) -> Optional[dict]:
        if self._client:
            raw = self._client.get(key)
            if raw:
                return json.loads(raw)
            return None
        return self._memory.get(key)

    def save(self, key: str, state: dict) -> None:
        if self._client:
            self._client.set(key, json.dumps(state))
        else:
            self._memory[key] = state
