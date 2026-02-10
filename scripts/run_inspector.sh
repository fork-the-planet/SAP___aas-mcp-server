#!/usr/bin/env bash
set -euo pipefail

# Example:
# AAS_BASE_URL=http://localhost:8080 ./scripts/run_inspector.sh

npx @modelcontextprotocol/inspector -- python -m aas_mcp.cli \
  --base-url "${AAS_BASE_URL:-http://localhost:8080}" \
  --openapi "${AAS_OPENAPI_PATH:-openapi/openapi.resolved.yaml}"
