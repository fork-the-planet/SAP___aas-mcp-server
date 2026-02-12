# AAS MCP Server

Open-source MCP server for Asset Administration Shell (AAS) APIs.
It converts an OpenAPI spec into MCP tools and exposes a curated, safe-by-default surface.

This server supports multiple AAS components in a single monorepo:
- **AAS Repository** - Manage Asset Administration Shells
- **Submodel Repository** - Manage Submodels
- **Concept Description Repository** - Manage Concept Descriptions
- **AAS Registry** - Discover and register AAS components

## Install
```bash
pip install aas-mcp-server
```

## Usage

The server requires a `--component` argument to specify which AAS component to serve:

### AAS Repository
```bash
aas-mcp-server --component aas-repo --base-url http://localhost:8080
```

### Submodel Repository
```bash
aas-mcp-server --component submodel-repo --base-url http://localhost:8081
```

### Concept Description Repository
```bash
aas-mcp-server --component concept-description-repo --base-url http://localhost:8082
```

### AAS Registry
```bash
aas-mcp-server --component aas-registry --base-url http://localhost:8083
```

## Configuration

Each component has default values that can be overridden:

### Command-line Arguments
- `--component` (required): Which AAS component to serve
- `--base-url`: Base URL for the component API (overrides component default)
- `--openapi`: Custom OpenAPI spec path (overrides component default)
- `--enable-writes`: Enable write operations (default: read-only)
- `--log-level`: Logging level (default: INFO)
- `--transport`: Transport protocol (default: stdio)

### Environment Variables
- `AAS_BASE_URL`: Override the default base URL
- `AAS_OPENAPI_PATH`: Override the default OpenAPI spec path
- `AAS_MCP_ENABLE_WRITES`: Set to "1" to enable write operations
- `LOG_LEVEL`: Set logging level
- `MCP_TRANSPORT`: Set transport protocol

### Example: Enable Writes
```bash
aas-mcp-server --component aas-repo --enable-writes
```

### Example: Custom OpenAPI Spec
```bash
aas-mcp-server --component submodel-repo --openapi ./my-custom-spec.yaml
```

## Claude Desktop Configuration

Add each component separately to your `claude_desktop_config.json`:

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
    },
    "concept-description-repo": {
      "command": "aas-mcp-server",
      "args": ["--component", "concept-description-repo", "--base-url", "http://localhost:8082"]
    },
    "aas-registry": {
      "command": "aas-mcp-server",
      "args": ["--component", "aas-registry", "--base-url", "http://localhost:8083"]
    }
  }
}
```

This allows Claude to access all AAS components simultaneously, each with its own dedicated tool set.

## OpenAPI Specifications

Place your OpenAPI specifications in the `openapi/` directory:
- `openapi/aas-repo.yaml` - AAS Repository spec
- `openapi/submodel-repo.yaml` - Submodel Repository spec
- `openapi/concept-description-repo.yaml` - Concept Description Repository spec
- `openapi/aas-registry.yaml` - AAS Registry spec

## Path Filtering & Overlays

The server supports optional path filtering and OpenAPI overlays to customize the API surface per component.

### Path Filtering

Filter the OpenAPI spec to include only specific paths and HTTP methods using environment variables:

| Component | Environment Variable |
|-----------|---------------------|
| aas-repo | `AAS_REPO_FILTER_PATHS` |
| submodel-repo | `SUBMODEL_REPO_FILTER_PATHS` |
| concept-description-repo | `CONCEPT_DESCRIPTION_REPO_FILTER_PATHS` |
| aas-registry | `AAS_REGISTRY_FILTER_PATHS` |
| submodel-registry | `SUBMODEL_REGISTRY_FILTER_PATHS` |

**Filter Format:**
- `/path` - include all HTTP methods for this path
- `/path:get` - include only GET method
- `/path:get,post` - include GET and POST methods
- Use semicolon (`;`) to separate multiple path filters

**Examples:**
```bash
# Expose only GET /shells
export AAS_REPO_FILTER_PATHS="/shells:get"

# Expose GET and POST for /shells, only GET for /shells/{aasIdentifier}
export AAS_REPO_FILTER_PATHS="/shells:get,post;/shells/{aasIdentifier}:get"

# Expose all methods for multiple paths
export AAS_REPO_FILTER_PATHS="/shells;/shells/{aasIdentifier}"

aas-mcp-server --component aas-repo
```

### OpenAPI Overlays

Apply [OpenAPI Overlay](https://github.com/OAI/Overlay-Specification) files to add custom extensions or modify the spec. Place overlay files in `openapi/overlays/` with the naming convention `{component}-overlay.yaml`.

Example overlay (`openapi/overlays/aas-repo-overlay.yaml`):
```yaml
overlay: 1.0.0
info:
  title: AAS Repository MCP Extensions
  version: 1.0.0
actions:
  - target: "$.paths['/shells'].get"
    update:
      x-mcp-tool:
        name: list_asset_administration_shells
        description: Returns all Asset Administration Shells
```

### Processing Order

1. Load the original OpenAPI spec
2. If filter paths env var is set, filter to only those paths
3. If overlay file exists, apply the overlay

This allows you to create a minimal, customized API surface without modifying the original OpenAPI files.

## Development

```bash
# Install dependencies
pip install -e .

# Run a specific component
aas-mcp-server --component aas-repo --log-level DEBUG
```
