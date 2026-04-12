# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AAS MCP Server is an OpenAPI-to-MCP bridge for Asset Administration Shell (AAS) APIs. It converts OpenAPI specifications into Model Context Protocol (MCP) tools, enabling LLMs to interact with AAS services through a safe, curated interface.

**Key Architecture Principles**:
1. **Pure Adapter Pattern**: The server doesn't bundle any AAS backend implementation. Users provide their own AAS backend (BaSyx, FA³ST, custom, etc.), and this server translates LLM requests into HTTP calls.
2. **Single Codebase, Multi-Component**: One CLI, multiple AAS components (repositories and registries), each with its own OpenAPI spec and default configuration.
3. **Default: Official Specs**: By default, uses full official AAS specifications. Derived specs are provided as examples for specific implementations (BaSyx).

## Component Architecture

The server supports 4 AAS components, defined in `src/aas_mcp_server/cli.py:COMPONENT_CONFIGS`:

1. **aas-repo** - Asset Administration Shell Repository
2. **submodel-repo** - Submodel Repository
3. **aas-registry** - AAS Registry
4. **submodel-registry** - Submodel Registry

Each component has:
- Default OpenAPI spec path (official AAS specs in `openapi/*.yaml`)
- Default base URL (must be provided by user, or defaults to localhost)
- Description string

**OpenAPI Specification Strategy**:
- **Default**: Official AAS OpenAPI specs (V3.1.1 SSP-001) - full, unfiltered
- **Examples**: Derived specs in `openapi/derived/` for Eclipse BaSyx v2.0
- **User Choice**: Users can generate their own derived specs for their implementation (see "Derived Specs and Implementation Filtering" below)

## Core Processing Pipeline

**Entry Point**: `cli.py:main()` → `server.py:build_mcp_server()` → FastMCP server

