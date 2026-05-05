# syntax=docker/dockerfile:1.7
FROM oven/bun:1.3.5-debian

WORKDIR /app

COPY package.json bun.lock* ./
RUN --mount=type=cache,target=/root/.bun/install/cache,sharing=locked \
    bun install --frozen-lockfile

COPY . .

CMD ["bun", "run", "dev", "--", "--host", "0.0.0.0"]
