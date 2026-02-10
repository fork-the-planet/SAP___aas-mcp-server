import argparse
import os
from .server import build_mcp_server

def main() -> None:
    p = argparse.ArgumentParser(prog="aas-mcp-server", description="AAS MCP Server (OpenAPI → MCP)")
    p.add_argument("--base-url", default=os.getenv("AAS_BASE_URL", "http://localhost:8080"))
    p.add_argument("--openapi", default=os.getenv("AAS_OPENAPI_PATH", "openapi/openapi.resolved.yaml"))
    p.add_argument("--transport", default=os.getenv("MCP_TRANSPORT", "stdio"), choices=["stdio"])
    p.add_argument("--enable-writes", action="store_true", default=os.getenv("AAS_MCP_ENABLE_WRITES") == "1")
    p.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))

    args = p.parse_args()

    mcp = build_mcp_server(
        base_url=args.base_url,
        openapi_path=args.openapi,
        enable_writes=args.enable_writes,
        log_level=args.log_level,
    )
    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main()
