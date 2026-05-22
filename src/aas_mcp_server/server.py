# SPDX-FileCopyrightText: 2026 SAP SE or an SAP affiliate company and aas-mcp-server contributors
# SPDX-License-Identifier: Apache-2.0

"""
MCP server builder for AAS components.

This module orchestrates the complete MCP server construction pipeline:
1. Process OpenAPI specification (derive from config + apply overlay)
2. Curate the spec for safe tool generation (allowlist, read-only by default)
3. Build HTTP client (no static auth — OAuth token is forwarded per-request)
4. Build FastMCP RemoteAuthProvider if OAuth is configured
5. Generate FastMCP server from curated OpenAPI spec

## Audience validation

OAUTH_AUDIENCE is always optional. When not set, a WARNING is logged at
startup because audience validation is disabled. Operators who want strict
audience enforcement should set OAUTH_AUDIENCE. Those who don't — including
test/dev environments and setups where the OAuth provider and AAS backend
share the same trust domain — can leave it unset.

There is no automatic hard-failure based on bind address or other runtime
signals. Such heuristics proved too fragile: Docker containers routinely bind
on 0.0.0.0 regardless of whether they are test or production, and using
OAUTH_SERVER_BASE_URL as a signal penalises operators who set it for the
correct reason (RFC 9728 metadata accuracy behind a reverse proxy).
"""

import logging
import math
import os

from fastmcp import FastMCP
from fastmcp.server.auth import JWTVerifier, RemoteAuthProvider
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from pydantic import AnyHttpUrl

from .config import ComponentConfig
from .spec_processor import process_component_spec
from .schema_flattener import flatten_spec_schemas
from .http_client import build_async_client
from .tool_curation import curate_openapi_spec, prune_unused_schemas
from .logging import configure_logging
from .constants import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    JWKS_WELL_KNOWN_PATH,
    LOCALHOST_ADDRESSES,
    SECONDS_PER_MINUTE,
    SERVER_NAME_FORMAT,
    WILDCARD_BIND_ADDRESSES,
    ENV_OAUTH_ISSUER_URL,
    ENV_OAUTH_AUDIENCE,
    ENV_OAUTH_REQUIRED_SCOPES,
    ENV_OAUTH_JWKS_URI,
    ENV_OAUTH_SERVER_BASE_URL,
    ENV_MCP_RATE_LIMIT_PER_MINUTE,
)

logger = logging.getLogger(__name__)

HTTP_TRANSPORTS = frozenset({"http", "sse", "streamable-http"})
SCOPES_DELIMITER = ","


def _parse_positive_int(env_var: str, default: int) -> int:
    """
    Read an environment variable as a positive integer.

    Raises ValueError with an actionable message if the value is not a
    valid integer or is less than 1.
    """
    raw = os.getenv(env_var, str(default))
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"Invalid value for {env_var}: {raw!r} is not an integer. "
            f"Provide a positive integer (default: {default})."
        )
    if value < 1:
        raise ValueError(
            f"Invalid value for {env_var}: {value} is not allowed. "
            f"Value must be >= 1 (default: {default})."
        )
    return value


def _parse_positive_float(env_var: str, default: float) -> float:
    """
    Read an environment variable as a positive finite float.

    Raises ValueError with an actionable message if the value is not a
    valid finite float or is not greater than 0. Explicitly rejects nan
    and inf which float() accepts but which produce undefined behaviour.
    """
    raw = os.getenv(env_var, str(default))
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(
            f"Invalid value for {env_var}: {raw!r} is not a number. "
            f"Provide a positive finite number (default: {default})."
        )
    if not math.isfinite(value) or value <= 0:
        raise ValueError(
            f"Invalid value for {env_var}: {value!r} is not allowed. "
            f"Value must be a positive finite number (default: {default})."
        )
    return value


