# Quick Start Guide

Get started with AAS MCP Server in 5 minutes!

## Prerequisites

- Python 3.12 or higher
- pip package manager

## Installation

```bash
pip install aas-mcp-server
```

Or install from source:
```bash
git clone <repository-url>
cd aas-mcp-server
pip install -e .
```

## Quick Test

### 1. Verify Installation

```bash
aas-mcp-server --help
```

You should see the help output with all available options.

### 2. Run a Component

```bash
# Start the AAS Repository component
aas-mcp-server --component aas-repo --log-level DEBUG
```

**Note:** This will fail if you don't have an AAS Repository running at http://localhost:8080. That's okay for now - we're just testing the CLI works.

## Next Steps

### Option A: Use with Existing AAS Services

If you already have AAS services running:

```bash
# Point to your AAS Repository
aas-mcp-server --component aas-repo --base-url http://your-server:8080

# Point to your Submodel Repository
aas-mcp-server --component submodel-repo --base-url http://your-server:8081
```

### Option B: Add Your OpenAPI Specs

1. **Replace placeholder specs** with your actual OpenAPI specifications:

```bash
# Copy your specs to the openapi/ directory
cp /path/to/your/aas-repo-spec.yaml openapi/aas-repo.yaml
cp /path/to/your/submodel-spec.yaml openapi/submodel-repo.yaml
```

2. **Run with your specs**:

```bash
aas-mcp-server --component aas-repo --base-url http://localhost:8080
```

### Option C: Use with Claude Desktop

1. **Install the server**:
```bash
pip install aas-mcp-server
```

2. **Update Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "aas-repo": {
      "command": "aas-mcp-server",
      "args": ["--component", "aas-repo", "--base-url", "http://localhost:8080"]
    }
  }
}
```

3. **Restart Claude Desktop**

4. **Test it**: Ask Claude "What tools do you have available?" - you should see AAS Repository tools.

## Component Reference

| Component | Default Port | Description |
|-----------|-------------|-------------|
| `aas-repo` | 8080 | AAS Repository - Manage Asset Administration Shells |
| `submodel-repo` | 8081 | Submodel Repository - Manage Submodels |
| `concept-description-repo` | 8082 | Concept Description Repository |
| `aas-registry` | 8083 | AAS Registry - Discovery and registration |

## Common Commands

```bash
# Run with defaults
aas-mcp-server --component aas-repo

# Run with custom URL
aas-mcp-server --component aas-repo --base-url http://prod:8080

# Enable write operations
aas-mcp-server --component aas-repo --enable-writes

# Use custom OpenAPI spec
aas-mcp-server --component aas-repo --openapi ./my-spec.yaml

# Debug mode
aas-mcp-server --component aas-repo --log-level DEBUG
```

## Environment Variables

Instead of command-line arguments, you can use environment variables:

```bash
export AAS_BASE_URL=http://localhost:8080
export LOG_LEVEL=DEBUG
aas-mcp-server --component aas-repo
```

## Troubleshooting

### "argument --component is required"
You must specify which component to run:
```bash
aas-mcp-server --component aas-repo
```

### "FileNotFoundError: openapi/aas-repo.yaml"
The OpenAPI spec file is missing or uses a placeholder. Either:
- Add your actual spec to `openapi/aas-repo.yaml`, or
- Use `--openapi` to point to your spec:
  ```bash
  aas-mcp-server --component aas-repo --openapi /path/to/spec.yaml
  ```

### Connection errors
Make sure your AAS service is running at the specified URL:
```bash
# Test the service
curl http://localhost:8080
```

## What's Next?

- **Read [README.md](README.md)** for detailed usage instructions
- **Check [ARCHITECTURE.md](ARCHITECTURE.md)** to understand the multi-component design
- **See [openapi/README.md](openapi/README.md)** for OpenAPI spec guidelines
- **Review [claude_desktop_config.example.json](claude_desktop_config.example.json)** for Claude integration

## Example: Running All Components

```bash
# Terminal 1 - AAS Repository
aas-mcp-server --component aas-repo --base-url http://localhost:8080

# Terminal 2 - Submodel Repository
aas-mcp-server --component submodel-repo --base-url http://localhost:8081

# Terminal 3 - Concept Description Repository
aas-mcp-server --component concept-description-repo --base-url http://localhost:8082

# Terminal 4 - AAS Registry
aas-mcp-server --component aas-registry --base-url http://localhost:8083
```

Or configure all in Claude Desktop to access all components simultaneously!

## Getting Help

- Check existing documentation files
- Run `aas-mcp-server --help`
- Enable debug logging: `--log-level DEBUG`

