from datetime import UTC, datetime, timedelta

import httpx
import pytest

from ingest.fetch import FetchBudgetExceeded, ObservedClient


def client_with_statuses(statuses, headers=None):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(statuses[len(calls) - 1], headers=headers, json={"jobs": []})

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def test_transient_retry_counts_real_requests_and_does_not_log_payloads():
    client, calls = client_with_statuses([503, 200])
    waits = []
    observer = ObservedClient(client, {"retry_delays_seconds": [5]}, sleeper=waits.append)
    observer.get("https://example.com/jobs?token=secret")
    assert len(calls) == observer.requests == 2
    assert observer.pages_fetched == 1
    assert observer.retries == 1
    assert observer.status_codes == {"503": 1, "200": 1}
    assert any(wait >= 5 for wait in waits)
    assert "secret" not in str(observer.events)
    assert "jobs" not in str(observer.events)


def test_403_is_never_retried():
    client, calls = client_with_statuses([403])
    observer = ObservedClient(client, {}, sleeper=lambda _: None)
    with pytest.raises(httpx.HTTPStatusError):
        observer.get("https://example.com")
    assert len(calls) == 1
    assert observer.retries == 0


def test_long_retry_after_defers_to_a_later_poll():
    client, calls = client_with_statuses([429], {"Retry-After": "3600"})
    observer = ObservedClient(client, {}, sleeper=lambda _: None)
    before = datetime.now(UTC)
    with pytest.raises(httpx.HTTPStatusError):
        observer.get("https://example.com")
    assert observer.next_allowed_at >= before + timedelta(seconds=3600)
    assert len(calls) == 1


def test_short_retry_after_is_respected():
    client, _ = client_with_statuses([429, 200], {"Retry-After": "10"})
    waits = []
    observer = ObservedClient(client, {}, sleeper=waits.append)
    observer.get("https://example.com")
    assert any(wait >= 10 for wait in waits)


def test_request_budget_stops_retries():
    client, calls = client_with_statuses([503])
    observer = ObservedClient(client, {"max_requests_per_run": 1}, sleeper=lambda _: None)
    with pytest.raises(FetchBudgetExceeded):
        observer.get("https://example.com")
    assert len(calls) == 1


def test_network_timeout_is_retried_within_budget():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("do not persist private body", request=request)
        return httpx.Response(200, json={})

    observer = ObservedClient(
        httpx.Client(transport=httpx.MockTransport(handler)), {}, sleeper=lambda _: None
    )
    observer.get("https://example.com")
    assert observer.retries == 1
    assert observer.events[0]["error_type"] == "ReadTimeout"
    assert "private" not in str(observer.events)
