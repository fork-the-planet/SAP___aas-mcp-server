# Environment variable for enabling writes
ENV_VAR_ENABLE_WRITES = "AAS_MCP_ENABLE_WRITES"
ENV_VAR_ENABLE_WRITES_VALUE = "1"

# Resource introduction text
AAS_MCP_RESOURCE_INTRO = f"""\
This MCP server exposes a curated subset of the AAS Repository API.

Defaults:
- Readonly-by-default (set {ENV_VAR_ENABLE_WRITES}={ENV_VAR_ENABLE_WRITES_VALUE} to enable write operations)
- Pagination limit is capped to prevent huge responses

Typical flow:
1) list_shells (optionally filtered)
2) get_shell_by_id (if exposed)
"""
