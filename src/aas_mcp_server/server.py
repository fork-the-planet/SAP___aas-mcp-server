from fastmcp import FastMCP
from .openapi_loader import load_and_process_openapi
from .http_client import build_async_client
from .tool_curation import curate_openapi_spec
from .logging import configure_logging

def build_mcp_server(
        base_url: str,
        openapi_path: str,
        enable_writes: bool,
        log_level: str = "INFO",
        component_name: str = "aas-repo",
) -> FastMCP:
    configure_logging(log_level)

    # Load spec with optional filtering (via env var) and overlay application
    spec = load_and_process_openapi(openapi_path, component_name)

    # Curate tool surface area (rename, filter, readonly-by-default)
    curated = curate_openapi_spec(spec, enable_writes=enable_writes)

    client = build_async_client(base_url=base_url)

    # FastMCP can generate an MCP server from OpenAPI directly
    # (tools + schemas are derived from OpenAPI operations). :contentReference[oaicite:2]{index=2}
    mcp = FastMCP.from_openapi(
        openapi_spec=curated,
        client=client,
        name=f"AAS MCP Server ({component_name})",
    )

    return mcp