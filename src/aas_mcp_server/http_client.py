import os
import httpx

def build_async_client(base_url: str) -> httpx.AsyncClient:
    token = os.getenv("AAS_TOKEN")  # optional bearer token
    api_key = os.getenv("AAS_API_KEY")  # optional API key
    api_key_header = os.getenv("AAS_API_KEY_HEADER", "X-API-Key")

    headers = {"Accept": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"
    if api_key:
        headers[api_key_header] = api_key

    timeout = float(os.getenv("AAS_HTTP_TIMEOUT", "30"))
    return httpx.AsyncClient(base_url=base_url, headers=headers, timeout=timeout)
