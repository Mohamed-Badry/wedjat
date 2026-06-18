#!/bin/bash
args=()
for arg in "$@"; do
  if [[ "$arg" != "--allow-pre-commit-input" && "$arg" != "--disable-gpu" ]]; then
    args+=("$arg")
  fi
done
exec flatpak run org.chromium.Chromium "${args[@]}"
