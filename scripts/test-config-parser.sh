#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
marker="$tmp/should-not-exist"
printf 'MODEL_DIR=%s\n' "\$(touch $marker)" > "$tmp/literal.env"
(
  ENV_FILE="$tmp/literal.env"
  # shellcheck source=scripts/load-env.sh
  source "$ROOT/scripts/load-env.sh"
  [[ "$MODEL_DIR" == "\$(touch $marker)" ]]
)
[[ ! -e "$marker" ]] || { echo 'dotenv value executed unexpectedly' >&2; exit 1; }
printf 'UNSUPPORTED_KEY=value\n' > "$tmp/unsupported.env"
if (ENV_FILE="$tmp/unsupported.env"; source "$ROOT/scripts/load-env.sh") 2>/dev/null; then
  echo 'unsupported dotenv key was accepted' >&2; exit 1
fi
printf 'PORT=8000\nPORT=8001\n' > "$tmp/duplicate.env"
if (ENV_FILE="$tmp/duplicate.env"; source "$ROOT/scripts/load-env.sh") 2>/dev/null; then
  echo 'duplicate dotenv key was accepted' >&2; exit 1
fi
mkdir -p "$tmp/model" "$tmp/draft" "$tmp/cache"
printf '{}\n' > "$tmp/model/config.json"
printf '{}\n' > "$tmp/draft/config.json"
validate_depth() (
  MODEL_DIR="$tmp/model" DRAFT_DIR="$tmp/draft" CACHE_DIR="$tmp/cache"
  GPU_DEVICES=0,1 BIND_ADDRESS=127.0.0.1 PORT=8000
  CONTAINER_NAME=test SERVED_MODEL_NAME=test MAX_MODEL_LEN=262144
  MAX_NUM_BATCHED_TOKENS=1024 MAX_NUM_SEQS=8
  DFLASH_SPECULATIVE_TOKENS="$1" GPU_MEMORY_UTILIZATION=0.979
  MAX_IMAGES_PER_PROMPT=5 NCCL_DEBUG=WARN
  source "$ROOT/scripts/defaults.sh"
  source "$ROOT/scripts/validate-config.sh"
)
validate_depth 3
if validate_depth 03 2>/dev/null; then
  echo 'non-canonical DFlash depth was accepted and would produce invalid JSON' >&2; exit 1
fi
echo 'strict dotenv tests passed'
