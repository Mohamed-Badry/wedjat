# syntax=docker/dockerfile:1.7
# Stage 1: Build
FROM oven/bun:1.3.5-debian AS builder

WORKDIR /app

COPY package.json bun.lock* ./
RUN --mount=type=cache,target=/root/.bun/install/cache,sharing=locked \
    bun install --frozen-lockfile

COPY . .
RUN bun run build

# Stage 2: Runtime
FROM oven/bun:1.3.5-slim

# Install curl for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN groupadd -r svelte && useradd -m -r -g svelte svelte

COPY --from=builder --chown=svelte:svelte /app/build ./build
COPY --from=builder --chown=svelte:svelte /app/node_modules ./node_modules
COPY --from=builder --chown=svelte:svelte /app/package.json ./package.json

USER svelte

ENV PORT=5173
ENV NODE_ENV=production

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5173/ || exit 1

CMD ["bun", "run", "build/index.js"]
