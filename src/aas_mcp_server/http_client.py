# SPDX-FileCopyrightText: 2026 SAP SE or an SAP affiliate company and aas-mcp-server contributors
# SPDX-License-Identifier: Apache-2.0

"""
HTTP client configuration for AAS MCP Server.

Authentication uses a custom httpx.Auth subclass (BearerTokenAuth) that reads
the validated OAuth access token from FastMCP's request context via
get_access_token() on every outbound request. This works correctly across all
FastMCP versions because it does not rely on get_http_headers(), which in
FastMCP >=3.3 explicitly excludes the Authorization header from forwarding.

For stdio transport (or when OAuth is not configured), get_access_token()
returns None and no Authorization header is added.
"""

import ipaddress
import os
from typing import Generator
from urllib.parse import urlparse

import httpx
from fastmcp.server.dependencies import get_access_token

from .constants import (
    ENV_AAS_HTTP_TIMEOUT,
    DEFAULT_HTTP_TIMEOUT,
)

# HTTP headers
HEADER_ACCEPT = "Accept"
HEADER_AUTHORIZATION = "Authorization"
CONTENT_TYPE_JSON = "application/json"

# Authorization format
AUTH_BEARER_FORMAT = "Bearer {token}"

# Allowed URL schemes for AAS backend
_ALLOWED_SCHEMES = frozenset({"http", "https"})

# Link-local ranges used by cloud metadata services.
# These are the only IPs that pose a genuine SSRF risk when present as a
# literal IP in AAS_BASE_URL — an operator would never intentionally target
# 169.254.169.254. All other private/RFC-1918 ranges (10/8, 172.16/12,
# 192.168/16) are legitimate Docker / on-premises backend addresses and are
# NOT blocked here. Network-level controls are the right enforcement layer
# for restricting what backends the server is allowed to reach in production.
_CLOUD_METADATA_NETWORKS = [
    ipaddress.ip_network("169.254.0.0/16"),  # AWS/GCP/Azure/DO metadata
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


def _is_cloud_metadata_ip(ip_str: str) -> bool:
    """Return True if the IP is a cloud metadata / link-local address."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    # Unwrap IPv4-mapped IPv6 (::ffff:169.254.169.254)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        return _is_cloud_metadata_ip(str(addr.ipv4_mapped))
    return any(addr in net for net in _CLOUD_METADATA_NETWORKS)


def validate_backend_url(url: str) -> None:
    """
    Validate that AAS_BASE_URL is a safe HTTP/HTTPS URL.

    Scope of this check
    -------------------
    AAS_BASE_URL is operator-controlled configuration, not user input.
    The SSRF risk profile is therefore narrow:

    - Wrong scheme (file://, ftp://, ldap://) — operator error or env-var
      injection. Blocked: only http:// and https:// are permitted.
    - Cloud metadata literal IPs (169.254.0.0/16, fe80::/10) — an operator
      would never intentionally point AAS_BASE_URL at a metadata endpoint;
      its presence strongly indicates misconfiguration or injection. Blocked.

    What is NOT blocked
    -------------------
    - RFC 1918 private addresses (10/8, 172.16/12, 192.168/16): these are
      the standard Docker network ranges and are the most common backend
      addresses in containerised deployments. Blocking them would make the
      server unusable in any Docker/Compose/Kubernetes environment.
    - Hostnames that resolve to private IPs (e.g. Docker service names like
      'aas-env-rbac'): same reason. Docker service discovery relies on
      internal DNS that resolves to RFC 1918 addresses by design.

    Network-level egress controls (firewalls, Kubernetes NetworkPolicy,
    egress proxies) are the appropriate enforcement layer for restricting
    which backends the server is permitted to reach in production.

    Raises ValueError with an actionable message on any violation.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"AAS_BASE_URL is not a valid URL: {url!r}") from exc

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"AAS_BASE_URL uses scheme {parsed.scheme!r}, which is not allowed. "
            f"Only 'http' and 'https' are permitted. "
            f"If you intended to point at your AAS backend, check the URL — "
            f"it should start with 'http://' or 'https://'."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError(
            f"AAS_BASE_URL has no hostname: {url!r}. "
            f"Provide a full URL such as 'http://aas-backend:8081'."
        )

    # Only block literal cloud metadata IPs — not general private ranges.
    # Docker service hostnames and RFC 1918 IPs are legitimate backend targets.
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_cloud_metadata_ip(str(ip)):
            raise ValueError(
                f"AAS_BASE_URL points to a cloud metadata IP address ({hostname}). "
                f"This address is reserved for cloud instance metadata services "
                f"(AWS/GCP/Azure/DigitalOcean) and cannot be an AAS backend. "
                f"If this was unintentional, check the AAS_BASE_URL value. "
                f"Expected format: 'http://your-aas-backend:8081'."
            )
    except ValueError as exc:
        if "AAS_BASE_URL" in str(exc):
            raise  # re-raise our own errors, not ipaddress parse errors


class BearerTokenAuth(httpx.Auth):
    """
    httpx.Auth implementation that injects the current request's OAuth Bearer
    token into every outbound AAS backend call.

    Reads the token from FastMCP's get_access_token() at request time, so each
    tool invocation uses the token belonging to that specific MCP session user.
    Returns no Authorization header on stdio transport or when OAuth is not
    configured (get_access_token() returns None in those cases).
    """

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        access_token = get_access_token()
        if access_token is not None:
            request.headers[HEADER_AUTHORIZATION] = AUTH_BEARER_FORMAT.format(
                token=access_token.token
            )
        yield request


def build_async_client(base_url: str) -> httpx.AsyncClient:
    """
    Build an async HTTP client that forwards the OAuth Bearer token
    per-request via BearerTokenAuth.

    Validates base_url to prevent SSRF attacks before creating the client.

    Args:
        base_url: Base URL for the AAS backend

    Returns:
        Configured httpx.AsyncClient instance

    Raises:
        ValueError: If base_url fails security validation
    """
    validate_backend_url(base_url)
    timeout = float(os.getenv(ENV_AAS_HTTP_TIMEOUT, str(DEFAULT_HTTP_TIMEOUT)))
    return httpx.AsyncClient(
        base_url=base_url,
        headers={HEADER_ACCEPT: CONTENT_TYPE_JSON},
        auth=BearerTokenAuth(),
        timeout=timeout,
        follow_redirects=False,  # Never follow redirects to prevent open-redirect SSRF
    )
