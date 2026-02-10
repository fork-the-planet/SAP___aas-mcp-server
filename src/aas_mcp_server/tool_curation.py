from typing import Any, Dict, Set, Tuple

# Minimal starter allowlist (expand as you add support)
DEFAULT_ALLOWLIST: Set[Tuple[str, str]] = {
    ("get", "/shells"),
    # ("get", "/shells/{aasIdentifier}"),  # example if present in your spec
}

# operations considered "writes"
WRITE_METHODS = {"post", "put", "patch", "delete"}

VALID_METHODS: Set[str] = {"get", "post", "put", "patch", "delete"}

# Friendly aliases (optional, but strongly recommended)
OPERATION_ID_ALIASES = {
    "GetAllAssetAdministrationShells": "list_shells",
    # Add more operationIds here...
}

def curate_openapi_spec(spec: Dict[str, Any], enable_writes: bool) -> Dict[str, Any]:
    out = dict(spec)

    paths = out.get("paths", {})
    new_paths: Dict[str, Any] = {}

    for path, path_item in paths.items():
        new_item: Dict[str, Any] = {}
        for method, op in (path_item or {}).items():
            m = method.lower()
            if m not in VALID_METHODS:
                continue

            # 1) Allowlist filter (keeps tool surface stable)
            if (m, path) not in DEFAULT_ALLOWLIST:
                continue

            # 2) Readonly-by-default safety gate
            if (m in WRITE_METHODS) and not enable_writes:
                continue

            op = dict(op or {})

            # 3) Rename tool via operationId aliasing (LLM-friendly)
            op_id = op.get("operationId")
            if op_id in OPERATION_ID_ALIASES:
                op["operationId"] = OPERATION_ID_ALIASES[op_id]

            # 4) Cap limit parameter (defensive)
            op = _cap_limit_parameter(op, max_limit=100)

            new_item[m] = op

        if new_item:
            new_paths[path] = new_item

    out["paths"] = new_paths
    return out

def _cap_limit_parameter(op: Dict[str, Any], max_limit: int) -> Dict[str, Any]:
    params = op.get("parameters") or []
    new_params = []
    for p in params:
        p2 = dict(p)
        schema = p2.get("schema")
        if isinstance(schema, dict) and p2.get("name") in {"limit", "Limit"}:
            schema = dict(schema)
            schema["maximum"] = max_limit
            p2["schema"] = schema
        new_params.append(p2)
    op["parameters"] = new_params
    return op
