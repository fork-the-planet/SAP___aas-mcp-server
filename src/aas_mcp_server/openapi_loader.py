# SPDX-FileCopyrightText: 2026 SAP SE or an SAP affiliate company and aas-mcp-server contributors
# SPDX-License-Identifier: Apache-2.0

"""
OpenAPI spec loader with support for path filtering and overlay application.

Environment Variables (per component):
    AAS_REPO_FILTER_PATHS: Semicolon-separated list of path filters for aas-repo
    SUBMODEL_REPO_FILTER_PATHS: Semicolon-separated list of path filters for submodel-repo
    AAS_REGISTRY_FILTER_PATHS: Semicolon-separated list of path filters for aas-registry
    SUBMODEL_REGISTRY_FILTER_PATHS: Semicolon-separated list of path filters for submodel-registry

Path Filter Format:
    - "/path" - include all HTTP methods for this path
    - "/path:get" - include only GET method
    - "/path:get,post" - include GET and POST methods
    - Use semicolon (;) to separate multiple path filters

    Examples:
        AAS_REPO_FILTER_PATHS="/shells:get,post;/shells/{aasIdentifier}:get,put,delete"

Overlay files are expected at: openapi/overlays/{component}-overlay.yaml
"""

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from oas_patch import apply_overlay


# Constants for parsing and filtering
FILTER_DELIMITER = ":"
METHOD_SEPARATOR = ","
PATH_FILTER_SEPARATOR = ";"
FILE_ENCODING = "utf-8"

# HTTP methods recognized in OpenAPI specs
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}

# OpenAPI spec structure keys
OPENAPI_KEY_PATHS = "paths"

# Directory and file patterns
DEFAULT_OVERLAY_DIR = "openapi/overlays"
OVERLAY_FILE_PATTERN = "{component_name}-overlay.yaml"

# Mapping of component names to their filter paths env variable names
COMPONENT_FILTER_ENV_VARS = {
    "aas-repo": "AAS_REPO_FILTER_PATHS",
    "submodel-repo": "SUBMODEL_REPO_FILTER_PATHS",
    "aas-registry": "AAS_REGISTRY_FILTER_PATHS",
    "submodel-registry": "SUBMODEL_REGISTRY_FILTER_PATHS",
}


def load_openapi_yaml(path: str) -> dict[str, Any]:
    """Load an OpenAPI YAML file."""
    with open(path, "r", encoding=FILE_ENCODING) as f:
        return yaml.safe_load(f)


def parse_path_filter(filter_str: str) -> tuple[str, list[str] | None]:
    """
    Parse a path filter string into path and methods.

    Format: "/path:method1,method2" or "/path" (all methods)

    Examples:
        "/shells:get,post" -> ("/shells", ["get", "post"])
        "/shells:get" -> ("/shells", ["get"])
        "/shells" -> ("/shells", None)  # None means all methods

    Args:
        filter_str: Filter string like "/shells:get,post" or "/shells"

    Returns:
        Tuple of (path, methods) where methods is None for all methods
    """
    if FILTER_DELIMITER in filter_str:
        path, methods_str = filter_str.rsplit(FILTER_DELIMITER, 1)
        methods = [m.strip().lower() for m in methods_str.split(METHOD_SEPARATOR) if m.strip()]
        return path, methods if methods else None
    return filter_str, None


def _build_path_methods_map(include_filters: list[str]) -> dict[str, set[str] | None]:
    """
    Build a mapping of paths to their allowed methods from filter strings.

    Args:
        include_filters: List of path filter strings

    Returns:
        Dict mapping path to set of methods (or None for all methods)
    """
    path_methods: dict[str, set[str] | None] = {}

    for filter_str in include_filters:
        path, methods = parse_path_filter(filter_str)

        if path not in path_methods:
            path_methods[path] = set(methods) if methods else None
        elif methods is None:
            # If any filter says "all methods", use all methods
            path_methods[path] = None
        elif path_methods[path] is not None:
            # Merge methods if both specify methods
            path_methods[path].update(methods)

    return path_methods


