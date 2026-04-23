# AAS MCP Server

> OpenAPI-to-MCP bridge for Asset Administration Shell (AAS) APIs

Converts OpenAPI specifications into Model Context Protocol (MCP) tools, enabling LLMs to interact with AAS services.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## 🚀 Quick Start

### Prerequisites

1. **AAS OpenAPI Specifications** - [Download from GitHub](https://github.com/admin-shell-io/aas-specs)
2. **AAS Backend Server** - Eclipse BaSyx, FA³ST Service, SAP BNAC, etc.
3. **Python 3.12+** OR **Docker**

### Setup

1. **Get AAS Specifications**:
   ```bash
   mkdir specs && cd specs
   # Download from https://github.com/admin-shell-io/aas-specs/tree/main/schemas/openapi
   ```

2. **Create config.yaml**:
   ```yaml
   components:
     aas-repo:
       official_spec: specs/AssetAdministrationShellRepositoryServiceSpecification-V3.1.1_SSP-001.yaml
   ```

3. **Run**:
   ```bash
   # Docker (recommended)
   docker run \
     -v $(pwd)/config.yaml:/app/config/config.yaml \
     -v $(pwd)/specs:/app/specs \
     -e AAS_COMPONENT=aas-repo \
     -e AAS_BASE_URL=http://your-backend:8080 \
     -i aas-mcp-server

   # Or install locally
   pip install -e .
   aas-mcp-server --component aas-repo --base-url http://localhost:8080 --config config.yaml
   ```

## 📖 Configuration

### Basic (Official Spec Only)

```yaml
components:
  aas-repo:
    official_spec: specs/aas-repo-spec.yaml
```

### Filtered (Implementation-Specific)

Filter to only endpoints your backend supports:

```yaml
components:
  aas-repo:
    official_spec: specs/aas-repo-official.yaml
    implementation_spec: specs/basyx-supported-endpoints.yaml
```

Result: Only endpoints in **both** specs are exposed (intersection).

### With Curation

Control which operations are exposed:

```yaml
components:
  aas-repo:
    official_spec: specs/aas-repo-spec.yaml
    curation:
      allowlist:
        - [get, /shells]
        - [post, /shells]
        # Wildcards supported:
        - [get, "*"]              # All GET operations
        - [*, /shells]            # All methods on /shells
      aliases:
        GetAllAssetAdministrationShells: list_shells
```

See [config.yaml.example](config.yaml.example) for complete options.

## 🐳 Docker Usage

### Basic

```bash
docker run \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/specs:/app/specs \
  -e AAS_COMPONENT=aas-repo \
  -e AAS_BASE_URL=http://your-backend:8080 \
  -i aas-mcp-server
```

### Custom Config Path

```bash
docker run \
  -v $(pwd)/my-config.yaml:/custom/config.yaml \
  -v $(pwd)/specs:/app/specs \
  -e CONFIG_PATH=/custom/config.yaml \
  -e AAS_COMPONENT=aas-repo \
  -e AAS_BASE_URL=http://your-backend:8080 \
  -i aas-mcp-server
```

### Multiple Volume Mounts

```bash
docker run \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/specs:/app/specs \
  -v $(pwd)/overlays:/app/overlays \
  -e AAS_COMPONENT=aas-repo \
  -e AAS_BASE_URL=http://your-backend:8080 \
  -i aas-mcp-server
```

## 🎯 Supported Components

- `aas-repo` - Asset Administration Shell Repository
- `submodel-repo` - Submodel Repository  
- `aas-registry` - AAS Registry
- `submodel-registry` - Submodel Registry

## 📚 Documentation

- [config.yaml.example](config.yaml.example) - Complete configuration template
- [CLAUDE.md](CLAUDE.md) - Architecture guide
- [docs/TESTING_COMPREHENSIVE.md](docs/TESTING_COMPREHENSIVE.md) - Testing guide

## 🔐 Security

- **Read-only by default** - Write operations disabled unless `--enable-writes`
- **Allowlist-based** - Only explicitly allowed operations exposed
- **Pagination limits** - Max 100 items per request

## 🆘 Troubleshooting

### "Configuration file not found"

**Provide config via**:
- `--config /path/to/config.yaml`
- `CONFIG_PATH` environment variable
- Default: `/app/config/config.yaml`

### "official_spec file not found"

**Check**:
- Paths in config.yaml are correct
- Specs are mounted (Docker): `-v $(pwd)/specs:/app/specs`

## 📄 License

Apache License 2.0 - See [LICENSE](LICENSE)
