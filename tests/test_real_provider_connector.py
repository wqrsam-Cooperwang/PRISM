from datetime import datetime, timezone
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from src.connectors import (
    FixtureHttpTransport,
    HttpDecodeError,
    HttpRequest,
    HttpResponse,
    HttpStatusError,
    HttpTransportError,
    ProviderSchemaError,
    RetryPolicy,
    StdlibHttpTransport,
    decode_json_object,
    send_with_retry,
)

FIXED_NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)


def _response(status: int, body: bytes = b"{}") -> HttpResponse:
    return HttpResponse(status_code=status, headers={}, body=body, received_at=FIXED_NOW)


def test_http_request_normalizes_and_validates_transport_inputs() -> None:
    request = HttpRequest(
        method="get",
        url="https://provider.example/match",
        headers={"X-Test": "yes"},
        query={"b": "2", "a": "1"},
        timeout_seconds=5,
    )

    assert request.method == "GET"
    assert request.timeout_seconds == pytest.approx(5.0)
    with pytest.raises(ValueError, match="http or https"):
        HttpRequest(method="GET", url="ftp://provider.example")
    with pytest.raises(ValueError, match="positive finite"):
        HttpRequest(method="GET", url="https://provider.example", timeout_seconds=0)


def test_stdlib_transport_constructs_real_request_without_live_network(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        headers = Message()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        def getcode(self) -> int:
            return 200

        def read(self) -> bytes:
            return b'{"ok": true}'

    def fake_urlopen(outbound, timeout):
        captured["url"] = outbound.full_url
        captured["method"] = outbound.get_method()
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("src.connectors.transport.urlopen", fake_urlopen)
    response = StdlibHttpTransport().send(
        HttpRequest(
            method="GET",
            url="https://provider.example/match?existing=yes",
            query={"b": "2", "a": "1"},
            timeout_seconds=7,
        )
    )

    assert captured == {
        "url": "https://provider.example/match?existing=yes&a=1&b=2",
        "method": "GET",
        "timeout": 7.0,
    }
    assert response.status_code == 200
    assert response.body == b'{"ok": true}'


def test_stdlib_transport_converts_http_error_to_response(monkeypatch) -> None:
    headers = Message()
    headers["Retry-After"] = "1"
    error = HTTPError(
        "https://provider.example",
        503,
        "unavailable",
        headers,
        BytesIO(b'{"error": "unavailable"}'),
    )

    def fake_urlopen(outbound, timeout):
        del outbound, timeout
        raise error

    monkeypatch.setattr("src.connectors.transport.urlopen", fake_urlopen)
    response = StdlibHttpTransport().send(HttpRequest(method="GET", url="https://provider.example"))

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "1"


def test_stdlib_transport_classifies_network_failure(monkeypatch) -> None:
    def fake_urlopen(outbound, timeout):
        del outbound, timeout
        raise URLError("dns failure")

    monkeypatch.setattr("src.connectors.transport.urlopen", fake_urlopen)
    with pytest.raises(HttpTransportError, match="transport failed"):
        StdlibHttpTransport().send(HttpRequest(method="GET", url="https://provider.example"))


def test_retry_policy_retries_transport_and_retryable_statuses() -> None:
    request = HttpRequest(method="GET", url="https://provider.example")
    transport = FixtureHttpTransport(
        [
            HttpTransportError("temporary network failure"),
            _response(503),
            _response(200, b'{"ok": true}'),
        ]
    )

    response = send_with_retry(transport, request, RetryPolicy(max_attempts=3))

    assert response.status_code == 200
    assert len(transport.requests) == 3


def test_non_retryable_http_status_fails_immediately() -> None:
    request = HttpRequest(method="GET", url="https://provider.example")
    transport = FixtureHttpTransport([_response(401), _response(200)])

    with pytest.raises(HttpStatusError) as captured:
        send_with_retry(transport, request)

    assert captured.value.status_code == 401
    assert len(transport.requests) == 1


def test_retry_exhaustion_preserves_final_status_or_transport_error() -> None:
    request = HttpRequest(method="GET", url="https://provider.example")
    status_transport = FixtureHttpTransport([_response(429), _response(429)])
    with pytest.raises(HttpStatusError) as status_error:
        send_with_retry(status_transport, request, RetryPolicy(max_attempts=2))
    assert status_error.value.status_code == 429

    network_transport = FixtureHttpTransport(
        [HttpTransportError("first"), HttpTransportError("second")]
    )
    with pytest.raises(HttpTransportError, match="second"):
        send_with_retry(network_transport, request, RetryPolicy(max_attempts=2))


def test_json_decoder_accepts_object_and_rejects_invalid_payloads() -> None:
    decoded = decode_json_object(_response(200, b'{"fixture": 1}'))
    assert decoded == {"fixture": 1}

    with pytest.raises(HttpDecodeError, match="UTF-8"):
        decode_json_object(_response(200, b"\xff"))
    with pytest.raises(HttpDecodeError, match="valid JSON"):
        decode_json_object(_response(200, b"not-json"))
    with pytest.raises(ProviderSchemaError, match="must be an object"):
        decode_json_object(_response(200, b"[]"))


def test_retry_policy_validation_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="valid HTTP status"):
        RetryPolicy(retryable_statuses=frozenset({999}))
