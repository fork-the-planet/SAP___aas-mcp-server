"""
OpenAPI spec loader with support for path filtering and overlay application.

Environment Variables (per component):
    AAS_REPO_FILTER_PATHS: Comma-separated list of paths to include for aas-repo
    SUBMODEL_REPO_FILTER_PATHS: Comma-separated list of paths to include for submodel-repo
    CONCEPT_DESCRIPTION_REPO_FILTER_PATHS: Comma-separated list of paths for concept-description-repo
    AAS_REGISTRY_FILTER_PATHS: Comma-separated list of paths to include for aas-registry
    SUBMODEL_REGISTRY_FILTER_PATHS: Comma-separated list of paths to include for submodel-registry

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
    "concept-description-repo": "CONCEPT_DESCRIPTION_REPO_FILTER_PATHS",
    "aas-registry": "AAS_REGISTRY_FILTER_PATHS",
    "submodel-registry": "SUBMODEL_REGISTRY_FILTER_PATHS",
}


def load_openapi_yaml(path: str) -> dict[str, Any]:
    """Load an OpenAPI YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def filter_paths(spec: dict[str, Any], include_paths: list[str]) -> dict[str, Any]:
    """
    Filter OpenAPI spec to include only specified paths.

    Args:
        spec: The OpenAPI specification dict
        include_paths: List of paths to keep (e.g., ['/shells', '/shells/{aasIdentifier}'])

    Returns:
        A new spec with only the specified paths
    """
    result = deepcopy(spec)
    result["paths"] = {
        path: definition
        for path, definition in spec.get("paths", {}).items()
        if path in include_paths
    }
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
        List of paths to include, or None if not set
    """
    env_var = COMPONENT_FILTER_ENV_VARS.get(component_name)
    if not env_var:
        return None

    paths_str = os.getenv(env_var)
    if not paths_str:
        return None

    # Parse comma-separated paths, strip whitespace
    return [p.strip() for p in paths_str.split(",") if p.strip()]


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