def _build_jwt_verifier_from_env() -> JWTVerifier | None:
    """
    Build a JWTVerifier from environment variables, or return None.

    Returns None when OAUTH_ISSUER_URL is not set (auth disabled).

    OAUTH_AUDIENCE is optional. When absent, audience validation is disabled
    and a WARNING is emitted. This is intentional: blocking startup on a
    missing audience is too aggressive for containerised test/dev environments
    where Docker bind addresses (0.0.0.0) cannot reliably distinguish test
    from production. Operators who need strict audience enforcement should set
    OAUTH_AUDIENCE explicitly.
    """
    issuer_url = os.getenv(ENV_OAUTH_ISSUER_URL)
    if not issuer_url:
        return None

    audience = os.getenv(ENV_OAUTH_AUDIENCE)
    if not audience:
        logger.warning(
            "OAUTH_ISSUER_URL is set but OAUTH_AUDIENCE is not. "
            "Audience validation is DISABLED — tokens intended for other resource "
            "servers may be accepted. Set OAUTH_AUDIENCE to the expected audience "
            "value (must match what the AAS backend also accepts)."
        )

    scopes_raw = os.getenv(ENV_OAUTH_REQUIRED_SCOPES)
    required_scopes: list[str] | None = None
    if scopes_raw:
        required_scopes = [
            s.strip() for s in scopes_raw.split(SCOPES_DELIMITER) if s.strip()
        ]

    explicit_jwks = os.getenv(ENV_OAUTH_JWKS_URI)
    jwks_uri = explicit_jwks or f"{issuer_url.rstrip('/')}{JWKS_WELL_KNOWN_PATH}"

    return JWTVerifier(
        jwks_uri=jwks_uri,
        issuer=issuer_url,
        audience=audience,
        required_scopes=required_scopes,
    )


def build_jwt_verifier() -> JWTVerifier | None:
    """
    Return a JWTVerifier built from environment variables, or None.

    Public wrapper retained for backward-compatibility with tests.
    Production server construction uses build_auth_provider() which wraps
    this in a RemoteAuthProvider to also serve the RFC 9728 discovery endpoint.
    """
    return _build_jwt_verifier_from_env()


def build_auth_provider(
    host: str,
    port: int,
) -> RemoteAuthProvider | None:
    """
    Build a FastMCP RemoteAuthProvider from environment variables, or return None.

    RemoteAuthProvider wraps a JWTVerifier (for token validation) and also
    serves the /.well-known/oauth-protected-resource/mcp endpoint (RFC 9728).
    This endpoint tells MCP clients which authorization server issues valid
    tokens, allowing them to perform the PKCE browser flow automatically.

    Returns None when OAUTH_ISSUER_URL is not set (auth disabled).
    """
    jwt_verifier = _build_jwt_verifier_from_env()
    if jwt_verifier is None:
        return None

    issuer_url = os.getenv(ENV_OAUTH_ISSUER_URL)  # already validated non-None above

    # Derive the MCP server's public base URL for the RFC 9728 metadata endpoint.
    # OAUTH_SERVER_BASE_URL can be set explicitly for reverse-proxy deployments
    # where the bind address (0.0.0.0) differs from the public-facing URL.
    # When constructing from host:port, use https:// for non-localhost hosts.
    explicit_base = os.getenv(ENV_OAUTH_SERVER_BASE_URL)

    # Warn when OAuth is active but the bind host is a wildcard address and no
    # explicit public URL has been provided. The derived metadata URL would be
    # e.g. https://0.0.0.0:8000 — not client-reachable, which silently breaks
    # the PKCE discovery flow for MCP clients.
    if not explicit_base and host in WILDCARD_BIND_ADDRESSES:
        logger.warning(
            "OAuth is enabled and MCP_HOST is a wildcard address (%s) but "
            "OAUTH_SERVER_BASE_URL is not set. The OAuth resource metadata will "
            "advertise an unreachable URL (%s:%s), which may break the PKCE "
            "authentication flow for MCP clients. "
            "Set OAUTH_SERVER_BASE_URL to the public-facing URL of this server, "
            "e.g. OAUTH_SERVER_BASE_URL=http://localhost:8000",
            host,
            host,
            port,
        )

    is_localhost_bind = host in LOCALHOST_ADDRESSES
    if explicit_base:
        server_base_url = explicit_base
    elif is_localhost_bind:
        formatted_host = f"[{host}]" if ":" in host else host
        server_base_url = f"http://{formatted_host}:{port}"
    else:
        formatted_host = f"[{host}]" if ":" in host else host
        server_base_url = f"https://{formatted_host}:{port}"

    logger.info(
        "OAuth 2.1 inbound auth enabled: issuer=%s, audience=%s, "
        "scopes=%s, jwks_uri=%s, server_base_url=%s",
        issuer_url,
        os.getenv(ENV_OAUTH_AUDIENCE) or "<not set>",
        jwt_verifier.required_scopes or "<not set>",
        jwt_verifier.jwks_uri,
        server_base_url,
    )

    return RemoteAuthProvider(
        token_verifier=jwt_verifier,
        authorization_servers=[AnyHttpUrl(issuer_url)],
        base_url=server_base_url,
    )


