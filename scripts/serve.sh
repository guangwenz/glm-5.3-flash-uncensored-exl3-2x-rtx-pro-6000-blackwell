#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env}"
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE; copy config/example.env to .env" >&2; exit 2; }
source "$ROOT/scripts/load-env.sh"
source "$ROOT/scripts/defaults.sh"
source "$ROOT/scripts/validate-config.sh"
"$ROOT/scripts/preflight.sh"
mkdir -p "$CACHE_DIR"
if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME")" != true ]] || { echo 'Container already running' >&2; exit 1; }
  docker rm "$CONTAINER_NAME" >/dev/null
fi
exec docker run -d --rm --name "$CONTAINER_NAME" \
  --init \
  --gpus "\"device=${GPU_DEVICES}\"" \
  --ipc=host --shm-size 32g \
  --publish "${BIND_ADDRESS}:${PORT}:8000" \
  --env HF_HUB_OFFLINE=1 \
  --env VLLM_ENGINE_READY_TIMEOUT_S=3600 \
  --env VLLM_B12X_GLM_NOPE_NVFP4=1 \
  --env VLLM_NVFP4_MLA_DYNAMIC_SCALE=0 \
  --env VLLM_NVFP4_MLA_SCALES_FILE=/opt/glm53/calibration/glm53_nvfp4_mla_outer_scales_mtp_power2_v2.json \
  --env VLLM_EXL3_PREFILL_BLOCK_M=128 \
  --env VLLM_USE_B12X_DCP_A2A=1 \
  --env VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=0 \
  --env VLLM_USE_BREAKABLE_CUDAGRAPH=1 \
  --env VLLM_ENABLE_PCIE_ALLREDUCE=1 \
  --env VLLM_PCIE_ALLREDUCE_BACKEND=cpp \
  --env OMP_NUM_THREADS=2 \
  --env NCCL_IB_DISABLE=1 \
  --env NCCL_P2P_LEVEL=4 \
  --env NCCL_DEBUG="$NCCL_DEBUG" \
  --volume "$MODEL_DIR:/model:ro" \
  --volume "$DRAFT_DIR:/draft:ro" \
  --volume "$CACHE_DIR:/cache" \
  "$IMAGE" serve /model \
  --served-model-name "$SERVED_MODEL_NAME" \
  --host 0.0.0.0 --port 8000 \
  --tensor-parallel-size 2 \
  --enable-expert-parallel \
  --decode-context-parallel-size 2 \
  --dcp-comm-backend a2a \
  --dtype bfloat16 \
  --load-format safetensors \
  --moe-backend b12x \
  --attention-backend B12X_MLA_SPARSE \
  --kv-cache-dtype nvfp4_ds_mla \
  --max-model-len "$MAX_MODEL_LEN" \
  --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS" \
  --max-num-seqs "$MAX_NUM_SEQS" \
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
  --enable-chunked-prefill \
  --no-enable-prefix-caching \
  --mamba-cache-mode none \
  --generation-config /model \
  --limit-mm-per-prompt "{\"image\":${MAX_IMAGES_PER_PROMPT},\"video\":0}" \
  --chat-template /opt/glm53/chat_template.multimodal.jinja \
  --reasoning-parser glm45 \
  --tool-call-parser glm47 \
  --enable-auto-tool-choice \
  --disable-custom-all-reduce
  # DFlash speculative decoding DISABLED 2026-09-19: draft/verify desyncs under
  # 2-agent concurrency (acceptance collapses to 0%, output degenerates to a
  # repetition wall). Re-enable by restoring the --speculative-config line.