The architecture separates **build-time** spec generation from **runtime** spec processing:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BUILD-TIME PIPELINE                              │
│                   (Run scripts to generate specs)                       │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ Implementation Config│  configs/basyx-config.yaml
│ (BaSyx, FA³ST, etc.) │  - implementation_spec (what's actually supported)
└──────────┬───────────┘  - official_spec (full AAS spec)
           │              - overlay (renames for LLMs)
           ▼
┌──────────────────────┐
│ generate_filters.py  │  Computes intersection: official ∩ implementation
└──────────┬───────────┘  Output: Filter strings (env vars)
           │              Example: AAS_REPO_FILTER_PATHS="/shells:get,post;..."
           ▼
┌──────────────────────┐
│generate_derived_      │  Applies filters + overlays to official spec
│    spec.py           │  Output: openapi/derived/*-derived.yaml
└──────────┬───────────┘  (One derived spec per component)
           │
           ▼
     ┌─────────────┐
     │ Derived Spec│───────┐
     │  (filtered  │       │
     │   + overlay)│       │
     └─────────────┘       │
                           │
┌──────────────────────────────────────────────────────────────────────┐
│                       RUNTIME PIPELINE                               │
│                  (When MCP server starts)                            │
└──────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────┐
         │ Stage 1: openapi_loader.py  │
         │ - Load derived spec         │
         │ - (Optional) Runtime filter │
         │ - (Optional) Runtime overlay│
         └──────────┬──────────────────┘
                    ▼
         ┌─────────────────────────────┐
         │ Stage 2: tool_curation.py   │
         │ - Allowlist filtering       │
         │ - Read-only enforcement     │
         │ - operationId aliasing      │
         │ - Limit parameter capping   │
         └──────────┬──────────────────┘
                    ▼
         ┌─────────────────────────────┐
         │ Stage 3: server.py          │
         │ - FastMCP.from_openapi()    │
         │ - Generate MCP tools        │
         │ - Build HTTP client         │
         └──────────┬──────────────────┘
                    ▼
              ┌──────────┐
              │ MCP Tools│ (Ready for LLM use)
              └──────────┘
```

### When to Regenerate Specs

**Regenerate derived specs when:**
- Implementation adds/removes endpoint support
- You want to expose different operations
- Overlay names need updating
- Switching to a different implementation (BaSyx → FA³ST)

**Quick regeneration:**
```bash
# Regenerate all specs for current config
python3 scripts/generate_implementation.py

# Or for specific implementation
python3 scripts/generate_implementation.py --config configs/faaast-config.yaml

# Validate specs are up-to-date
python3 scripts/validate_derived_specs.py
```

### Build-Time vs Runtime

| Stage | When | Purpose | Tools |
|-------|------|---------|-------|
| **Build-Time** | Before deployment, after config changes | Generate filtered specs from implementation configs | `generate_filters.py`, `generate_derived_spec.py`, `generate_implementation.py` |
| **Runtime** | Every MCP server start | Apply safety rules and generate MCP tools | `openapi_loader.py`, `tool_curation.py`, `server.py` |

**Why separate?**
- **Performance**: Filtering at build-time means faster startup
- **Inspectability**: Derived specs can be version-controlled and reviewed
- **Flexibility**: Runtime can still apply additional filters/overlays if needed

### Stage Details

#### Build-Time: Spec Generation

1. **Configuration** (`configs/*.yaml`)
   - Defines implementation capabilities
   - Points to implementation and official specs
   - Specifies overlays for renaming

2. **Filter Generation** (`scripts/generate_filters.py`)
   - Computes intersection: official spec ∩ implementation spec
   - Outputs filter strings (which paths/methods to keep)

3. **Derived Spec Generation** (`scripts/generate_derived_spec.py`)
   - Applies filters to official spec (keeps only supported endpoints)
   - Applies overlays (renames operationIds for LLM understanding)
   - Writes to `openapi/derived/*.yaml`

#### Runtime: MCP Tool Generation

**Stage 1: Load & Process** (`openapi_loader.py`)
1. Load OpenAPI spec from disk
   - **Default**: Official AAS spec (full, unfiltered)
   - **Optional**: User-provided derived spec via `--openapi` flag
2. **Optional**: Apply runtime path filtering via env var
   - Env var format: `{COMPONENT}_FILTER_PATHS` (e.g., `AAS_REPO_FILTER_PATHS`)
   - Filter syntax: `/path:method1,method2` or `/path` (all methods)
   - Semicolon-separated for multiple paths
3. **Optional**: Apply runtime overlay if exists
   - Overlay path: `openapi/overlays/{component}-overlay.yaml`
   - Uses `oas-patch` library to apply overlay transformations

**Stage 2: Curation** (`tool_curation.py`)
Safety-focused transformations:
- **Allowlist filtering**: Only expose operations in `DEFAULT_ALLOWLIST`
- **Read-only by default**: Block write methods (POST/PUT/PATCH/DELETE) unless `--enable-writes`
- **operationId aliasing**: Rename operations to LLM-friendly names via `OPERATION_ID_ALIASES`
- **Limit parameter capping**: Cap pagination limits to max 100

**Stage 3: MCP Generation** (`server.py`)
- `FastMCP.from_openapi()` generates MCP tools from curated spec
- HTTP client built with optional auth headers (`http_client.py`)
- Returns ready-to-run FastMCP server instance

## Derived Specs and Implementation Filtering

**By default**, the MCP server uses the **official AAS OpenAPI specifications** (V3.1.1 SSP-001) - full, unfiltered specs that define the complete AAS API surface.

**Optional**: The project includes **example derived specs** for **Eclipse BaSyx v2.0** in `openapi/derived/`. These are pre-filtered to only include endpoints that BaSyx actually implements, preventing LLMs from attempting to use unsupported endpoints.

**User Choice**: Users can generate their own derived specs for their specific implementation (FA³ST, custom servers, etc.) using the provided tools.

### Why Use Derived Specs?

The official AAS OpenAPI specs are comprehensive, but real-world implementations often support only a subset of endpoints:

**Example - Eclipse BaSyx Coverage:**
- **AAS Repo**: Official spec has 33 paths, BaSyx implements 6 core paths (18% coverage)
- **Submodel Repo**: Official spec has 30 paths, BaSyx implements 9 paths (30% coverage)
- **AAS Registry**: Official spec has 5 paths, BaSyx implements all 5 (100% coverage)
- **Submodel Registry**: Official spec has 3 paths, BaSyx implements all 3 (100% coverage)

**Benefits of derived specs:**
- Prevents LLMs from attempting unsupported endpoints (better UX)
- Faster spec processing (smaller OpenAPI spec)
- Clearer tool documentation (only shows what works)

**When to use official specs vs derived specs:**
- **Official specs** (default): Your backend implements most/all of the AAS specification
- **Derived specs**: Your backend implements a subset, and you want to hide unsupported endpoints

### Generating Derived Specs for Your Implementation

**Quick method** (recommended - runs all steps automatically):
```bash
# One command to generate all specs
python3 scripts/generate_implementation.py --config configs/your-config.yaml

# Dry-run to preview
python3 scripts/generate_implementation.py --config configs/your-config.yaml --dry-run
```

**Manual method** (for advanced users):

1. **Generate filter strings** (computes intersection of official spec and implementation):
   ```bash
   # Use default configuration (BaSyx)
   python3 scripts/generate_filters.py

   # Use specific implementation via environment variable
   export AAS_IMPLEMENTATION_CONFIG=configs/faaast-config.yaml
   python3 scripts/generate_filters.py

   # Use specific implementation via command-line
   python3 scripts/generate_filters.py --config configs/your-config.yaml

   # List available configurations
   python3 scripts/generate_filters.py --list-configs
   ```

   The script loads configuration from (in priority order):
   1. Command-line argument (`--config`)
   2. Environment variable (`AAS_IMPLEMENTATION_CONFIG`)
   3. Default (`configs/basyx-config.yaml`)

2. **Generate derived specs** using the filter strings:
   ```bash
   # Copy the export commands from step 1 output, then:
   export AAS_REPO_FILTER_PATHS="<filter string>"
   python3 scripts/generate_derived_spec.py --component aas-repo

   export SUBMODEL_REPO_FILTER_PATHS="<filter string>"
   python3 scripts/generate_derived_spec.py --component submodel-repo

   export AAS_REGISTRY_FILTER_PATHS="<filter string>"
   python3 scripts/generate_derived_spec.py --component aas-registry

   export SUBMODEL_REGISTRY_FILTER_PATHS="<filter string>"
   python3 scripts/generate_derived_spec.py --component submodel-registry
   ```

Derived specs are written to `openapi/derived/` and include overlays automatically.

### Default Implementation: Eclipse BaSyx

The project includes derived specs for **Eclipse BaSyx** implementations as the default reference. The following endpoints are supported:

**AAS Repository** (6 paths, 13 operations):
- `/shells` - GET, POST
- `/shells/{aasIdentifier}` - GET, PUT, DELETE
- `/shells/{aasIdentifier}/asset-information` - GET, PUT
- `/shells/{aasIdentifier}/asset-information/thumbnail` - GET, PUT, DELETE
- `/shells/{aasIdentifier}/submodel-refs` - GET, POST
- `/shells/{aasIdentifier}/submodel-refs/{submodelIdentifier}` - DELETE

**Submodel Repository** (9 paths, 20 operations):
- `/submodels` - GET, POST
- `/submodels/{submodelIdentifier}` - GET, PUT, DELETE
- `/submodels/{submodelIdentifier}/$metadata` - GET
- `/submodels/{submodelIdentifier}/$value` - GET, PATCH
- `/submodels/{submodelIdentifier}/submodel-elements` - GET, POST
- `/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}` - GET, PUT, POST, DELETE
- `/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$value` - GET, PATCH
- `/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment` - GET, PUT, DELETE
- `/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke` - POST

**AAS Registry** (5 paths, 11 operations):
- `/description` - GET
- `/shell-descriptors` - GET, POST
- `/shell-descriptors/{aasIdentifier}` - GET, PUT, DELETE
- `/shell-descriptors/{aasIdentifier}/submodel-descriptors` - GET, POST
- `/shell-descriptors/{aasIdentifier}/submodel-descriptors/{submodelIdentifier}` - GET, PUT, DELETE

**Submodel Registry** (3 paths, 7 operations):
- `/description` - GET
- `/submodel-descriptors` - GET, POST
- `/submodel-descriptors/{submodelIdentifier}` - GET, PUT, DELETE

**Reference Documentation:**
- `docs/basyx-repo-supported-endpoints.json` (AAS and Submodel Repositories)
- `docs/basyx-aas-registry-supported-endpoints.json` (AAS Registry)
- `docs/basyx-submodel-registry-supported-endpoints.json` (Submodel Registry)

### Adding Support for Other Implementations

To add support for additional implementations (e.g., FA³ST, custom servers):

1. **Document the implementation's endpoints** in an OpenAPI JSON/YAML file (e.g., `docs/faaast-repo-supported-endpoints.json`)

2. **Create a configuration file** in `configs/` directory:
   ```yaml
   # configs/faaast-config.yaml
   name: FA³ST Service
   version: v1.0
   components:
     aas-repo:
       implementation_spec: docs/faaast-repo-supported-endpoints.json
       official_spec: openapi/AssetAdministrationShellRepositoryServiceSpecification-V3.1.1_SSP-001-resolved.yaml
       path_prefix: /shells
   ```
   See `configs/README.md` and `configs/faaast-config.yaml.template` for details.

3. **Generate filter strings**:
   ```bash
   python3 scripts/generate_filters.py --config configs/faaast-config.yaml
   ```

4. **Generate derived specs** using the output filter strings

5. **(Optional) Create overlays** to customize operation names and descriptions

6. **Update CLI configuration** in `src/aas_mcp_server/cli.py` to point to the new derived specs

The architecture supports multiple implementations side-by-side through configuration files in the `configs/` directory. Each configuration defines the endpoint mapping for a specific AAS implementation.

## Development Commands

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_openapi_loader.py -v

# Run specific test class/method
uv run pytest tests/test_openapi_loader.py::TestFilterPaths::test_filter_single_path_all_methods -v
```

### Running the Server Locally
```bash
# Install in editable mode
pip install -e .

# Run with specific component
aas-mcp-server --component aas-repo --log-level DEBUG

# Run with custom base URL
aas-mcp-server --component submodel-repo --base-url http://prod-server:8081

# Enable write operations
aas-mcp-server --component aas-repo --enable-writes

# Use custom OpenAPI spec
aas-mcp-server --component aas-registry --openapi ./custom-spec.yaml
```

### Testing with Path Filtering
```bash
# Filter to specific paths
export AAS_REPO_FILTER_PATHS="/shells:get,post;/shells/{aasIdentifier}:get"
aas-mcp-server --component aas-repo --log-level DEBUG

# View available tools in MCP inspector
# The filtered spec will only expose the specified paths/methods
```

## Key Files and Their Roles

### Core Module Files (`src/aas_mcp_server/`)
- **`cli.py`**: Argument parsing, component configuration mapping, main entry point
- **`server.py`**: FastMCP server builder, orchestrates the processing pipeline
- **`openapi_loader.py`**: OpenAPI loading with filtering and overlay support
- **`tool_curation.py`**: Safety-focused allowlist, write-blocking, and aliasing
- **`http_client.py`**: Async HTTP client builder with auth header support
- **`resources.py`**: Resource descriptions/documentation strings
- **`logging.py`**: Centralized logging configuration

### OpenAPI Specifications (`openapi/`)
- Official AAS specs: `*ServiceSpecification-V3.1.1_SSP-001-resolved.yaml`
- Overlays: `openapi/overlays/{component}-overlay.yaml`
- Derived specs: `openapi/derived/` (generated, not manually edited)

### Configuration Files
- **`pyproject.toml`**: Python packaging, dependencies, pytest config
- **`claude_desktop_config.example.json`**: Example Claude Desktop integration

## Environment Variables

### Component-Specific
- `AAS_BASE_URL`: Override default base URL
- `AAS_OPENAPI_PATH`: Override default OpenAPI spec path
- `AAS_MCP_ENABLE_WRITES`: Set to "1" to enable write operations
- `{COMPONENT}_FILTER_PATHS`: Path filtering per component (e.g., `AAS_REPO_FILTER_PATHS`)

### HTTP Client
- `AAS_TOKEN`: Bearer token for authentication
- `AAS_API_KEY`: API key for authentication
- `AAS_API_KEY_HEADER`: Custom API key header name (default: "X-API-Key")
- `AAS_HTTP_TIMEOUT`: HTTP request timeout in seconds (default: 30)

### General
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `MCP_TRANSPORT`: Transport protocol (default: stdio)

## Common Development Patterns

### Adding Support for a New Path
1. **Option A - Via Allowlist** (most restrictive, recommended):
   - Add `(method, path)` tuple to `tool_curation.py:DEFAULT_ALLOWLIST`
   - Add operationId alias to `OPERATION_ID_ALIASES` for better naming

2. **Option B - Via Environment Variable** (runtime filtering):
   - Set `{COMPONENT}_FILTER_PATHS` env var with desired paths
   - Useful for testing without code changes

3. **Option C - Via Overlay** (spec transformation):
   - Create/edit `openapi/overlays/{component}-overlay.yaml`
   - Use JSONPath targets to modify specific operations
   - Good for renaming, adding descriptions, or custom extensions

### Adding a New Component
1. Add entry to `cli.py:COMPONENT_CONFIGS` with:
   - OpenAPI spec path
   - Default URL
   - Description
2. Add filter env var mapping to `openapi_loader.py:COMPONENT_FILTER_ENV_VARS`
3. Place OpenAPI spec in `openapi/` directory
4. (Optional) Create overlay file in `openapi/overlays/`

### Debugging Tool Generation
1. Enable debug logging: `--log-level DEBUG`
2. Check filtered spec: Add logging in `openapi_loader.py:load_and_process_openapi()`
3. Check curated spec: Add logging in `tool_curation.py:curate_openapi_spec()`
4. Verify FastMCP receives expected spec in `server.py:build_mcp_server()`

## Testing Strategy

Tests are focused on the transformation pipeline:
- **`test_openapi_loader.py`**: Comprehensive tests for filtering and overlay application
  - Path filter parsing
  - Path/method filtering logic
  - Overlay file detection and application
  - Integration tests combining filtering + overlays

Key test patterns:
- Use fixtures to load real OpenAPI specs from `openapi/` directory
- Tests skip gracefully if fixture files are missing
- Tests verify transformations don't modify original spec (deepcopy validation)
- Integration tests verify complete pipeline from raw spec to curated output

## Safety and Security Philosophy

**Read-only by default**: Write operations (POST/PUT/PATCH/DELETE) are blocked unless explicitly enabled with `--enable-writes` flag. This prevents accidental modifications to production AAS services.

**Allowlist-based exposure**: Only paths explicitly listed in `DEFAULT_ALLOWLIST` are exposed as MCP tools. This creates a minimal, auditable API surface.

**Pagination limits**: `limit` query parameters are capped at 100 to prevent LLMs from requesting massive result sets that could overwhelm clients or services.

**Authentication support**: Optional bearer tokens and API keys are supported but must be explicitly configured via environment variables.

## MCP Integration Notes

Claude Desktop configuration requires one entry per component:
```json
{
  "mcpServers": {
    "aas-repo": {
      "command": "aas-mcp-server",
      "args": ["--component", "aas-repo", "--base-url", "http://localhost:8080"]
    },
    "submodel-repo": {
      "command": "aas-mcp-server",
      "args": ["--component", "submodel-repo", "--base-url", "http://localhost:8081"]
    }
  }
}
```

Each component runs as a separate MCP server process, exposing its own tool set. This allows LLMs to work with multiple AAS services simultaneously while keeping tool namespaces separate.

## OpenAPI Overlay Specification

Overlays follow the [OpenAPI Overlay Specification](https://github.com/OAI/Overlay-Specification). They use JSONPath to target specific parts of the OpenAPI spec and apply modifications.

Example overlay structure:
```yaml
overlay: 1.0.0
info:
  title: Component Extensions
  version: 1.0.0
actions:
  - target: "$.paths['/shells'].get"
    update:
      operationId: list_shells
      summary: List all Asset Administration Shells
```

Overlays are applied AFTER path filtering, so they only affect operations that survived the filter stage.
