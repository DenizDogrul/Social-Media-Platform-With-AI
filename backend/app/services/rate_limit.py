from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def enforce(self, key: str, limit: int, window_seconds: int) -> None:
        now = monotonic()
        window_start = now - window_seconds

        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < window_start:
                bucket.popleft()

            if len(bucket) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please retry later.",
                )

            bucket.append(now)


limiter = InMemoryRateLimiter()


def apply_rate_limit(
    request: Request,
    *,
    bucket: str,
    limit: int,
    window_seconds: int,
    user_id: int | None = None,
) -> None:
    client_ip = request.client.host if request.client else "unknown"
    identity = f"user:{user_id}" if user_id is not None else f"ip:{client_ip}"
    limiter.enforce(f"{bucket}:{identity}", limit=limit, window_seconds=window_seconds)
