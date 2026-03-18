#!/usr/bin/env python
"""
Generate a derived OpenAPI spec with path filtering and overlay applied.

This script allows you to manually verify the filtered and overlay-applied spec.

Path Filter Format:
    - "/path" - include all HTTP methods for this path
    - "/path:get" - include only GET method
    - "/path:get,post" - include GET and POST methods
    - Use semicolon (;) to separate multiple path filters

Usage:
    # Using environment variables
    export AAS_REPO_FILTER_PATHS="/shells:get,post;/shells/{aasIdentifier}:get"
    python scripts/generate_derived_spec.py --component aas-repo

    # Or with command-line arguments (include only GET /shells)
    python scripts/generate_derived_spec.py \
        --component aas-repo \
        --filter-paths "/shells:get"

    # Include GET and POST for /shells, only GET for /shells/{aasIdentifier}
    python scripts/generate_derived_spec.py \
        --component aas-repo \
        --filter-paths "/shells:get,post;/shells/{aasIdentifier}:get"

    # Include all methods for a path
    python scripts/generate_derived_spec.py \
        --component aas-repo \
        --filter-paths "/shells;/shells/{aasIdentifier}"
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml
from aas_mcp_server.openapi_loader import (
    load_openapi_yaml,
    filter_paths,
    COMPONENT_FILTER_ENV_VARS,
)
from oas_patch import apply_overlay


# Component to OpenAPI spec mapping
COMPONENT_SPECS = {
    "aas-repo": "openapi/AssetAdministrationShellRepositoryServiceSpecification-V3.1.1_SSP-001-resolved.yaml",
    "submodel-repo": "openapi/SubmodelRepositoryServiceSpecification-V3.1.1_SSP-001-resolved.yaml",
    "aas-registry": "openapi/AssetAdministrationShellRegistryServiceSpecification-V3.1.1_SSP-001-resolved.yaml",
    "submodel-registry": "openapi/SubmodelRegistryServiceSpecification-V3.1.1_SSP-001-resolved.yaml",
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate a derived OpenAPI spec with filtering and overlay applied.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--component",
        required=True,
        choices=list(COMPONENT_SPECS.keys()),
        help="Component to process",
    )
    parser.add_argument(
        "--filter-paths",
        help="Comma-separated list of paths to include (overrides env var)",
    )
    parser.add_argument(
        "--overlay",
        help="Path to overlay YAML file (default: openapi/overlays/{component}-overlay.yaml)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: openapi/derived/{component}-derived.yaml)",
    )
    parser.add_argument(
        "--spec",
        help="Path to source OpenAPI spec (overrides default for component)",
    )
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Skip overlay application even if overlay file exists",
    )

    args = parser.parse_args()

    # Determine source spec
    spec_path = args.spec or COMPONENT_SPECS[args.component]
    if not Path(spec_path).exists():
        print(f"Error: Source spec not found: {spec_path}")
        sys.exit(1)

    # Determine filter paths (CLI arg > env var) - semicolon separated
    filter_paths_list = None
    if args.filter_paths:
        filter_paths_list = [p.strip() for p in args.filter_paths.split(";") if p.strip()]
    else:
        env_var = COMPONENT_FILTER_ENV_VARS.get(args.component)
        if env_var and os.getenv(env_var):
            filter_paths_list = [p.strip() for p in os.getenv(env_var).split(";") if p.strip()]

    # Determine overlay path
    overlay_path = None
    if not args.no_overlay:
        if args.overlay:
            overlay_path = Path(args.overlay)
        else:
            default_overlay = Path(f"openapi/overlays/{args.component}-overlay.yaml")
            if default_overlay.exists():
                overlay_path = default_overlay

    # Determine output path - default to original filename with -derived suffix
    if args.output:
        output_path = Path(args.output)
    else:
        # Get original filename and add -derived suffix before extension
        original_filename = Path(spec_path).stem  # filename without extension
        output_path = Path(f"openapi/derived/{original_filename}-derived.yaml")

    # Print configuration
    print("=" * 60)
    print("Configuration:")
    print(f"  Component:     {args.component}")
    print(f"  Source spec:   {spec_path}")
    print(f"  Filter paths:  {filter_paths_list or 'None (full spec)'}")
    print(f"  Overlay:       {overlay_path or 'None'}")
    print(f"  Output:        {output_path}")
    print("=" * 60)

    # Step 1: Load spec
    print("\n[1/3] Loading source spec...")
    spec = load_openapi_yaml(spec_path)
    print(f"      Loaded {len(spec.get('paths', {}))} paths")

    # Step 2: Filter paths
    if filter_paths_list:
        print(f"\n[2/3] Filtering to {len(filter_paths_list)} paths...")
        spec = filter_paths(spec, filter_paths_list)
        print(f"      Remaining paths: {list(spec['paths'].keys())}")
    else:
        print("\n[2/3] Skipping filtering (no filter paths specified)")

    # Step 3: Apply overlay
    if overlay_path and overlay_path.exists():
        print(f"\n[3/3] Applying overlay from {overlay_path}...")
        overlay = load_openapi_yaml(str(overlay_path))
        spec = apply_overlay(spec, overlay)
        print("      Overlay applied successfully")
    else:
        print("\n[3/3] Skipping overlay (no overlay file)")

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"\n✅ Derived spec written to: {output_path}")
    print(f"   Paths in derived spec: {len(spec.get('paths', {}))}")

    # Show summary of paths and their operations
    print("\n📋 Summary of derived spec:")
    for path, operations in spec.get("paths", {}).items():
        methods = [m.upper() for m in operations.keys() if m in ["get", "post", "put", "patch", "delete"]]
        op_ids = [operations[m.lower()].get("operationId", "N/A") for m in methods if m.lower() in operations]
        print(f"   {path}")
        for method, op_id in zip(methods, op_ids):
            print(f"      {method}: {op_id}")


if __name__ == "__main__":
    main()

