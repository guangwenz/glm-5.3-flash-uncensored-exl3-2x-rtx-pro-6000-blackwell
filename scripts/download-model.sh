#!/usr/bin/env bash
set -euo pipefail
[[ "${EUID:-$(id -u)}" -ne 0 ]] || { echo 'Run as an unprivileged user.' >&2; exit 2; }
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env}"
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE; copy config/example.env to .env" >&2; exit 2; }
source "$ROOT/scripts/load-env.sh"
[[ "${I_ACCEPT_SHAPLEYMCG_LICENSE:-}" == yes ]] || { echo 'Review ShapleyMCG License 1.0, then set I_ACCEPT_SHAPLEYMCG_LICENSE=yes.' >&2; exit 2; }
[[ "${I_ACCEPT_UNCENSORED_MODEL_TERMS:-}" == yes ]] || { echo 'Review the gated uncensored checkpoint card, then set I_ACCEPT_UNCENSORED_MODEL_TERMS=yes.' >&2; exit 2; }
[[ "${I_ACCEPT_DFLASH2_CC_BY_NC_ND_4_0:-}" == yes ]] || { echo 'DFlash2 is CC BY-NC-ND 4.0 and non-commercial; set I_ACCEPT_DFLASH2_CC_BY_NC_ND_4_0=yes after review.' >&2; exit 2; }
for _v in MODEL_DIR DRAFT_DIR; do
  [[ "${!_v:-}" == /* && "${!_v}" == "$(realpath -m -- "${!_v}")" ]] || { echo "$_v must be a canonical absolute path" >&2; exit 2; }
  [[ "${!_v}" != / && "${!_v}" != /dev* && "${!_v}" != /proc* && "${!_v}" != /sys* ]] || { echo "Unsafe $_v" >&2; exit 2; }
done
command -v hf >/dev/null || { echo 'Missing Hugging Face hf CLI.' >&2; exit 1; }
hf --version
python3 - "$MODEL_DIR" "$DRAFT_DIR" <<'PY'
from pathlib import Path
import os,sys
items=[(Path(sys.argv[1]),'neko-legends/GLM-5.3-Flash-Uncensored-EXL3@1fac3dbe6269a399ce5378261cdf250fde706180'),(Path(sys.argv[2]),'incoai/GLM-5.3-Flash-DFlash2@7d74cdd881ed7e32c31175984a67823127b66cfe')]
a,b=(x[0] for x in items)
if a==b or a in b.parents or b in a.parents: raise SystemExit('MODEL_DIR and DRAFT_DIR must be disjoint')
for path,pin in items:
    cur=Path('/')
    for part in path.parts[1:]:
        cur/=part
        if cur.exists() and cur.is_symlink(): raise SystemExit(f'refusing symlinked path component: {cur}')
    marker=path/'.recipe-download-pin'
    if path.exists() and not path.is_dir(): raise SystemExit(f'not a directory: {path}')
    if path.exists() and any(path.iterdir()):
        if not marker.is_file() or marker.read_text().strip()!=pin:
            raise SystemExit(f'non-empty destination lacks matching resume marker: {path}')
    path.mkdir(parents=True,exist_ok=True)
    tmp=path/'.recipe-download-pin.tmp'; tmp.write_text(pin+'\n'); os.replace(tmp,marker)
PY
hf download neko-legends/GLM-5.3-Flash-Uncensored-EXL3 --revision 1fac3dbe6269a399ce5378261cdf250fde706180 --local-dir "$MODEL_DIR"
hf download incoai/GLM-5.3-Flash-DFlash2 --revision 7d74cdd881ed7e32c31175984a67823127b66cfe --local-dir "$DRAFT_DIR"
printf '%s\n' 'neko-legends/GLM-5.3-Flash-Uncensored-EXL3@1fac3dbe6269a399ce5378261cdf250fde706180' > "$MODEL_DIR/RECIPE_PIN.txt"
printf '%s\n' 'incoai/GLM-5.3-Flash-DFlash2@7d74cdd881ed7e32c31175984a67823127b66cfe' > "$DRAFT_DIR/RECIPE_PIN.txt"
echo 'Downloads complete. Run scripts/preflight.sh; full hash verification reads about 178 GB.'
