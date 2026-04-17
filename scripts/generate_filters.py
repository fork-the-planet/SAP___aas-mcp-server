#!/usr/bin/env python3
"""
Generate path filter strings for AAS implementation-supported endpoints.

This script computes the intersection of:
1. Paths in the official OpenAPI specs (AAS Repo, Submodel Repo, AAS Registry, Submodel Registry)
2. Paths supported by a specific AAS implementation (e.g., BaSyx, FA³ST)

For each path, it takes the intersection of HTTP methods (only methods in BOTH specs).

Configuration is loaded from YAML files. The configuration file path can be specified via:
1. Command-line argument: --config
2. Environment variable: AAS_IMPLEMENTATION_CONFIG
3. Default: config.yaml.template (users should create their own config)

Output format: Semicolon-separated path filters suitable for generate_derived_spec.py
Example: /shells:get,post;/shells/{aasIdentifier}:get,put,delete

Usage:
    # Use specific configuration
    python3 scripts/generate_filters.py --config configs/my-implementation-config.yaml

    # Use environment variable
    export AAS_IMPLEMENTATION_CONFIG=configs/my-config.yaml
    python3 scripts/generate_filters.py

    # Use BaSyx example
    python3 scripts/generate_filters.py --config configs/basyx-config.example.yaml

    # List available configurations
    python3 scripts/generate_filters.py --list-configs
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)


# Default configuration file path (template - users should create their own)
DEFAULT_CONFIG_PATH = "configs/config.yaml.template"

# Environment variable for configuration path
CONFIG_ENV_VAR = "AAS_IMPLEMENTATION_CONFIG"


def load_openapi_yaml(path: str) -> dict[str, Any]:
    """Load OpenAPI spec from YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def load_openapi_json(path: str) -> dict[str, Any]:
    """Load OpenAPI spec from JSON file."""
    with open(path) as f:
        return json.load(f)


def load_openapi_file(path: str) -> dict[str, Any]:
    """Load OpenAPI spec from YAML or JSON file based on extension."""
    path_obj = Path(path)
    if path_obj.suffix in ['.yaml', '.yml']:
        return load_openapi_yaml(path)
    elif path_obj.suffix == '.json':
        return load_openapi_json(path)
    else:
        raise ValueError(f"Unsupported file extension: {path_obj.suffix}")


def extract_paths_and_methods(spec: dict[str, Any]) -> dict[str, set[str]]:
    """
    Extract paths and their HTTP methods from OpenAPI spec.

    Returns:
        dict mapping path string to set of lowercase method names (e.g., {'get', 'post'})
    """
    result = {}
    for path, operations in spec.get("paths", {}).items():
        methods = {
            method.lower()
            for method in operations.keys()
            if method.lower() in {"get", "post", "put", "patch", "delete"}
        }
        if methods:
            result[path] = methods
    return result


def compute_intersection(
    official_paths: dict[str, set[str]], implementation_paths: dict[str, set[str]]
) -> dict[str, set[str]]:
    """
    Compute the intersection of paths and methods.

    Only includes paths that exist in BOTH specs.
    For each path, only includes methods that exist in BOTH specs.

    Returns:
        dict mapping path to set of methods that exist in both specs
    """
    intersection = {}
    for path in set(official_paths.keys()) & set(implementation_paths.keys()):
        common_methods = official_paths[path] & implementation_paths[path]
        if common_methods:
            intersection[path] = common_methods
    return intersection


def format_filter_string(paths_methods: dict[str, set[str]]) -> str:
    """
    Format paths and methods as a filter string for generate_derived_spec.py.

    Format: /path:method1,method2;/path2:method3
    """
    parts = []
    for path in sorted(paths_methods.keys()):
        methods = sorted(paths_methods[path])
        parts.append(f"{path}:{','.join(methods)}")
    return ";".join(parts)


def filter_by_prefix(paths_methods: dict[str, set[str]], prefix: str | None) -> dict[str, set[str]]:
    """
    Filter paths to only those starting with the given prefix.

    If prefix is None, return all paths.
    """
    if prefix is None:
        return paths_methods
    return {path: methods for path, methods in paths_methods.items() if path.startswith(prefix)}


