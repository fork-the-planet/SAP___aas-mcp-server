FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY openapi /app/openapi

RUN pip install --no-cache-dir .

ENV MCP_TRANSPORT=stdio
CMD ["aas-mcp", "--base-url", "http://host.docker.internal:8080", "--openapi", "openapi/openapi.resolved.yaml"]
