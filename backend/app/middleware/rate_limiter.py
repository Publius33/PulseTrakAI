"""
Rate limiter middleware (sliding window) for PulseTrakAI™

Features:
- Sliding window rate limiter
- Per-IP and per-API-key limits
- Burst protection
- Configurable via env: RATE_LIMIT_IP and RATE_LIMIT_API_KEY (values per minute)

This implementation is an in-memory demo intended for Stage 4 scaffolding.
For production use a distributed store (Redis) or API gateway.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import os
import time
from collections import deque, defaultdict
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def _env_limit(name: str, default_per_min: int) -> int:
    v = os.environ.get(name)
    try:
        if v:
            return int(v)
    except Exception:
        pass
    return default_per_min


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window per-key rate limiter with burst protection.

    Uses deques of timestamps per key and prunes entries older than window.
    Keys: per-IP (remote host) and per-API-Key (X-API-Key / Authorization).
    """

    def __init__(self, app, **kwargs):
        super().__init__(app)
        # limits in requests per minute
        self.ip_limit = _env_limit('RATE_LIMIT_IP', 200)
        self.api_key_limit = _env_limit('RATE_LIMIT_API_KEY', 600)
        # burst factor allows short spikes up to burst_factor * limit
        self.burst_factor = float(os.environ.get('RATE_LIMIT_BURST_FACTOR', '1.5'))
        # windows: 60 seconds
        self.window_seconds = 60
        # storage
        self.ip_buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self.key_buckets: Dict[str, Deque[float]] = defaultdict(deque)

    def _prune(self, dq: Deque[float], now: float):
        cutoff = now - self.window_seconds
        while dq and dq[0] < cutoff:
            dq.popleft()

    async def dispatch(self, request: Request, call_next):
        now = time.time()

        # determine client IP
        client = request.client
        ip = getattr(client, 'host', 'unknown') if client else 'unknown'

        # determine api key
        api_key = None
        if 'x-api-key' in request.headers:
            api_key = request.headers.get('x-api-key')
        elif 'X-Api-Key' in request.headers:
            api_key = request.headers.get('X-Api-Key')
        else:
            auth = request.headers.get('authorization')
            if auth and auth.lower().startswith('bearer '):
                api_key = auth.split(' ', 1)[1]

        # check per-IP
        ip_dq = self.ip_buckets[ip]
        self._prune(ip_dq, now)
        ip_capacity = int(self.ip_limit * self.burst_factor)
        if len(ip_dq) >= ip_capacity:
            retry_after = int(self.window_seconds - (now - ip_dq[0])) if ip_dq else self.window_seconds
            return JSONResponse({"detail": "Too many requests (IP)"}, status_code=429, headers={"Retry-After": str(retry_after)})

        # check per-api-key if present (stronger limit)
        if api_key:
            key_dq = self.key_buckets[api_key]
            self._prune(key_dq, now)
            key_capacity = int(self.api_key_limit * self.burst_factor)
            if len(key_dq) >= key_capacity:
                retry_after = int(self.window_seconds - (now - key_dq[0])) if key_dq else self.window_seconds
                return JSONResponse({"detail": "Too many requests (API key)"}, status_code=429, headers={"Retry-After": str(retry_after)})

        # record requests
        ip_dq.append(now)
        if api_key:
            self.key_buckets[api_key].append(now)

        # Set headers to indicate remaining budget (best-effort)
        remaining_ip = max(0, self.ip_limit - len([t for t in ip_dq if t >= now - self.window_seconds]))
        headers = {
            'X-RateLimit-Limit-IP': str(self.ip_limit),
            'X-RateLimit-Remaining-IP': str(remaining_ip),
        }
        if api_key:
            remaining_key = max(0, self.api_key_limit - len([t for t in self.key_buckets[api_key] if t >= now - self.window_seconds]))
            headers.update({'X-RateLimit-Limit-Key': str(self.api_key_limit), 'X-RateLimit-Remaining-Key': str(remaining_key)})

        response = await call_next(request)
        for k, v in headers.items():
            response.headers.setdefault(k, v)
        return response
