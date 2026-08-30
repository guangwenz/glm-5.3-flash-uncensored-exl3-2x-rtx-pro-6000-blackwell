#!/usr/bin/env bash
# Validate public recipe configuration. Source after defaults.
set -euo pipefail
[[ "${EUID:-$(id -u)}" -ne 0 ]] || { echo 'Run as an unprivileged user, not root.' >&2; return 2; }
for _pair in MODEL_DIR:"${MODEL_DIR:-}" DRAFT_DIR:"${DRAFT_DIR:-}" CACHE_DIR:"${CACHE_DIR:-}"; do
  _key="${_pair%%:*}"; _path="${_pair#*:}"
  [[ "$_path" == /* && "$_path" != / && "$_path" != /dev* && "$_path" != /proc* && "$_path" != /sys* ]] || { echo "$_key must be a safe absolute path" >&2; return 2; }
  [[ "$_path" == "$(realpath -m -- "$_path")" ]] || { echo "$_key must use its canonical spelling: $_path" >&2; return 2; }
done
[[ -f "$MODEL_DIR/config.json" ]] || { echo 'MODEL_DIR must contain config.json' >&2; return 2; }
[[ -f "$DRAFT_DIR/config.json" ]] || { echo 'DRAFT_DIR must contain config.json' >&2; return 2; }
[[ "$GPU_DEVICES" =~ ^[0-9]+,[0-9]+$ ]] || { echo 'GPU_DEVICES must contain exactly two indices, e.g. 0,2' >&2; return 2; }
IFS=',' read -r _gpu_a _gpu_b <<< "$GPU_DEVICES"; [[ "$_gpu_a" != "$_gpu_b" ]] || { echo 'GPU indices must be distinct' >&2; return 2; }
[[ "$CONTAINER_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || { echo 'Invalid CONTAINER_NAME' >&2; return 2; }
[[ "$SERVED_MODEL_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9._:/-]*$ ]] || { echo 'Invalid SERVED_MODEL_NAME' >&2; return 2; }
for _v in PORT MAX_MODEL_LEN MAX_NUM_BATCHED_TOKENS MAX_NUM_SEQS MAX_IMAGES_PER_PROMPT; do
  [[ "${!_v}" =~ ^[0-9]+$ ]] || { echo "$_v must be an integer" >&2; return 2; }
done
(( PORT>=1 && PORT<=65535 )) || { echo 'PORT must be 1..65535' >&2; return 2; }
(( MAX_MODEL_LEN==262144 )) || { echo 'Qualified profile requires MAX_MODEL_LEN=262144' >&2; return 2; }
(( MAX_NUM_BATCHED_TOKENS==1024 )) || { echo 'Qualified profile requires MAX_NUM_BATCHED_TOKENS=1024' >&2; return 2; }
(( MAX_NUM_SEQS==8 )) || { echo 'Qualified profile requires MAX_NUM_SEQS=8' >&2; return 2; }
(( MAX_IMAGES_PER_PROMPT==1 )) || { echo 'Qualified profile requires MAX_IMAGES_PER_PROMPT=1' >&2; return 2; }
[[ "$NCCL_DEBUG" =~ ^(VERSION|WARN|INFO|TRACE|ABORT)$ ]] || { echo 'Invalid NCCL_DEBUG' >&2; return 2; }
python3 - "$BIND_ADDRESS" "$GPU_MEMORY_UTILIZATION" <<'PY'
import ipaddress,sys
try: a=ipaddress.ip_address(sys.argv[1])
except ValueError as e: raise SystemExit(f'BIND_ADDRESS must be a literal IPv4 address: {e}')
if a.version != 4: raise SystemExit('BIND_ADDRESS must be IPv4')
try: u=float(sys.argv[2])
except ValueError: raise SystemExit('GPU_MEMORY_UTILIZATION must be numeric')
if not 0 < u <= 0.979: raise SystemExit('GPU_MEMORY_UTILIZATION must be >0 and <=0.979')
PY
unset _pair _key _path _gpu_a _gpu_b _v
