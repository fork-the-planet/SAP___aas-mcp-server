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

## Development

```bash
# Install dependencies
pip install -e .

# Run a specific component
aas-mcp-server --component aas-repo --log-level DEBUG
```
