#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
bash -n scripts/*.sh
PYTHONPYCACHEPREFIX="$(mktemp -d)" python3 -m py_compile scripts/*.py benchmarks/*.py
scripts/test-config-parser.sh
if command -v shellcheck >/dev/null; then
  shellcheck scripts/*.sh
elif command -v uvx >/dev/null; then
  uvx --from shellcheck-py==0.11.0.1 shellcheck scripts/*.sh
else
  echo 'shellcheck is required (or uvx for the pinned shellcheck-py fallback)' >&2; exit 1
fi
python3 - <<'PY'
from pathlib import Path
import hashlib,json,re,subprocess
root=Path('.')
required=[
 'README.md','ATTRIBUTIONS.md','THIRD_PARTY_NOTICES.md','PROVENANCE.md','NOTICE','LICENSE',
 'THIRD_PARTY_LICENSES/ShapleyMCG-LICENSE-1.0.txt',
 'THIRD_PARTY_LICENSES/ZAI-GLM-5.3-Flash-BF16-MIT.txt',
 'THIRD_PARTY_LICENSES/CC-BY-NC-ND-4.0.txt',
 'manifests/model.sha256','manifests/dflash2.sha256','manifests/runtime-image-provenance.json',
 'docs/BENCHMARKS.md','docs/TROUBLESHOOTING.md','benchmarks/README.md',
 'benchmarks/performance_benchmark.py','benchmarks/generate_humanevalplus.py','benchmarks/Dockerfile.evalplus','benchmarks/requirements-evalplus.txt','benchmarks/bfcl-local.patch',
]
for name in required:
 if not (root/name).is_file(): raise SystemExit(f'missing {name}')
expected={
 'THIRD_PARTY_LICENSES/ShapleyMCG-LICENSE-1.0.txt':'9a354667162e40201fa556e29ae7a327cdb112eacaa8ef100106e6063635e28a',
 'THIRD_PARTY_LICENSES/ZAI-GLM-5.3-Flash-BF16-MIT.txt':'30b85b6b9659f2e78aa259f8faf5d920a68dee7c9ced3fa6dba1f19f2bc4fca1',
 'THIRD_PARTY_LICENSES/CC-BY-NC-ND-4.0.txt':'f7f28b8c7a1af76b9874ca6d040e8b1eb6768fd1043106c9d315090ea96754e7',
}
for name,want in expected.items():
 got=hashlib.sha256((root/name).read_bytes()).hexdigest()
 if got!=want: raise SystemExit(f'license hash mismatch: {name}: {got}')
for name,count in [('manifests/model.sha256',106),('manifests/dflash2.sha256',4)]:
 rows=(root/name).read_text().splitlines()
 if len(rows)!=count: raise SystemExit(f'{name} has {len(rows)} rows, expected {count}')
 if any(not re.fullmatch(r'[0-9a-f]{64}  [^\r\n]+',r) for r in rows): raise SystemExit(f'invalid SHA-256 manifest row in {name}')
runtime_provenance=root/'manifests/runtime-image-provenance.json'
json.loads(runtime_provenance.read_text())
if hashlib.sha256(runtime_provenance.read_bytes()).hexdigest()!='cf4b00958987cc50f94641592b1a8d74874adb4d671861ce12dd5e8f2907d907': raise SystemExit('runtime image provenance hash mismatch')
for md in root.rglob('*.md'):
 for target in re.findall(r'\[[^]]*\]\(([^)]+)\)',md.read_text()):
  if target.startswith(('#','http://','https://','mailto:')): continue
  local=(md.parent/target.split('#',1)[0]).resolve()
  if not local.exists(): raise SystemExit(f'broken local Markdown link in {md}: {target}')
if 'evalplus==0.3.1' not in (root/'benchmarks/requirements-evalplus.txt').read_text().splitlines(): raise SystemExit('EvalPlus lock is not pinned')
if not (root/'benchmarks/Dockerfile.evalplus').read_text().startswith('FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6\n'): raise SystemExit('EvalPlus base image is not digest-pinned')
all_text='\n'.join(p.read_text(errors='ignore') for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and '.cache' not in p.parts)
for pin in [
 '1fac3dbe6269a399ce5378261cdf250fde706180',
 '7d74cdd881ed7e32c31175984a67823127b66cfe',
 'sha256:0f1cdcc8891f1cc3a444121eb61d366289a1cbba285f0892dcbb24bc94961692',
 'bd5321c1cfd4b8d352ef380e3158c64886039d03',
 'cf4b00958987cc50f94641592b1a8d74874adb4d671861ce12dd5e8f2907d907',
]:
 if pin not in all_text: raise SystemExit(f'missing immutable pin: {pin}')
notice='This work includes or was produced using ShapleyMcg, created by Brandon M. Music'
for name in ['README.md','ATTRIBUTIONS.md','NOTICE']:
 if notice not in (root/name).read_text(): raise SystemExit(f'missing required attribution in {name}')
for pat,label in [
 (r'gh[pousr]_[A-Za-z0-9_]{20,}','GitHub token'),(r'hf_[A-Za-z0-9]{20,}','Hugging Face token'),
 (r'AKIA[0-9A-Z]{16}','AWS access key'),(r'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----','private key'),
 (r'GPU-[0-9a-fA-F-]{20,}','private GPU UUID'),(r'/media/'+'samcardillo|/home/'+'samcardillo','private host path'),
 (r'192\.168\.\d+\.\d+','private IPv4 address'),
]:
 if re.search(pat,all_text): raise SystemExit(f'possible {label} found')
# Prevent accidentally activating Actions without deliberate workflow-scope publication.
if (root/'.github/workflows').exists(): raise SystemExit('active GitHub workflows are not permitted in this token-compatible publication')
if (root/'.git').exists():
 staged=subprocess.check_output(['git','ls-files','--stage','scripts'],text=True)
 for line in staged.splitlines():
  mode,_,_,path=line.split(maxsplit=3)
  if path.endswith(('.sh','.py')) and mode!='100755': raise SystemExit(f'not executable in Git: {path} ({mode})')
print('repository checks passed')
PY
git diff --check -- . ':!*.sha256'
echo 'CI PASS'
