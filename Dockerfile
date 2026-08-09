FROM node:20-bookworm-slim AS nse-mcp
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/* \
    && corepack enable \
    && git clone https://github.com/manitgupta/NSE-MCP.git NSE-MCP \
    && cd NSE-MCP && git checkout 8fe76bc51fc2beb5013eb252592b285be8e1b5c0 \
    && pnpm install --frozen-lockfile=false && pnpm run build

FROM python:3.11-slim
WORKDIR /app
COPY --from=node:20-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:20-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=nse-mcp /build/NSE-MCP /app/.vendor/NSE-MCP
COPY . /app
RUN pip install --no-cache-dir .
ENV SIGNALRELAY_HOST=0.0.0.0 \
    SIGNALRELAY_PORT=8000 \
    NSE_MCP_ENTRY=/app/.vendor/NSE-MCP/dist/index.js \
    NODE_BINARY=/usr/local/bin/node
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
