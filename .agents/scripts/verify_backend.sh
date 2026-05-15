#!/usr/bin/env bash
# Fast backend verification script
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$DIR" || exit 1

# Using uv to run tools on the src/, scripts/, and notebooks/ directories
set +e
OUTPUT=$(uv run ruff check src/ scripts/ notebooks/ 2>&1 && uv run ruff format --check src/ scripts/ notebooks/ 2>&1)
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -ne 0 ]; then
    echo "Backend verification failed." >&2
    echo "$OUTPUT" >&2
    exit 1
fi

echo "Backend verification passed." >&2
exit 0