FROM python:3.12-slim

WORKDIR /app

# Copy and install Python package
COPY pyproject.toml README.md /app/
COPY src /app/src
RUN pip install --no-cache-dir .

# Note: config.yaml and OpenAPI specs must be provided via volume mounts
# See README.md for usage instructions

ENV MCP_TRANSPORT=stdio
# MCP servers over stdio need unbuffered output
ENV PYTHONUNBUFFERED=1

# Default environment variables (can be overridden)
ENV AAS_COMPONENT=aas-repo
ENV AAS_BASE_URL=http://host.docker.internal:8081

# Set working directory to /app
WORKDIR /app

CMD ["sh", "-c", "aas-mcp-server --component ${AAS_COMPONENT} --base-url ${AAS_BASE_URL}"]
