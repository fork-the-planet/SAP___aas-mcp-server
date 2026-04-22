# SPDX-FileCopyrightText: 2026 SAP SE or an SAP affiliate company and aas-mcp-server contributors
# SPDX-License-Identifier: Apache-2.0

"""
Command-line interface for AAS MCP Server.

This module provides the main CLI entry point for running the AAS MCP server.
It handles argument parsing, configuration loading, and server initialization.

Supports multiple AAS components:
- aas-repo: Asset Administration Shell Repository
- submodel-repo: Submodel Repository
- aas-registry: AAS Registry
- submodel-registry: Submodel Registry

Each component can be configured via command-line arguments or environment variables.
"""

import argparse
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import yaml

from .server import build_mcp_server

# Constants for environment variables
ENV_VAR_MCP_TRANSPORT = "MCP_TRANSPORT"
ENV_VAR_AAS_MCP_ENABLE_WRITES = "AAS_MCP_ENABLE_WRITES"
ENV_VAR_LOG_LEVEL = "LOG_LEVEL"
ENV_VAR_AAS_BASE_URL = "AAS_BASE_URL"
ENV_VAR_AAS_OPENAPI_PATH = "AAS_OPENAPI_PATH"
ENV_VAR_AAS_IMPLEMENTATION_CONFIG = "AAS_IMPLEMENTATION_CONFIG"

# Constants for default values
DEFAULT_TRANSPORT = "stdio"
DEFAULT_LOG_LEVEL = "INFO"
ENABLE_WRITES_TRUE_VALUE = "1"

# Constants for CLI program
CLI_PROGRAM_NAME = "aas-mcp-server"
CLI_DESCRIPTION = "AAS MCP Server (OpenAPI → MCP) - Support for multiple AAS components"

# Constants for argument names
ARG_COMPONENT = "--component"
ARG_BASE_URL = "--base-url"
ARG_OPENAPI = "--openapi"
ARG_CONFIG = "--config"
ARG_TRANSPORT = "--transport"
ARG_ENABLE_WRITES = "--enable-writes"
ARG_LOG_LEVEL = "--log-level"

# Constants for component configuration keys
CONFIG_KEY_OPENAPI = "openapi"
CONFIG_KEY_DEFAULT_URL = "default_url"
CONFIG_KEY_DESCRIPTION = "description"

# Component-to-OpenAPI mapping
# By default, uses official AAS specifications (full, unfiltered)
# Users can override with --openapi flag to use derived specs or custom specs
COMPONENT_CONFIGS = {
    "aas-repo": {
        CONFIG_KEY_OPENAPI: "openapi/AssetAdministrationShellRepositoryServiceSpecification-V3.1.1_SSP-001-resolved.yaml",
        CONFIG_KEY_DEFAULT_URL: "http://localhost:8080",
        CONFIG_KEY_DESCRIPTION: "AAS Repository - Manage Asset Administration Shells",
    },
    "submodel-repo": {
        CONFIG_KEY_OPENAPI: "openapi/SubmodelRepositoryServiceSpecification-V3.1.1_SSP-001-resolved.yaml",
        CONFIG_KEY_DEFAULT_URL: "http://localhost:8081",
        CONFIG_KEY_DESCRIPTION: "Submodel Repository - Manage Submodels",
    },
    "aas-registry": {
        CONFIG_KEY_OPENAPI: "openapi/AssetAdministrationShellRegistryServiceSpecification-V3.1.1_SSP-001-resolved.yaml",
        CONFIG_KEY_DEFAULT_URL: "http://localhost:8083",
        CONFIG_KEY_DESCRIPTION: "AAS Registry - Discover and register AAS components",
    },
    "submodel-registry": {
        CONFIG_KEY_OPENAPI: "openapi/SubmodelRegistryServiceSpecification-V3.1.1_SSP-001-resolved.yaml",
        CONFIG_KEY_DEFAULT_URL: "http://localhost:8084",
        CONFIG_KEY_DESCRIPTION: "Submodel Registry - Discover and register Submodels",
    },
}

