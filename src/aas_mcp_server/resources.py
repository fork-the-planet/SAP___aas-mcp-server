AAS_MCP_RESOURCE_INTRO = """\
This MCP server exposes a curated subset of the AAS Repository API.

Defaults:
- Readonly-by-default (set AAS_MCP_ENABLE_WRITES=1 to enable write operations)
- Pagination limit is capped to prevent huge responses

Typical flow:
1) list_shells (optionally filtered)
2) get_shell_by_id (if exposed)
"""