def load_config(config_path: str | None) -> dict[str, Any]:
    """
    Load configuration from YAML file.

    Priority:
    1. Command-line argument (--config)
    2. Environment variable (AAS_IMPLEMENTATION_CONFIG)
    3. Default (configs/basyx-config.yaml)

    Args:
        config_path: Path to configuration file from command-line, or None

    Returns:
        Configuration dictionary
    """
    # Determine config path with priority
    if config_path is None:
        config_path = os.getenv(CONFIG_ENV_VAR, DEFAULT_CONFIG_PATH)

        if os.getenv(CONFIG_ENV_VAR):
            logging.info(f"Using configuration from environment variable {CONFIG_ENV_VAR}")
        else:
            logging.info(f"Using default configuration")

    if not Path(config_path).exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please create a configuration file or use --list-configs to see available configurations.\n"
            f"You can set the configuration via:\n"
            f"  1. Command-line: --config <path>\n"
            f"  2. Environment: export {CONFIG_ENV_VAR}=<path>\n"
            f"  3. Default location: {DEFAULT_CONFIG_PATH}"
        )

    logging.info(f"Loading configuration from: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


def list_available_configs():
    """List available configuration files in the configs/ directory."""
    configs_dir = Path("configs")
    if not configs_dir.exists():
        logging.error("No configs/ directory found.")
        logging.info("\nPlease create a configs/ directory with configuration files.")
        logging.info("See config.yaml.template and basyx-config.example.yaml for examples.")
        return

    config_files = list(configs_dir.glob("*.yaml")) + list(configs_dir.glob("*.yml"))
    if not config_files:
        logging.error("No configuration files found in configs/ directory.")
        logging.info("\nPlease create a configuration file in configs/")
        logging.info("See config.yaml.template and basyx-config.example.yaml for examples.")
        return

    logging.info("Available configurations in configs/:")
    for config_file in sorted(config_files):
        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)
                name = config.get('name', config_file.stem)
                version = config.get('version', 'unknown')
                is_default = str(config_file) == DEFAULT_CONFIG_PATH
                default_marker = " (default)" if is_default else ""
                logging.info(f"  - {config_file}: {name} {version}{default_marker}")
        except Exception as e:
            logging.warning(f"  - {config_file}: (error reading: {e})")

    logging.info(f"\nDefault configuration: {DEFAULT_CONFIG_PATH}")
    logging.info(f"Environment variable: {CONFIG_ENV_VAR}")

    current_env = os.getenv(CONFIG_ENV_VAR)
    if current_env:
        logging.info(f"Currently set to: {current_env}")
    else:
        logging.info(f"Currently not set (will use default)")


def process_component(
    component_config: dict[str, Any]
) -> tuple[dict[str, set[str]], str]:
    """
    Process a single component and return intersection and filter string.

    Returns:
        Tuple of (intersection dict, filter string)
    """
    # Load implementation spec
    impl_spec_path = component_config["implementation_spec"]
    logging.debug(f"  Loading implementation spec: {impl_spec_path}")
    impl_spec = load_openapi_file(impl_spec_path)
    impl_paths = extract_paths_and_methods(impl_spec)

    # Load official spec
    official_spec_path = component_config["official_spec"]
    logging.debug(f"  Loading official spec: {official_spec_path}")
    official_spec = load_openapi_yaml(official_spec_path)
    official_paths = extract_paths_and_methods(official_spec)

    # Apply path prefix filter if specified
    path_prefix = component_config.get("path_prefix")
    if path_prefix:
        impl_paths = filter_by_prefix(impl_paths, path_prefix)
        official_paths = filter_by_prefix(official_paths, path_prefix)

    # Compute intersection
    intersection = compute_intersection(official_paths, impl_paths)

    # Generate filter string
    filter_string = format_filter_string(intersection)

    return intersection, filter_string


def main():
    parser = argparse.ArgumentParser(
        description="Generate filter path strings for AAS implementation endpoints.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        help="Path to implementation configuration file (default: built-in BaSyx config)",
    )
    parser.add_argument(
        "--list-configs",
        action="store_true",
        help="List available configuration files",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(args.log_level)

    # Handle --list-configs
    if args.list_configs:
        list_available_configs()
        return

    # Load configuration
    config = load_config(args.config)
    config_name = config.get("name", "Unknown")
    config_version = config.get("version", "")

    logging.info("=" * 80)
    logging.info(f"AAS IMPLEMENTATION-SUPPORTED ENDPOINTS ANALYSIS")
    logging.info(f"Implementation: {config_name} {config_version}")
    logging.info("=" * 80)

    # Process each component
    results = {}
    for component_name, component_config in config["components"].items():
        logging.info(f"\n[{component_name.upper().replace('-', ' ')}]")

        try:
            intersection, filter_string = process_component(component_config)

            logging.info(f"  Intersection: {len(intersection)} paths")
            logging.info("\n  Intersection details:")
            for path in sorted(intersection.keys()):
                methods = sorted(intersection[path])
                logging.info(f"    {path}: {methods}")

            # Store results
            env_var = f"{component_name.upper().replace('-', '_')}_FILTER_PATHS"
            results[component_name] = {
                "env_var": env_var,
                "filter_string": filter_string,
                "path_count": len(intersection),
                "operation_count": sum(len(methods) for methods in intersection.values())
            }

            logging.info(f"\n  Filter string for {component_name}:")
            logging.info(f"    export {env_var}=\"{filter_string}\"")

        except Exception as e:
            logging.error(f"  Failed to process {component_name}: {e}")
            continue

    # Summary
    logging.info("\n" + "=" * 80)
    logging.info("SUMMARY - Copy these export commands:")
    logging.info("=" * 80)
    for component_name, result in results.items():
        logging.info(f'export {result["env_var"]}="{result["filter_string"]}"')

    logging.info("=" * 80)
    logging.info("\nStatistics:")
    for component_name, result in results.items():
        logging.info(f"  {component_name}: {result['path_count']} paths, {result['operation_count']} operations")
    logging.info("=" * 80)


if __name__ == "__main__":
    main()
