from __future__ import annotations

import uuid
from typing import Optional

try:
    import redis
except Exception:  # pragma: no cover - redis optional
    redis = None


class IdempotencyService:
    def __init__(self, redis_url: Optional[str] = None):
        self._memory: dict[str, str] = {}
        self._client = None
        if redis and redis_url:
            try:
                self._client = redis.Redis.from_url(redis_url)
            except Exception:
                self._client = None

    def new_key(self, prefix: str) -> str:
        return f"{prefix}:{uuid.uuid4()}"

    def store(self, key: str, value: str) -> None:
        if self._client:
            self._client.setnx(key, value)
        else:
            self._memory.setdefault(key, value)

    def seen(self, key: str) -> Optional[str]:
        if self._client:
            value = self._client.get(key)
            return value.decode() if value else None
        return self._memory.get(key)
