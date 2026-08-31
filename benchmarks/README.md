# Benchmark reproduction

These commands reproduce the performance, HumanEval+, and BFCL methods behind [../docs/BENCHMARKS.md](../docs/BENCHMARKS.md). Run against an otherwise idle local endpoint.

## Performance

No third-party Python packages are required:

```bash
python3 benchmarks/performance_benchmark.py
```

The harness writes `benchmarks/performance.json` incrementally. TTFT recognizes first output in `delta.content`, `delta.reasoning_content`, or `delta.reasoning`; omitting `delta.reasoning` produces invalid TTFT for this runtime. It fails closed unless token counters are type-strict integers, every output reaches the exact requested length with `finish_reason=length`, output is non-empty, and prompt plus requested output fits the qualified context. Regression tests cover these checks. The qualified-artifact and hardened-rerun validation ledger is [`qualified-performance-validation.json`](qualified-performance-validation.json).

The near-limit case consumes most of the 262,144-token context and may take over a minute before first output.

## DFlash/scheduler tuning

The shorter fixed-fixture harness records decode, concurrency, live scheduler admission, and DFlash acceptance metrics:

```bash
python3 benchmarks/tuning_benchmark.py \
  --label k3-qualified \
  --out benchmarks/tuning-k3-qualified.json
```

Run candidates sequentially on an otherwise idle endpoint. The public launcher and validator intentionally accept only the qualified K=3 profile; changing only `.env` to K=2/4/5/7 is rejected. Reproducing an unqualified candidate requires a disposable Git branch that changes both the exact default and its validator constraint, followed by a restart to readiness. Record that temporary tree identity and change no other variable. Restore the clean K=3 tree after the experiment. The fixture prompts are fixed and independent of `--label`. Do not compare a warm repeated-prefix run with a cold no-prefix run. The aggregate results and rejected candidates from the qualified sweep are documented in [../docs/OPTIMIZATION.md](../docs/OPTIMIZATION.md); raw files can expose deployment-specific telemetry and are intentionally not redistributed.

## HumanEval+

Use the exact evaluator version and dataset version:

```bash
uv venv benchmarks/.venv-evalplus --python 3.11
uv pip install --python benchmarks/.venv-evalplus/bin/python 'evalplus==0.3.1'
benchmarks/.venv-evalplus/bin/python benchmarks/generate_humanevalplus.py
benchmarks/.venv-evalplus/bin/python -m evalplus.sanitize benchmarks/humanevalplus_raw.jsonl
```

Generation policy:

- one ordered sample for each of 164 HumanEval+ v0.1.10 tasks;
- temperature 0;
- initial output cap 4,096 tokens;
- only an empty-content response is retried once at 8,192 tokens;
- the retry replaces the failed row rather than creating a second sample;
- no task is dropped.

In the published run, four empty first responses were retried and still exhausted 8,192 tokens with no extractable solution. They remained failures. The 92.7% HumanEval+ score therefore does not benefit from those retries.

### Isolated executable scoring

Model-generated code is untrusted. Do not execute it directly on the host. Build the pinned evaluator image:

```bash
docker build -f benchmarks/Dockerfile.evalplus -t glm53-evalplus:0.3.1 benchmarks
mkdir -p benchmarks/evalplus-sandbox/cache
cp "$HOME/.cache/evalplus/HumanEvalPlus-v0.1.10.jsonl" benchmarks/evalplus-sandbox/cache/
cp benchmarks/humanevalplus_raw-sanitized.jsonl benchmarks/evalplus-sandbox/samples.jsonl
chmod -R u+rw benchmarks/evalplus-sandbox
```

Evaluate without network access or Linux capabilities:

```bash
docker run --rm \
  --network none \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 4096 \
  --memory 32g \
  --cpus 32 \
  --tmpfs /tmp:rw,nosuid,noexec,size=4g \
  -v "$PWD/benchmarks/evalplus-sandbox:/work" \
  -v "$PWD/benchmarks/evalplus-sandbox/cache:/root/.cache/evalplus" \
  glm53-evalplus:0.3.1 \
  humaneval --samples /work/samples.jsonl --version v0.1.10 --parallel 32
```

Inspect `/work/samples_eval_results.json`. The evaluator reports both original HumanEval and expanded HumanEval+ pass@1.

## BFCL V4 native function calling

The run used Gorilla/BFCL commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8` and seven deterministic non-live categories. It did not use live external APIs or claim full web-agent coverage.

```bash
git clone https://github.com/ShishirPatil/gorilla.git benchmarks/gorilla
cd benchmarks/gorilla
git checkout 6ea57973c7a6097fd7c5915698c54c17c5b1b6c8
git apply ../../benchmarks/bfcl-local.patch
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e berkeley-function-call-leaderboard
cd ../..
```

The patch registers the exact local model under a distinct BFCL name and adds a 4,096-token completion bound. The bound prevents malformed/no-tool reasoning from consuming the entire 262K context; it must be disclosed with scores.

```bash
export OPENAI_API_KEY=EMPTY
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export BFCL_PROJECT_ROOT="$PWD/benchmarks/bfcl-run"
BFCL="$PWD/benchmarks/gorilla/.venv/bin/bfcl"
CATS='simple_python,simple_java,simple_javascript,parallel,multiple,parallel_multiple,irrelevance'

"$BFCL" generate \
  --model glm-5.3-flash-uncensored-exl3-FC \
  --test-category "$CATS" \
  --temperature 0 \
  --num-threads 8

"$BFCL" evaluate \
  --model glm-5.3-flash-uncensored-exl3-FC \
  --test-category "$CATS"
```

Scores appear under `benchmarks/bfcl-run/score/`. Keep BFCL and HumanEval datasets/results out of Git unless their redistribution terms have been reviewed; this repository intentionally excludes generated samples and raw evaluator data.

## Attribution

EvalPlus/HumanEval+, OpenAI HumanEval, and Gorilla/BFCL are third-party benchmark projects. See [../ATTRIBUTIONS.md](../ATTRIBUTIONS.md) and [../THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Their licenses do not apply to model weights or runtime layers.
