#!/usr/bin/env bash
set -euo pipefail

# Requires: npm i -g @redocly/cli
redocly bundle openapi/openapi.yaml -o openapi/openapi.resolved.yaml
echo "Wrote openapi/openapi.resolved.yaml"
