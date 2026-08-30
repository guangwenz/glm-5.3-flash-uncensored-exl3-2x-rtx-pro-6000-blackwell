#!/usr/bin/env bash
set -euo pipefail
[[ "${EUID:-$(id -u)}" -ne 0 ]] || { echo 'Run as an unprivileged user.' >&2; exit 2; }
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] || { echo 'Create and review .env first.' >&2; exit 2; }
UNIT_DIR="$HOME/.config/systemd/user"; ENV_DIR="$HOME/.config/glm53-uncensored-exl3"; WANTS="$UNIT_DIR/default.target.wants"
for path in "$ROOT" "$UNIT_DIR" "$ENV_DIR" "$WANTS"; do
  [[ "$path" =~ ^/[A-Za-z0-9._/-]+$ ]] || { echo "Unsupported path: $path" >&2; exit 2; }
done
python3 - "$HOME" "$UNIT_DIR" "$ENV_DIR" "$WANTS" <<'PY'
from pathlib import Path
import os,sys
home=Path(sys.argv[1]).resolve()
for raw in sys.argv[2:]:
 p=Path(raw)
 try: p.relative_to(home)
 except ValueError: raise SystemExit(f'path escapes HOME: {p}')
 cur=home
 for part in p.relative_to(home).parts:
  cur=cur/part
  if cur.exists() and cur.is_symlink(): raise SystemExit(f'refusing symlinked path: {cur}')
for raw in sys.argv[2:]: Path(raw).mkdir(parents=True,exist_ok=True)
PY
install -m 600 "$ROOT/.env" "$ENV_DIR/env"
python3 - "$ROOT" "$ENV_DIR/env" "$ROOT/systemd/glm53-uncensored-exl3.service.in" "$UNIT_DIR/glm53-uncensored-exl3.service" <<'PY'
from pathlib import Path
import os,sys,tempfile
root,env,src,dst=sys.argv[1:]; target=Path(dst)
text=Path(src).read_text().replace('@REPO_DIR@',root).replace('@ENV_FILE@',env)
fd,tmp=tempfile.mkstemp(prefix='.glm53-unit-',dir=target.parent)
try:
 with os.fdopen(fd,'w') as f: f.write(text); f.flush(); os.fsync(f.fileno())
 os.chmod(tmp,0o644); os.replace(tmp,target)
finally:
 if os.path.exists(tmp): os.unlink(tmp)
PY
systemd-analyze --user verify "$UNIT_DIR/glm53-uncensored-exl3.service"
systemctl --user daemon-reload
systemctl --user enable glm53-uncensored-exl3.service
echo 'Installed and enabled. Start with: systemctl --user start glm53-uncensored-exl3.service'
echo "Optional pre-login startup: sudo loginctl enable-linger \"$USER\""
