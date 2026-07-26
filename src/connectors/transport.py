"""Real standard-library HTTP transport for PRISM provider connectors."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from src.connectors.errors import HttpTransportError
from src.connectors.models import HttpRequest, HttpResponse


def _url_with_query(request: HttpRequest) -> str:
    parts = urlsplit(request.url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    query_items.extend(sorted(request.query.items()))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment)
    )


class StdlibHttpTransport:
    """Execute real HTTP requests with Python's standard library."""

    def send(self, request: HttpRequest) -> HttpResponse:
        outbound = Request(
            _url_with_query(request),
            data=b"" if request.method == "POST" else None,
            headers=dict(request.headers),
            method=request.method,
        )
        try:
            with urlopen(outbound, timeout=request.timeout_seconds) as response:
                status_code = response.getcode()
                if status_code is None:
                    raise HttpTransportError("Provider HTTP response did not include a status code")
                return HttpResponse(
                    status_code=status_code,
                    headers=dict(response.headers.items()),
                    body=response.read(),
                    received_at=datetime.now(timezone.utc),
                )
        except HTTPError as exc:
            return HttpResponse(
                status_code=exc.code,
                headers=dict(exc.headers.items()) if exc.headers is not None else {},
                body=exc.read(),
                received_at=datetime.now(timezone.utc),
            )
        except OSError as exc:
            raise HttpTransportError("Provider HTTP transport failed") from exc
