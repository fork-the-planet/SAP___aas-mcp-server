# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AAS MCP Server is an OpenAPI-to-MCP bridge for Asset Administration Shell (AAS) APIs. It converts OpenAPI specifications into Model Context Protocol (MCP) tools, enabling LLMs to interact with AAS services through a safe, curated interface.

**Key Architecture Principle**: Single codebase, multi-component monorepo. One CLI, multiple AAS components (repositories and registries), each with its own OpenAPI spec and default configuration.

## Component Architecture

The server supports 4 AAS components, defined in `src/aas_mcp_server/cli.py:COMPONENT_CONFIGS`:

1. **aas-repo** - Asset Administration Shell Repository (port 8080)
2. **submodel-repo** - Submodel Repository (port 8081)
3. **aas-registry** - AAS Registry (port 8083)
4. **submodel-registry** - Submodel Registry (port 8084)

Each component has:
- Default OpenAPI spec path (derived specs in `openapi/derived/*.yaml` for repos, original specs for registries)
- Default base URL (localhost with component-specific port)
- Description string

**Note**: The AAS and Submodel Repository components use **derived OpenAPI specs** that are filtered to only include endpoints supported by the BaSyx implementation. See the "Derived Specs and BaSyx Filtering" section below for details.

## Core Processing Pipeline

**Entry Point**: `cli.py:main()` → `server.py:build_mcp_server()` → FastMCP server

The OpenAPI spec undergoes a 3-stage transformation:

### Stage 1: Load & Process (`openapi_loader.py`)
1. Load OpenAPI YAML from disk
2. **Path Filtering** (optional): Filter to specific paths/methods via env var
   - Env var format: `{COMPONENT}_FILTER_PATHS` (e.g., `AAS_REPO_FILTER_PATHS`)
   - Filter syntax: `/path:method1,method2` or `/path` (all methods)
   - Semicolon-separated for multiple paths
3. **Overlay Application** (optional): Apply OpenAPI Overlay spec if exists
   - Overlay path: `openapi/overlays/{component}-overlay.yaml`
   - Uses `oas-patch` library to apply overlay transformations
   - Overlays can rename operationIds, update descriptions, add extensions

### Stage 2: Curation (`tool_curation.py`)
Safety-focused transformations:
- **Allowlist filtering**: Only expose operations in `DEFAULT_ALLOWLIST`
- **Read-only by default**: Block write methods (POST/PUT/PATCH/DELETE) unless `--enable-writes`
- **operationId aliasing**: Rename operations to LLM-friendly names via `OPERATION_ID_ALIASES`
- **Limit parameter capping**: Cap pagination limits to max 100

### Stage 3: MCP Generation (`server.py`)
- `FastMCP.from_openapi()` generates MCP tools from curated spec
- HTTP client built with optional auth headers (`http_client.py`)
- Returns ready-to-run FastMCP server instance

## Derived Specs and BaSyx Filtering

The AAS and Submodel Repository components use **derived OpenAPI specifications** that are pre-filtered to only include endpoints actually supported by the Eclipse BaSyx implementation. This ensures the MCP server exposes a practical, working API surface rather than the full theoretical specification.

### Why Derived Specs?

The official AAS OpenAPI specs (V3.1.1 SSP-001) define many endpoints that are not implemented by BaSyx:
- **AAS Repo**: Official spec has 33 paths, BaSyx implements only 6 core paths
- **Submodel Repo**: Official spec has 30 paths, BaSyx implements only 9 core paths

Using derived specs prevents LLMs from attempting to use unsupported endpoints.

### Generating Derived Specs

Derived specs are generated using a two-step process:

1. **Generate BaSyx filter strings** (computes intersection of official spec and BaSyx implementation):
   ```bash
   python3 scripts/generate_basyx_filters.py
   ```
   This analyzes `docs/basyx-repo-supported-endpoints.json` and outputs filter path strings.

2. **Generate derived specs** using the filter strings:
   ```bash
   # Copy the export commands from step 1 output, then:
   export AAS_REPO_FILTER_PATHS="<filter string>"
   python3 scripts/generate_derived_spec.py --component aas-repo

   export SUBMODEL_REPO_FILTER_PATHS="<filter string>"
   python3 scripts/generate_derived_spec.py --component submodel-repo
   ```

Derived specs are written to `openapi/derived/` and include overlays automatically.

### BaSyx-Supported Endpoints

**AAS Repository** (6 paths, 14 operations):
- `/shells` - GET, POST
- `/shells/{aasIdentifier}` - GET, PUT, DELETE
- `/shells/{aasIdentifier}/asset-information` - GET, PUT
- `/shells/{aasIdentifier}/asset-information/thumbnail` - GET, PUT, DELETE
- `/shells/{aasIdentifier}/submodel-refs` - GET, POST
- `/shells/{aasIdentifier}/submodel-refs/{submodelIdentifier}` - DELETE

**Submodel Repository** (9 paths, 22 operations):
- `/submodels` - GET, POST
- `/submodels/{submodelIdentifier}` - GET, PUT, DELETE
- `/submodels/{submodelIdentifier}/$metadata` - GET
- `/submodels/{submodelIdentifier}/$value` - GET, PATCH
- `/submodels/{submodelIdentifier}/submodel-elements` - GET, POST
- `/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}` - GET, PUT, POST, DELETE
- `/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$value` - GET, PATCH
- `/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment` - GET, PUT, DELETE
- `/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke` - POST

The reference documentation is maintained in `docs/basyx-repo-supported-endpoints.json`.

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
