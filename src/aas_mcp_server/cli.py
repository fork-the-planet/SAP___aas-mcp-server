import argparse
import os
from .server import build_mcp_server

# Component-to-OpenAPI mapping
COMPONENT_CONFIGS = {
    "aas-repo": {
        "openapi": "openapi/derived/AssetAdministrationShellRepositoryServiceSpecification-V3.1.1_SSP-001-resolved-derived.yaml",
        "default_url": "http://localhost:8080",
        "description": "AAS Repository - Manage Asset Administration Shells",
    },
    "submodel-repo": {
        "openapi": "openapi/derived/SubmodelRepositoryServiceSpecification-V3.1.1_SSP-001-resolved-derived.yaml",
        "default_url": "http://localhost:8081",
        "description": "Submodel Repository - Manage Submodels",
    },
    "aas-registry": {
        "openapi": "openapi/AssetAdministrationShellRegistryServiceSpecification-V3.1.1_SSP-001-resolved.yaml",
        "default_url": "http://localhost:8083",
        "description": "AAS Registry - Discover and register AAS components",
    },
    "submodel-registry": {
        "openapi": "openapi/SubmodelRegistryServiceSpecification-V3.1.1_SSP-001-resolved.yaml",
        "default_url": "http://localhost:8084",
        "description": "Submodel Registry - Discover and register Submodels",
    },
}

def main() -> None:
    p = argparse.ArgumentParser(
        prog="aas-mcp-server",
        description="AAS MCP Server (OpenAPI → MCP) - Support for multiple AAS components"
    )
    p.add_argument(
        "--component",
        required=True,
        choices=list(COMPONENT_CONFIGS.keys()),
        help="AAS component to serve"
    )
    p.add_argument(
        "--base-url",
        help="Base URL for the component API (overrides component default)"
    )
    p.add_argument(
        "--openapi",
        help="Custom OpenAPI spec path (overrides component default)"
    )
    p.add_argument(
        "--transport",
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        choices=["stdio"]
    )
    p.add_argument(
        "--enable-writes",
        action="store_true",
        default=os.getenv("AAS_MCP_ENABLE_WRITES") == "1"
    )
    p.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO")
    )

    args = p.parse_args()

    # Get component configuration
    component_config = COMPONENT_CONFIGS[args.component]

    # Use provided values or fall back to component defaults
    base_url = args.base_url or os.getenv("AAS_BASE_URL") or component_config["default_url"]
    openapi_path = args.openapi or os.getenv("AAS_OPENAPI_PATH") or component_config["openapi"]

    mcp = build_mcp_server(
        base_url=base_url,
        openapi_path=openapi_path,
        enable_writes=args.enable_writes,
        log_level=args.log_level,
        component_name=args.component,
    )
    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main()
