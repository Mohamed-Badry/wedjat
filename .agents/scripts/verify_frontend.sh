#!/usr/bin/env bash
# Fast frontend verification script
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../frontend" && pwd)"
cd "$DIR" || exit 1

# Redirect noisy output to stderr, keep stdout clean for the agent
set +e
OUTPUT=$(bun run format 2>&1 && bun run lint 2>&1 && bun run check 2>&1)
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -ne 0 ]; then
    echo "Frontend verification failed." >&2
    echo "$OUTPUT" >&2
    exit 1
fi

echo "Frontend verification passed." >&2
exit 0