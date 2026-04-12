# Implementation Configurations

This directory contains configuration files for different AAS implementation profiles. Each configuration defines the complete specification pipeline:
1. **Endpoint intersection** (which endpoints are supported)
2. **Overlay application** (renaming operations for LLM understanding)
3. **Curation rules** (allowlist, aliases, safety settings)

## Available Configurations

### Eclipse BaSyx (`basyx-config.yaml`)
Default configuration for Eclipse BaSyx v2.0 implementation. This is the reference implementation included with the project.

### FA³ST Service (Template)
Template configuration for FA³ST Service. See `faaast-config.yaml.template` for instructions on how to create a FA³ST configuration.

## Configuration File Format

Each configuration file follows this structure:

```yaml
name: Implementation Name
version: version
description: Description of the implementation

components:
  component-name:
    # Required fields
    implementation_spec: path/to/implementation-endpoints.json  # What the implementation actually supports
    official_spec: path/to/official-spec.yaml                  # Official AAS specification
    
    # Optional fields
    path_prefix: /optional-prefix  # Filter paths by prefix (null = no filtering)
    description: Component description
    overlay: path/to/overlay.yaml  # OpenAPI Overlay for renaming operations
    
    # Optional curation settings (for documentation/future use)
    curation:
      allowlist:                   # List of [method, path] tuples to expose as MCP tools
        - [get, /shells]
        - [post, /shells]
      aliases:                     # Map operationId to LLM-friendly names
        GetAllAssetAdministrationShells: list_shells
```

### Fields Explained

#### Top-level Fields

- **name**: Human-readable name of the implementation (e.g., "Eclipse BaSyx")
- **version**: Version string (e.g., "v2.0")
- **description**: Brief description of the implementation

#### Component Fields (Required)

- **implementation_spec**: Path to OpenAPI spec documenting what the implementation actually supports
  - Can be JSON or YAML format
  - Should contain only the endpoints that the implementation has implemented
  - Used to compute the intersection with the official spec

- **official_spec**: Path to the official AAS OpenAPI specification
  - Always YAML format
  - The authoritative spec from IDTA/AAS standards body
  - Used as the base for derived spec generation

#### Component Fields (Optional)

- **path_prefix**: String or null
  - Filter implementation spec paths to only those starting with this prefix
  - Useful when one implementation spec file covers multiple components
  - Example: `/shells` for aas-repo, `/submodels` for submodel-repo
  - Set to `null` when no filtering is needed

- **description**: String
  - Human-readable description shown in CLI output

- **overlay**: String (path to file)
  - Path to an OpenAPI Overlay YAML file
  - Applied during derived spec generation
  - Used to rename operationIds, update descriptions, add extensions
  - Example: `openapi/overlays/aas-repo-overlay.yaml`

- **curation**: Object (allowlist + aliases)
  - **NOTE**: Currently for documentation only - not yet consumed by runtime
  - Future: Will override defaults from `tool_curation.py`
  - **allowlist**: List of `[method, path]` tuples
    - Only these operations will be exposed as MCP tools
    - Method should be lowercase (get, post, put, patch, delete)
  - **aliases**: Map of operationId → friendly name
    - Makes tool names more LLM-friendly

## Using Configurations

### Quick Start: Generate All Specs in One Command

```bash
# Default (BaSyx)
python3 scripts/generate_implementation.py

# Specific implementation
python3 scripts/generate_implementation.py --config configs/faaast-config.yaml

# Dry-run to see what would happen
python3 scripts/generate_implementation.py --dry-run
```

### Manual Step-by-Step (Advanced)

#### Step 1: Generate Filter Strings

```bash
# Default Configuration (BaSyx)
python3 scripts/generate_filters.py

# Via Environment Variable
export AAS_IMPLEMENTATION_CONFIG=configs/basyx-config.yaml
python3 scripts/generate_filters.py

# Via Command-Line Argument
python3 scripts/generate_filters.py --config configs/basyx-config.yaml

# List Available Configurations
python3 scripts/generate_filters.py --list-configs
```

#### Step 2: Generate Derived Specs

```bash
# Copy the export commands from step 1 output, then:
export AAS_REPO_FILTER_PATHS="<filter string>"
python3 scripts/generate_derived_spec.py --component aas-repo

# Repeat for other components
```

## Creating a New Implementation Configuration

1. **Document the implementation's endpoints**
   - Export or manually create an OpenAPI spec (JSON or YAML)
   - Document all paths and HTTP methods supported by the implementation
   - Save in `docs/` directory (e.g., `docs/myimpl-repo-supported-endpoints.json`)

2. **Create configuration file**
   - Copy `basyx-config.yaml` as a starting point
   - Update all `implementation_spec` paths to point to your documentation
   - Update `name`, `version`, and `description`
   - Add `overlay` paths if you have custom overlays
   - Save as `configs/myimpl-config.yaml`

3. **Generate all specs in one command**
   ```bash
   python3 scripts/generate_implementation.py --config configs/myimpl-config.yaml
   ```

4. **(Optional) Create overlays**
   - Create overlay files in `openapi/overlays/` to customize operation names
   - See existing overlays for examples
   - Reference them in your config file's `overlay` field

5. **(Optional) Update CLI defaults**
   - Modify `src/aas_mcp_server/cli.py` to add a new component profile or
   - Use environment variables to point to your derived specs

## Example: Adding Custom Implementation

```yaml
# configs/custom-config.yaml
name: Custom AAS Implementation
version: v1.0
description: My custom AAS server implementation

components:
  aas-repo:
    implementation_spec: docs/custom-repo-endpoints.json
    official_spec: openapi/AssetAdministrationShellRepositoryServiceSpecification-V3.1.1_SSP-001-resolved.yaml
    path_prefix: /shells
    description: Custom AAS Repository
    overlay: openapi/overlays/custom-aas-repo-overlay.yaml  # Optional

  # ... other components
```

Then generate all specs:
```bash
python3 scripts/generate_implementation.py --config configs/custom-config.yaml
```

## Pipeline Overview

The configuration file is used by these scripts:

1. **scripts/generate_filters.py**
   - Reads: `implementation_spec`, `official_spec`, `path_prefix`
   - Computes intersection of endpoints
   - Outputs: Filter strings for environment variables

2. **scripts/generate_derived_spec.py**
   - Reads: `official_spec`, `overlay` (via env vars or defaults)
   - Applies path filtering and overlay
   - Outputs: Derived OpenAPI specs in `openapi/derived/`

3. **scripts/generate_implementation.py** (Recommended)
   - Orchestrates steps 1 and 2 automatically
   - Reads all fields to coordinate the pipeline
   - One command to generate everything

4. **src/aas_mcp_server/** (Runtime)
   - Currently: Uses hardcoded defaults in `tool_curation.py`
   - Future: Could read `curation` section from config

## Validation

To validate that your derived specs are up-to-date with config:

```bash
python3 scripts/validate_derived_specs.py --config configs/your-config.yaml
```

(Coming soon)

## Notes

- The `path_prefix` is useful when a single implementation spec contains endpoints for multiple components (like BaSyx's combined repo spec)
- Set `path_prefix: null` when the implementation spec only contains paths for that specific component
- Configuration files must be valid YAML
- Implementation specs can be either JSON or YAML format (both are supported)
- Overlay files follow the [OpenAPI Overlay Specification](https://github.com/OAI/Overlay-Specification)
