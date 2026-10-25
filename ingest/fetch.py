"""Bounded, observable HTTP access; never record response bodies or exception text."""

from __future__ import annotations

import random
import time
from collections import Counter
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx
import requests


class FetchBudgetExceeded(RuntimeError):
    pass


class ObservedClient:
    """Wrap an adapter's existing client without changing its transport or identity."""

    def __init__(self, client, policy: dict, *, sleeper=time.sleep, on_event=None):
        self.on_event = on_event
        self.client = client
        self.policy = policy
        self.sleeper = sleeper
        self.requests = 0
        self.pages_fetched = 0
        self.retries = 0
        self.status_codes: Counter[str] = Counter()
        self.events: list[dict] = []
        self.next_allowed_at: datetime | None = None
        self.last_request_at: float | None = None

    def get(self, url, **kwargs):
        return self._request("get", url, **kwargs)

    def post(self, url, **kwargs):
        # Elevolt's POST is a read-only search. No mutating HTTP verbs are supported.
        return self._request("post", url, **kwargs)

    def _request(self, method, url, **kwargs):
        delays = self.policy.get("retry_delays_seconds", [5, 20])[:2]
        budget = self.policy.get("max_requests_per_run", 60)
        timeout = self.policy.get("timeout_seconds", 15)
        kwargs["timeout"] = timeout
        for attempt in range(len(delays) + 1):
            if self.requests >= budget:
                raise FetchBudgetExceeded("source request budget exhausted")
            if self.last_request_at is not None:
                gap = self.policy.get("request_delay_ms", 1500) / 1000
                self.sleeper(max(0, gap - (time.monotonic() - self.last_request_at)))
            started = datetime.now(UTC)
            tick = time.monotonic()
            self.requests += 1
            response = None
            error = None
            code = None
            try:
                response = getattr(self.client, method)(url, **kwargs)
                code = response.status_code
                self.status_codes[str(code)] += 1
                if code != 304:
                    response.raise_for_status()
            except (httpx.HTTPError, requests.exceptions.RequestException) as exc:
                error = exc
            finally:
                self.last_request_at = time.monotonic()
            self.events.append(
                {
                    "started_at": started.isoformat(),
                    "duration_seconds": round(time.monotonic() - tick, 3),
                    "method": method.upper(),
                    "host": urlparse(str(url)).hostname,
                    "http_status": code,
                    "attempt": attempt + 1,
                    "error_type": type(error).__name__ if error else None,
                }
            )
            if self.on_event:
                self.on_event(self.events[-1])
            if error is None:
                self.pages_fetched += 1
                return response
            # Never retry a deliberate block or a permanent 4xx response.
            transient = code in (429, 500, 502, 503, 504) or isinstance(
                error,
                (
                    httpx.TransportError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                ),
            )
            delay = delays[attempt] if attempt < len(delays) else None
            if response is not None and code in (429, 503):
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        retry_delay = max(0, float(retry_after))
                    except ValueError:
                        try:
                            retry_delay = max(
                                0,
                                (
                                    parsedate_to_datetime(retry_after) - datetime.now(UTC)
                                ).total_seconds(),
                            )
                        except (TypeError, ValueError, OverflowError):
                            retry_delay = None
                    if retry_delay is not None:
                        from datetime import timedelta

                        self.next_allowed_at = datetime.now(UTC) + timedelta(seconds=retry_delay)
                        if delay is not None:
                            delay = max(delay, retry_delay)
            if not transient or delay is None or delay > 120:
                raise error
            self.retries += 1
            self.sleeper(delay + random.uniform(0, 1))
        raise AssertionError("unreachable")
