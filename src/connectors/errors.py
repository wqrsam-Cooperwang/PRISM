"""Auditable error classes for PRISM provider connectors."""

from __future__ import annotations


class ProviderConnectorError(RuntimeError):
    """Base class for provider connector failures."""


class HttpTransportError(ProviderConnectorError):
    """Network, DNS, TLS, or timeout failure before a usable response."""


class HttpStatusError(ProviderConnectorError):
    """Non-success HTTP response that may not proceed downstream."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Provider HTTP request failed with status {status_code}")


class HttpDecodeError(ProviderConnectorError):
    """Provider response body could not be decoded into the expected representation."""


class ProviderSchemaError(ProviderConnectorError):
    """Decoded provider payload does not satisfy the connector schema."""
