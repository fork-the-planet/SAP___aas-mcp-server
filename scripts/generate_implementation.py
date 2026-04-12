#!/usr/bin/env python3
"""
Orchestration script to generate all derived specs for an AAS implementation.

This script runs the complete pipeline:
1. Generate filter strings (computes intersection with implementation)
2. Generate derived specs for each component (applies filters + overlays)

This is a convenience wrapper around generate_filters.py and generate_derived_spec.py.

Usage:
    # Generate all specs for default implementation (BaSyx)
    python3 scripts/generate_implementation.py

    # Generate for specific implementation
    python3 scripts/generate_implementation.py --config configs/faaast-config.yaml

    # Dry-run to see what would be generated without writing files
    python3 scripts/generate_implementation.py --dry-run

    # With verbose output
    python3 scripts/generate_implementation.py --log-level DEBUG
"""

import argparse
import logging
import os
import subprocess
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

# Default configuration file path
DEFAULT_CONFIG_PATH = "configs/basyx-config.yaml"

# Environment variable for configuration path
CONFIG_ENV_VAR = "AAS_IMPLEMENTATION_CONFIG"


def load_config(config_path: str | None) -> dict[str, Any]:
    """
    Load configuration from YAML file.

    Priority:
    1. Command-line argument (--config)
    2. Environment variable (AAS_IMPLEMENTATION_CONFIG)
    3. Default (configs/basyx-config.yaml)
    """
    if config_path is None:
        config_path = os.getenv(CONFIG_ENV_VAR, DEFAULT_CONFIG_PATH)

    if not Path(config_path).exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please create a configuration file or use --list-configs to see available configurations."
        )

    logging.info(f"Loading configuration from: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


def run_command(cmd: list[str], description: str, dry_run: bool = False) -> tuple[bool, str]:
    """
    Run a shell command and return success status and output.

    Args:
        cmd: Command and arguments as list
        description: Human-readable description of what the command does
        dry_run: If True, only print the command without executing it

    Returns:
        Tuple of (success: bool, output: str)
    """
    logging.info(f"\n{'[DRY-RUN] ' if dry_run else ''}Running: {description}")
    logging.debug(f"Command: {' '.join(cmd)}")

    if dry_run:
        logging.info(f"  Would execute: {' '.join(cmd)}")
        return True, ""

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"  ❌ Command failed with exit code {e.returncode}")
        logging.error(f"  Error output: {e.stderr}")
        return False, e.stderr


def main():
    parser = argparse.ArgumentParser(
        description="Generate all derived specs for an AAS implementation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        help=f"Path to implementation configuration file (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually executing commands",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level (default: INFO)",
    )
    parser.add_argument(
        "--skip-filters",
        action="store_true",
        help="Skip filter generation step (use existing environment variables)",
    )

    args = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(args.log_level)

    # Load configuration
    config_path = args.config or os.getenv(CONFIG_ENV_VAR, DEFAULT_CONFIG_PATH)
    config = load_config(config_path)
    config_name = config.get("name", "Unknown")
    config_version = config.get("version", "")

    logging.info("=" * 80)
    logging.info(f"AAS IMPLEMENTATION SPEC GENERATION")
    logging.info(f"Implementation: {config_name} {config_version}")
    logging.info(f"Configuration: {config_path}")
    if args.dry_run:
        logging.info("Mode: DRY-RUN (no files will be written)")
    logging.info("=" * 80)

    # Step 1: Generate filter strings
    if not args.skip_filters:
        logging.info("\n" + "=" * 80)
        logging.info("STEP 1: Generate Filter Strings")
        logging.info("=" * 80)

        filter_cmd = [
            "python3",
            "scripts/generate_filters.py",
            "--config", config_path,
            "--log-level", args.log_level
        ]

        success, output = run_command(
            filter_cmd,
            "Computing intersection of official spec and implementation",
            dry_run=args.dry_run
        )

        if not success:
            logging.error("\n❌ Filter generation failed. Aborting.")
            sys.exit(1)

        if not args.dry_run:
            # Parse filter strings from output
            filter_strings = {}
            for line in output.split('\n'):
                if line.strip().startswith('export ') and '_FILTER_PATHS=' in line:
                    # Extract: export AAS_REPO_FILTER_PATHS="..."
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        env_var = parts[0].replace('export ', '').strip()
                        value = parts[1].strip().strip('"')
                        filter_strings[env_var] = value

            logging.info(f"\n✅ Generated {len(filter_strings)} filter strings")
            for env_var, value in filter_strings.items():
                logging.debug(f"  {env_var}: {value[:80]}...")

            # Set environment variables for next step
            for env_var, value in filter_strings.items():
                os.environ[env_var] = value
                logging.debug(f"  Set environment variable: {env_var}")
    else:
        logging.info("\n⏭️  Skipping filter generation (--skip-filters specified)")
        logging.info("Using existing environment variables")

    # Step 2: Generate derived specs for each component
    logging.info("\n" + "=" * 80)
    logging.info("STEP 2: Generate Derived Specs")
    logging.info("=" * 80)

    components = config.get("components", {})
    if not components:
        logging.error("❌ No components found in configuration")
        sys.exit(1)

    success_count = 0
    fail_count = 0

    for component_name in components.keys():
        logging.info(f"\n{'─' * 80}")
        logging.info(f"Generating derived spec for: {component_name}")
        logging.info(f"{'─' * 80}")

        derived_cmd = [
            "python3",
            "scripts/generate_derived_spec.py",
            "--component", component_name
        ]

        success, output = run_command(
            derived_cmd,
            f"Generating derived spec for {component_name}",
            dry_run=args.dry_run
        )

        if success:
            success_count += 1
            if not args.dry_run and output:
                # Show summary from generate_derived_spec.py output
                for line in output.split('\n'):
                    if '✅' in line or '📋' in line or line.strip().startswith('Paths in derived spec:'):
                        logging.info(f"  {line}")
        else:
            fail_count += 1

    # Final summary
    logging.info("\n" + "=" * 80)
    logging.info("SUMMARY")
    logging.info("=" * 80)
    logging.info(f"Total components: {len(components)}")
    logging.info(f"  ✅ Successful: {success_count}")
    if fail_count > 0:
        logging.error(f"  ❌ Failed: {fail_count}")

    if args.dry_run:
        logging.info("\n💡 This was a dry-run. Run without --dry-run to generate actual files.")
    else:
        logging.info(f"\n✅ All derived specs generated successfully!")
        logging.info(f"   Output directory: openapi/derived/")

    # Exit with error code if any component failed
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