def _filter_path_definition(
    definition: dict[str, Any],
    allowed_methods: set[str] | None,
    http_methods: set[str]
) -> dict[str, Any] | None:
    """
    Filter a path definition to include only allowed methods.

    Args:
        definition: Path definition from OpenAPI spec
        allowed_methods: Set of allowed methods (None = all methods)
        http_methods: Set of valid HTTP method names

    Returns:
        Filtered definition, or None if no methods remain
    """
    if allowed_methods is None:
        # Include all methods
        return definition

    # Include only specified methods
    filtered_definition = {
        key: value
        for key, value in definition.items()
        if key.lower() not in http_methods or key.lower() in allowed_methods
    }

    # Only return if at least one HTTP method remains
    if any(k.lower() in http_methods for k in filtered_definition):
        return filtered_definition

    return None


def filter_paths(spec: dict[str, Any], include_filters: list[str]) -> dict[str, Any]:
    """
    Filter OpenAPI spec to include only specified paths and methods.

    Args:
        spec: The OpenAPI specification dict
        include_filters: List of path filters to keep
            Format: "/path:method1,method2" or "/path" (all methods)
            Examples:
                - "/shells" - include all methods for /shells
                - "/shells:get" - include only GET /shells
                - "/shells:get,post" - include GET and POST /shells

    Returns:
        A new spec with only the specified paths and methods
    """
    result = deepcopy(spec)

    # Parse all filters into a dict: {path: set of methods or None}
    path_methods = _build_path_methods_map(include_filters)

    # Filter paths and methods
    filtered_paths = {}

    for path, definition in spec.get(OPENAPI_KEY_PATHS, {}).items():
        if path not in path_methods:
            continue

        allowed_methods = path_methods[path]
        filtered_definition = _filter_path_definition(definition, allowed_methods, HTTP_METHODS)

        if filtered_definition is not None:
            filtered_paths[path] = filtered_definition

    result[OPENAPI_KEY_PATHS] = filtered_paths
    return result


def get_overlay_path(component_name: str, base_dir: str = DEFAULT_OVERLAY_DIR) -> Path | None:
    """
    Get the overlay file path for a component if it exists.

    Args:
        component_name: Name of the component (e.g., 'aas-repo')
        base_dir: Base directory for overlay files

    Returns:
        Path to overlay file if it exists, None otherwise
    """
    overlay_filename = OVERLAY_FILE_PATTERN.format(component_name=component_name)
    overlay_path = Path(base_dir) / overlay_filename
    if overlay_path.exists():
        return overlay_path
    return None


def get_filter_paths_from_env(component_name: str) -> list[str] | None:
    """
    Get filter paths from environment variable for a component.

    Args:
        component_name: Name of the component (e.g., 'aas-repo')

    Returns:
        List of path filters to include, or None if not set
    """
    env_var = COMPONENT_FILTER_ENV_VARS.get(component_name)
    if not env_var:
        return None

    paths_str = os.getenv(env_var)
    if not paths_str:
        return None

    # Parse semicolon-separated path filters, strip whitespace
    return [p.strip() for p in paths_str.split(PATH_FILTER_SEPARATOR) if p.strip()]


def load_and_process_openapi(
    openapi_path: str,
    component_name: str,
    overlay_base_dir: str = DEFAULT_OVERLAY_DIR,
) -> dict[str, Any]:
    """
    Load OpenAPI spec with optional filtering and overlay application.

    Processing order:
    1. Load the original OpenAPI spec
    2. If filter paths env var is set for this component, filter to those paths
    3. If overlay file exists for this component, apply the overlay

    Args:
        openapi_path: Path to the OpenAPI spec file
        component_name: Name of the component (e.g., 'aas-repo')
        overlay_base_dir: Base directory for overlay files

    Returns:
        Processed OpenAPI specification dict
    """
    # Step 1: Load original spec
    spec = load_openapi_yaml(openapi_path)

    # Step 2: Apply path filtering if env var is set
    filter_paths_list = get_filter_paths_from_env(component_name)
    if filter_paths_list:
        spec = filter_paths(spec, filter_paths_list)

    # Step 3: Apply overlay if it exists
    overlay_path = get_overlay_path(component_name, overlay_base_dir)
    if overlay_path:
        overlay = load_openapi_yaml(str(overlay_path))
        spec = apply_overlay(spec, overlay)

    return spec
