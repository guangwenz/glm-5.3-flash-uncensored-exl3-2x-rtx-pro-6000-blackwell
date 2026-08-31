#!/usr/bin/env bash
# Strict dotenv reader: operator-selected ENV_FILE is parsed as literal data, never sourced.
set -euo pipefail
_ALLOWED_KEYS=' MODEL_DIR DRAFT_DIR CACHE_DIR GPU_DEVICES BIND_ADDRESS PORT CONTAINER_NAME SERVED_MODEL_NAME MAX_MODEL_LEN MAX_NUM_BATCHED_TOKENS MAX_NUM_SEQS DFLASH_SPECULATIVE_TOKENS GPU_MEMORY_UTILIZATION MAX_IMAGES_PER_PROMPT NCCL_DEBUG '
declare -A _SEEN_ENV_KEYS=()
while IFS= read -r _line || [[ -n "$_line" ]]; do
  _line="${_line%$'\r'}"
  [[ -z "$_line" || "$_line" == '#'* ]] && continue
  [[ "$_line" == *'='* ]] || { echo "Invalid dotenv line: $_line" >&2; return 2; }
  _key="${_line%%=*}"; _value="${_line#*=}"
  [[ "$_key" =~ ^[A-Z][A-Z0-9_]*$ ]] || { echo "Invalid dotenv key: $_key" >&2; return 2; }
  [[ "$_ALLOWED_KEYS" == *" $_key "* ]] || { echo "Unsupported dotenv key: $_key" >&2; return 2; }
  [[ -z "${_SEEN_ENV_KEYS[$_key]+x}" ]] || { echo "Duplicate dotenv key: $_key" >&2; return 2; }
  _SEEN_ENV_KEYS[$_key]=1
  printf -v "$_key" '%s' "$_value"; export "${_key?}"
done < "$ENV_FILE"
unset _ALLOWED_KEYS _SEEN_ENV_KEYS _line _key _value
