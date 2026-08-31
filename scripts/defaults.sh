#!/usr/bin/env bash
# Exact qualified defaults. Source only after scripts/load-env.sh.
set -euo pipefail
CONTAINER_NAME="${CONTAINER_NAME:-glm53-flash-uncensored-exl3}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-glm-5.3-flash-uncensored-exl3}"
BIND_ADDRESS="${BIND_ADDRESS:-127.0.0.1}"
PORT="${PORT:-8000}"
GPU_DEVICES="${GPU_DEVICES:-0,1}"
CACHE_DIR="${CACHE_DIR:-${ROOT}/.cache}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-262144}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-1024}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-8}"
DFLASH_SPECULATIVE_TOKENS="${DFLASH_SPECULATIVE_TOKENS:-3}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.979}"
MAX_IMAGES_PER_PROMPT="${MAX_IMAGES_PER_PROMPT:-1}"
NCCL_DEBUG="${NCCL_DEBUG:-WARN}"
# shellcheck disable=SC2034 # consumed by callers after this file is sourced
IMAGE='verdictai/glm53-flash-exl3-k4:r19-sm120-tp2-ep2-dcp2-v84-dflash2@sha256:0f1cdcc8891f1cc3a444121eb61d366289a1cbba285f0892dcbb24bc94961692'
