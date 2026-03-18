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


# Mapping of component names to their filter paths env variable names
COMPONENT_FILTER_ENV_VARS = {
    "aas-repo": "AAS_REPO_FILTER_PATHS",
    "submodel-repo": "SUBMODEL_REPO_FILTER_PATHS",
    "aas-registry": "AAS_REGISTRY_FILTER_PATHS",
    "submodel-registry": "SUBMODEL_REGISTRY_FILTER_PATHS",
}


def load_openapi_yaml(path: str) -> dict[str, Any]:
    """Load an OpenAPI YAML file."""
    with open(path, "r", encoding="utf-8") as f:
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
    if ":" in filter_str:
        path, methods_str = filter_str.rsplit(":", 1)
        methods = [m.strip().lower() for m in methods_str.split(",") if m.strip()]
        return path, methods if methods else None
    return filter_str, None


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
    path_methods: dict[str, set[str] | None] = {}
    for filter_str in include_filters:
        path, methods = parse_path_filter(filter_str)
        if path not in path_methods:
            path_methods[path] = set(methods) if methods else None
        elif path_methods[path] is not None and methods is not None:
            # Merge methods if both specify methods
            path_methods[path].update(methods)
        elif methods is None:
            # If any filter says "all methods", use all methods
            path_methods[path] = None

    # Filter paths and methods
    filtered_paths = {}
    http_methods = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}

    for path, definition in spec.get("paths", {}).items():
        if path not in path_methods:
            continue

        allowed_methods = path_methods[path]
        if allowed_methods is None:
            # Include all methods
            filtered_paths[path] = definition
        else:
            # Include only specified methods
            filtered_definition = {
                key: value
                for key, value in definition.items()
                if key.lower() not in http_methods or key.lower() in allowed_methods
            }
            if any(k.lower() in http_methods for k in filtered_definition):
                filtered_paths[path] = filtered_definition

    result["paths"] = filtered_paths
    return result


def get_overlay_path(component_name: str, base_dir: str = "openapi/overlays") -> Path | None:
    """
    Get the overlay file path for a component if it exists.

    Args:
        component_name: Name of the component (e.g., 'aas-repo')
        base_dir: Base directory for overlay files

    Returns:
        Path to overlay file if it exists, None otherwise
    """
    overlay_path = Path(base_dir) / f"{component_name}-overlay.yaml"
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
    return [p.strip() for p in paths_str.split(";") if p.strip()]


def load_and_process_openapi(
    openapi_path: str,
    component_name: str,
    overlay_base_dir: str = "openapi/overlays",
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
