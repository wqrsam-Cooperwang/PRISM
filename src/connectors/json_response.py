"""Fail-closed JSON response decoding for PRISM provider connectors."""

from __future__ import annotations

import json
from typing import Any

from src.connectors.errors import HttpDecodeError, ProviderSchemaError
from src.connectors.models import HttpResponse


def decode_json_object(response: HttpResponse) -> dict[str, Any]:
    """Decode a UTF-8 JSON object and reject non-object provider payloads."""

    try:
        text = response.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HttpDecodeError("Provider response is not valid UTF-8") from exc
    try:
        decoded: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HttpDecodeError("Provider response is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ProviderSchemaError("Provider JSON response must be an object")
    return {str(key): value for key, value in decoded.items()}
