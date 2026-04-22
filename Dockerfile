FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY openapi /app/openapi

RUN pip install --no-cache-dir .

ENV MCP_TRANSPORT=stdio
# Default component is aas-repo, override with --build-arg COMPONENT=<component-name>
# or set via docker run environment variables
ARG COMPONENT=aas-repo
ARG BASE_URL=http://host.docker.internal:8080

ENV AAS_COMPONENT=${COMPONENT}
ENV AAS_BASE_URL=${BASE_URL}

CMD ["sh", "-c", "aas-mcp-server --component ${AAS_COMPONENT} --base-url ${AAS_BASE_URL}"]