def load_curation_from_config(config_path: Optional[str], component_name: str) -> Optional[Dict[str, Any]]:
    """
    Load curation settings from configuration file.

    Args:
        config_path: Path to configuration YAML file
        component_name: Name of the component (e.g., "aas-repo")

    Returns:
        Dictionary with curation settings (allowlist, aliases) or None if not found
    """
    if not config_path:
        return None

    config_file = Path(config_path)
    if not config_file.exists():
        return None

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if not config:
            return None

        # Navigate to component-specific curation settings
        components = config.get('components', {})
        component_config = components.get(component_name, {})
        curation = component_config.get('curation')

        if not curation:
            return None

        # Convert allowlist from list format to set of tuples
        result: Dict[str, Any] = {}

        if 'allowlist' in curation:
            allowlist_raw = curation['allowlist']
            if isinstance(allowlist_raw, list):
                # Convert [[method, path], ...] to {(method, path), ...}
                result['allowlist'] = {
                    (tuple(item) if isinstance(item, list) else item)
                    for item in allowlist_raw
                }

        if 'aliases' in curation:
            result['aliases'] = dict(curation['aliases'])

        return result if result else None

    except Exception:
        # Silently fail - will use defaults
        return None

def main() -> None:
    """
    Main entry point for the AAS MCP Server CLI.

    Parses command-line arguments, loads component configuration,
    builds the MCP server, and starts it with the specified transport.

    The function handles:
    - Argument parsing and validation
    - Configuration resolution (CLI args > env vars > defaults)
    - MCP server initialization
    - Server execution

    Exits:
        The function runs the MCP server and does not return.
    """
    p = argparse.ArgumentParser(
        prog=CLI_PROGRAM_NAME,
        description=CLI_DESCRIPTION
    )
    p.add_argument(
        ARG_COMPONENT,
        required=True,
        choices=list(COMPONENT_CONFIGS.keys()),
        help="AAS component to serve"
    )
    p.add_argument(
        ARG_BASE_URL,
        help="Base URL for the component API (overrides component default)"
    )
    p.add_argument(
        ARG_OPENAPI,
        help="Custom OpenAPI spec path (overrides component default)"
    )
    p.add_argument(
        ARG_CONFIG,
        help="Path to implementation config file (for loading curation settings)"
    )
    p.add_argument(
        ARG_TRANSPORT,
        default=os.getenv(ENV_VAR_MCP_TRANSPORT, DEFAULT_TRANSPORT),
        choices=[DEFAULT_TRANSPORT]
    )
    p.add_argument(
        ARG_ENABLE_WRITES,
        action="store_true",
        default=os.getenv(ENV_VAR_AAS_MCP_ENABLE_WRITES) == ENABLE_WRITES_TRUE_VALUE
    )
    p.add_argument(
        ARG_LOG_LEVEL,
        default=os.getenv(ENV_VAR_LOG_LEVEL, DEFAULT_LOG_LEVEL)
    )

    args = p.parse_args()

    # Get component configuration
    component_config = COMPONENT_CONFIGS[args.component]

    # Use provided values or fall back to component defaults
    base_url = (
        args.base_url
        or os.getenv(ENV_VAR_AAS_BASE_URL)
        or component_config[CONFIG_KEY_DEFAULT_URL]
    )
    openapi_path = (
        args.openapi
        or os.getenv(ENV_VAR_AAS_OPENAPI_PATH)
        or component_config[CONFIG_KEY_OPENAPI]
    )

    # Load curation settings from config file if provided
    config_path = args.config or os.getenv(ENV_VAR_AAS_IMPLEMENTATION_CONFIG)
    curation_settings = load_curation_from_config(config_path, args.component)

    mcp = build_mcp_server(
        base_url=base_url,
        openapi_path=openapi_path,
        enable_writes=args.enable_writes,
        log_level=args.log_level,
        component_name=args.component,
        curation_settings=curation_settings,
    )
    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main()
