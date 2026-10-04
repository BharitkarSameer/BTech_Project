import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 86400):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if not item:
            return None
        ts, value = item
        if time.time() - ts > self.ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)


sentinel_cache = TTLCache(ttl_seconds=86400)
autofill_cache = TTLCache(ttl_seconds=3600)
