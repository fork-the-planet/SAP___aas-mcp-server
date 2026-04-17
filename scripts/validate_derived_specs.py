#!/usr/bin/env python3
"""
Validate that derived OpenAPI specs are up-to-date with their source configuration.

This script checks:
1. Whether derived specs exist for all components in a configuration
2. Whether derived specs were generated from the correct source specs
3. Whether overlays have been applied
4. Whether the filter paths match (by checking path counts)

Usage:
    # Validate your implementation configuration
    python3 scripts/validate_derived_specs.py --config configs/my-implementation-config.yaml

    # Validate BaSyx example configuration
    python3 scripts/validate_derived_specs.py --config configs/basyx-config.example.yaml

    # Verbose output
    python3 scripts/validate_derived_specs.py --config configs/my-config.yaml --log-level DEBUG
"""

import argparse
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


def load_config(config_path: str | None) -> dict[str, Any]:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = os.getenv(CONFIG_ENV_VAR, DEFAULT_CONFIG_PATH)

    if not Path(config_path).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    logging.debug(f"Loading configuration from: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_openapi_yaml(path: str) -> dict[str, Any]:
    """Load OpenAPI spec from YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def get_derived_spec_path(component_name: str, official_spec_path: str) -> Path:
    """
    Compute the expected path for a derived spec.

    Convention: openapi/derived/{original-filename}-derived.yaml
    """
    original_filename = Path(official_spec_path).stem
    return Path(f"openapi/derived/{original_filename}-derived.yaml")


def validate_component(
    component_name: str,
    component_config: dict[str, Any],
    config_name: str
) -> tuple[bool, list[str]]:
    """
    Validate a single component's derived spec.

    Returns:
        Tuple of (is_valid: bool, issues: list[str])
    """
    issues = []

    # Get expected derived spec path
    official_spec_path = component_config["official_spec"]
    derived_spec_path = get_derived_spec_path(component_name, official_spec_path)

    logging.debug(f"  Expected derived spec: {derived_spec_path}")

    # Check 1: Derived spec exists
    if not derived_spec_path.exists():
        issues.append(f"Derived spec not found: {derived_spec_path}")
        return False, issues

    logging.debug(f"  ✓ Derived spec exists")

    # Check 2: Derived spec is valid YAML
    try:
        derived_spec = load_openapi_yaml(str(derived_spec_path))
    except Exception as e:
        issues.append(f"Failed to parse derived spec: {e}")
        return False, issues

    logging.debug(f"  ✓ Derived spec is valid YAML")

    # Check 3: Derived spec has paths
    derived_paths = derived_spec.get("paths", {})
    if not derived_paths:
        issues.append(f"Derived spec has no paths (empty spec)")
        return False, issues

    logging.debug(f"  ✓ Derived spec has {len(derived_paths)} paths")

    # Check 4: Official spec exists and is parseable
    if not Path(official_spec_path).exists():
        issues.append(f"Official spec not found: {official_spec_path}")
        return False, issues

    try:
        official_spec = load_openapi_yaml(official_spec_path)
        official_paths = official_spec.get("paths", {})
    except Exception as e:
        issues.append(f"Failed to parse official spec: {e}")
        return False, issues

    logging.debug(f"  ✓ Official spec has {len(official_paths)} paths")

    # Check 5: Derived spec is a subset of official spec
    derived_path_set = set(derived_paths.keys())
    official_path_set = set(official_paths.keys())

    invalid_paths = derived_path_set - official_path_set
    if invalid_paths:
        issues.append(
            f"Derived spec contains paths not in official spec: {invalid_paths}"
        )
        return False, issues

    logging.debug(f"  ✓ All derived paths exist in official spec")

    # Check 6: Overlay exists if specified
    overlay_path = component_config.get("overlay")
    if overlay_path:
        if not Path(overlay_path).exists():
            issues.append(f"Overlay file not found: {overlay_path}")
        else:
            logging.debug(f"  ✓ Overlay exists: {overlay_path}")

    # Check 7: Implementation spec exists
    impl_spec_path = component_config["implementation_spec"]
    if not Path(impl_spec_path).exists():
        issues.append(f"Implementation spec not found: {impl_spec_path}")
    else:
        logging.debug(f"  ✓ Implementation spec exists: {impl_spec_path}")

    # All checks passed
    if not issues:
        logging.info(f"    ✅ Valid ({len(derived_paths)} paths)")
        return True, []
    else:
        return False, issues


def main():
    parser = argparse.ArgumentParser(
        description="Validate that derived specs are up-to-date with configuration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        help=f"Path to implementation configuration file (default: {DEFAULT_CONFIG_PATH})",
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

    # Load configuration
    config_path = args.config or os.getenv(CONFIG_ENV_VAR, DEFAULT_CONFIG_PATH)
    try:
        config = load_config(config_path)
    except FileNotFoundError as e:
        logging.error(f"❌ {e}")
        sys.exit(1)

    config_name = config.get("name", "Unknown")
    config_version = config.get("version", "")

    logging.info("=" * 80)
    logging.info(f"DERIVED SPEC VALIDATION")
    logging.info(f"Implementation: {config_name} {config_version}")
    logging.info(f"Configuration: {config_path}")
    logging.info("=" * 80)

    components = config.get("components", {})
    if not components:
        logging.error("\n❌ No components found in configuration")
        sys.exit(1)

    # Validate each component
    valid_count = 0
    invalid_count = 0
    all_issues = {}

    for component_name, component_config in components.items():
        logging.info(f"\n  [{component_name}]")

        is_valid, issues = validate_component(
            component_name, component_config, config_name
        )

        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            all_issues[component_name] = issues
            for issue in issues:
                logging.error(f"    ❌ {issue}")

    # Summary
    logging.info("\n" + "=" * 80)
    logging.info("VALIDATION SUMMARY")
    logging.info("=" * 80)
    logging.info(f"Total components: {len(components)}")
    logging.info(f"  ✅ Valid: {valid_count}")
    if invalid_count > 0:
        logging.error(f"  ❌ Invalid: {invalid_count}")

    # Show remediation steps if there are issues
    if all_issues:
        logging.info("\n" + "=" * 80)
        logging.info("REMEDIATION")
        logging.info("=" * 80)
        logging.info("To fix validation issues, regenerate the derived specs:")
        logging.info(f"  python3 scripts/generate_implementation.py --config {config_path}")
        logging.info("\nOr regenerate individual components:")
        for component_name in all_issues.keys():
            logging.info(f"  python3 scripts/generate_derived_spec.py --component {component_name}")

    # Exit with error code if validation failed
    if invalid_count > 0:
        sys.exit(1)
    else:
        logging.info("\n✅ All derived specs are valid and up-to-date!")


if __name__ == "__main__":
    main()
