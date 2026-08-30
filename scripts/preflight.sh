#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env}"
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 2; }
source "$ROOT/scripts/load-env.sh"
source "$ROOT/scripts/defaults.sh"
source "$ROOT/scripts/validate-config.sh"
for c in docker nvidia-smi python3 sha256sum; do command -v "$c" >/dev/null || { echo "FAIL missing command: $c" >&2; exit 1; }; done
docker info >/dev/null || { echo 'FAIL Docker daemon unavailable' >&2; exit 1; }
docker image inspect "$IMAGE" >/dev/null 2>&1 || docker pull "$IMAGE"
actual_digest=$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')
[[ "$actual_digest" == *@sha256:0f1cdcc8891f1cc3a444121eb61d366289a1cbba285f0892dcbb24bc94961692 ]] || { echo "FAIL image digest mismatch: $actual_digest" >&2; exit 1; }
python3 - "$MODEL_DIR" "$DRAFT_DIR" <<'PY'
import json,sys
from pathlib import Path
m,d=map(Path,sys.argv[1:])
c=json.loads((m/'config.json').read_text()); q=json.loads((m/'quantization_config.json').read_text()); dc=json.loads((d/'config.json').read_text())
if c.get('model_type')!='glm5_next' or c.get('architectures')!=['Glm5NextForConditionalGeneration']: raise SystemExit('FAIL unexpected target architecture')
if q.get('quant_method')!='exl3' or q.get('bits')!=4: raise SystemExit('FAIL target is not the pinned 4-bit EXL3 format')
if dc.get('architectures')!=['DFlash2DraftModel'] or dc.get('model_type')!='qwen3': raise SystemExit('FAIL unexpected DFlash2 architecture')
PY
echo 'Verifying exact model files (this intentionally reads about 178 GB)...'
(cd "$MODEL_DIR" && sha256sum --quiet -c "$ROOT/manifests/model.sha256")
(cd "$DRAFT_DIR" && sha256sum --quiet -c "$ROOT/manifests/dflash2.sha256")
IFS=',' read -r -a gpus <<< "$GPU_DEVICES"
[[ ${#gpus[@]} -eq 2 && ${gpus[0]} != "${gpus[1]}" ]] || { echo 'FAIL select exactly two distinct GPUs' >&2; exit 1; }
for i in "${gpus[@]}"; do
  row=$(nvidia-smi -i "$i" --query-gpu=index,uuid,name,memory.total,memory.free,pci.bus_id --format=csv,noheader,nounits)
  echo "GPU $row"
  name=$(cut -d, -f3 <<<"$row" | xargs); total=$(cut -d, -f4 <<<"$row" | xargs); free=$(cut -d, -f5 <<<"$row" | xargs)
  [[ "$name" == *'RTX PRO 6000'* && "$name" == *'Blackwell'* ]] || { echo "FAIL GPU $i is not RTX PRO 6000 Blackwell" >&2; exit 1; }
  (( total >= 97000 )) || { echo "FAIL GPU $i has only ${total} MiB total" >&2; exit 1; }
  (( free >= 88000 )) || { echo "FAIL GPU $i has only ${free} MiB free; stop other GPU workloads first" >&2; exit 1; }
done
avail_kib=$(python3 - <<'PY'
for line in open('/proc/meminfo'):
    if line.startswith('MemAvailable:'):
        print(line.split()[1]); break
PY
)
(( avail_kib >= 32*1024*1024 )) || { echo 'FAIL less than 32 GiB host memory available' >&2; exit 1; }
nvidia-smi topo -p2p r || true
echo "Image: $actual_digest"
echo 'PREFLIGHT PASS'