def build_mcp_server(
    component_config: ComponentConfig,
    base_url: str,
    enable_writes: bool,
    log_level: str = DEFAULT_LOG_LEVEL,
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> FastMCP:
    """
    Build and configure an MCP server for AAS components.

    Args:
        component_config: Component configuration from config.yaml
        base_url: Base URL of the AAS backend server
        enable_writes: Whether to enable write operations (POST/PUT/PATCH/DELETE)
        log_level: Logging level (default: INFO)
        transport: MCP transport type ('stdio', 'http', 'sse', etc.)
        host: Host the server will bind to (used for TLS warning and base URL)
        port: Port the server will bind to (used for base URL construction)

    Returns:
        Configured FastMCP server instance
    """
    configure_logging(log_level, transport=transport)

    # Warn when OAuth is active over plain HTTP on a non-localhost bind address
    if os.getenv(ENV_OAUTH_ISSUER_URL) and transport in HTTP_TRANSPORTS:
        if host not in LOCALHOST_ADDRESSES:
            logger.warning(
                "OAuth is enabled but TLS termination cannot be verified. "
                "All authorization endpoints MUST be served over HTTPS in "
                "production. Ensure a TLS-terminating reverse proxy is in place."
            )

    # Process spec according to config (derive + apply overlay)
    spec = process_component_spec(component_config)

    # Resolve $refs and flatten allOf so FastMCP sees plain schemas
    spec = flatten_spec_schemas(spec)

    # Curate tool surface area (rename, filter, readonly-by-default)
    curated = curate_openapi_spec(
        spec, enable_writes=enable_writes, curation_settings=component_config.curation
    )

    # Remove schemas no longer reachable from the curated paths
    curated = prune_unused_schemas(curated)

    # Build HTTP client (no static auth — token forwarding via BearerTokenAuth)
    client = build_async_client(base_url=base_url)

    # Build auth provider (None when OAuth not configured)
    auth_provider = build_auth_provider(host=host, port=port)

    # Configure rate limiting (convert per-minute to per-second for token bucket)
    rate_limit = _parse_positive_int(
        ENV_MCP_RATE_LIMIT_PER_MINUTE, DEFAULT_RATE_LIMIT_PER_MINUTE
    )
    rate_limiter = RateLimitingMiddleware(
        max_requests_per_second=rate_limit / SECONDS_PER_MINUTE,
        burst_capacity=rate_limit,
    )

    # Generate MCP server from OpenAPI.
    # mask_error_details=True prevents internal backend error messages (stack
    # traces, AAS backend URLs, internal hostnames) from leaking to MCP clients.
    mcp = FastMCP.from_openapi(
        openapi_spec=curated,
        client=client,
        name=SERVER_NAME_FORMAT.format(component_name=component_config.component_name),
        auth=auth_provider,
        middleware=[rate_limiter],
        mask_error_details=True,
    )

    return mcp
