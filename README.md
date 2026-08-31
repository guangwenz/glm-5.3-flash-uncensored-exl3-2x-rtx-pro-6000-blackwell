# GLM-5.3 Flash Uncensored EXL3 on 2× RTX PRO 6000 Blackwell

Reproducible, revision-pinned recipe for the exact deployment qualified on two NVIDIA RTX PRO 6000 Blackwell Workstation Edition 96 GB GPUs:

- `neko-legends/GLM-5.3-Flash-Uncensored-EXL3@1fac3dbe6269a399ce5378261cdf250fde706180`
- EXL3/TR3 4 bpw routed experts, BF16 remainder
- TP2 + EP2 + DCP2
- DFlash2 depth 3 balanced profile (qualified after a K=2/3/4/5/7 sweep)
- 262,144-token context
- NVFP4 DSA/MLA KV cache
- one still image per request; native video disabled
- OpenAI-compatible text, reasoning, and native tool calls

This is the uncensored/abliterated checkpoint, not the aligned GLM-5.3 Flash checkpoint and not full GLM-5.3.

## License warning

This is a source-available deployment stack, not an all-MIT/open-source bundle:

- the checkpoint includes ShapleyMCG-licensed calibration artifacts and requires attribution;
- the uncensored checkpoint is gated and has additional model-card terms;
- the DFlash2 drafter is **CC BY-NC-ND 4.0**, for non-commercial research/evaluation unless separately licensed;
- the container declares `LicenseRef-ShapleyMCG-1.0` and is pulled by digest, not redistributed here.

Review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [ATTRIBUTIONS.md](ATTRIBUTIONS.md), and all upstream terms before use.

> This work includes or was produced using ShapleyMcg, created by Brandon M. Music
> (https://github.com/brandonmmusic-max/shapleymcg). ShapleyMcg is licensed under the
> ShapleyMcg License v1.0, an attribution-required license that grants no rights to
> the person known as "0xSero." Use of ShapleyMcg without this attribution is unlicensed.

## Qualified hardware and software

- 2× NVIDIA RTX PRO 6000 Blackwell Workstation Edition, 96 GB each
- both cards selected explicitly; an RTX 5090 in the test workstation was excluded
- NVIDIA driver 590.48.01
- Docker 29.1.3 with NVIDIA Container Toolkit
- Ubuntu 24.04 host
- pinned runtime image digest in [PROVENANCE.md](PROVENANCE.md)

Other GPUs, driver branches, container engines, lower-VRAM cards, and topology combinations are unqualified.

## Quick start

Prerequisites:

1. Docker Engine and NVIDIA Container Toolkit working for an unprivileged user.
2. Exactly two free RTX PRO 6000 Blackwell 96 GB GPUs.
3. About 180 GB for the target checkpoint, 2.4 GB for the drafter, and additional cache space.
4. An authenticated Hugging Face account approved for the gated target checkpoint.
5. Hugging Face `hf` CLI (tested with 1.9.0).

```bash
git clone https://github.com/samuelcardillo/glm-5.3-flash-uncensored-exl3-2x-rtx-pro-6000-blackwell.git
cd glm-5.3-flash-uncensored-exl3-2x-rtx-pro-6000-blackwell
cp config/example.env .env
$EDITOR .env
```

Authenticate with Hugging Face, review the three licenses/terms, then download exact revisions:

```bash
hf auth login
I_ACCEPT_SHAPLEYMCG_LICENSE=yes \
I_ACCEPT_UNCENSORED_MODEL_TERMS=yes \
I_ACCEPT_DFLASH2_CC_BY_NC_ND_4_0=yes \
  ./scripts/download-model.sh
```

The acceptance variables are deliberately not stored in `.env`. The downloader checks all three before creating download directories.

Run full preflight and launch:

```bash
./scripts/preflight.sh        # hashes every pinned file; expect a full ~178 GB read
./scripts/serve.sh
```

In another terminal:

```bash
./scripts/verify.py
./scripts/verify-long-context.py   # exact 261,875-token retrieval; can take over a minute
```

Stop:

```bash
./scripts/stop.sh
```

## User systemd service

```bash
./scripts/install-user-service.sh
systemctl --user start glm53-uncensored-exl3.service
journalctl --user -u glm53-uncensored-exl3.service -f
```

The user manager starts after login. For deliberate pre-login startup, review `loginctl enable-linger` and its security implications.

## API example

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model":"glm-5.3-flash-uncensored-exl3",
    "messages":[{"role":"user","content":"Reply with exactly READY"}],
    "temperature":0,
    "max_tokens":64
  }'
```

The API has no built-in authentication. It binds to loopback by default. Do not set `BIND_ADDRESS=0.0.0.0`; use a specific trusted LAN/Tailnet address and an authenticated gateway such as LiteLLM when remote access is required.

## Measured results

The initial K=7 profile admitted only one active request because its hybrid recurrent/speculative cache reservation consumed about 60% of the available KV pool per short request. The qualified K=3 profile admits three active requests and preserves single-stream performance:

- concurrency 1: 117.82 → 123.19 output tok/s (+4.56%);
- concurrency 2: 127.31 → 205.40 output tok/s (+61.33%);
- concurrency 4: 131.66 → 212.90 output tok/s (+61.70%);
- slowest of four 512-token requests: 15.55 → 9.62 seconds (-38.16%);
- near-262K TTFT: 60.456 → 59.850 seconds.

A sequential matched-checkpoint A/B under the same K=3 runtime found the uncensored checkpoint within about 4% of the aligned checkpoint on the isolated regressions and faster on most measured workloads. This does not reconstruct the former aligned native-MTP/ReplaySSM service. HumanEval+ pass@1 remains 92.7% from the original qualification. See [docs/OPTIMIZATION.md](docs/OPTIMIZATION.md) and [docs/BENCHMARKS.md](docs/BENCHMARKS.md) for methods, provenance, rejected candidates, and limitations.

## Important limitations

- The K=3 profile balances interactive latency and overlapping-request throughput. K=2 was faster at concurrency 4 but materially slower for an isolated stream; K=4/5 admitted only two active requests; K=7 admitted only one.
- Prefix caching is disabled in the qualified profile.
- Native video is disabled and unqualified. Still-image input is limited to one image per request.
- DFlash2 at the pinned revision is non-commercial under CC BY-NC-ND 4.0.
- Uncensored weights reduce refusal behavior; operators are responsible for authorization, safeguards, and legal use.
- The recipe pulls, but does not mirror, the composed runtime image. Its embedded provenance is preserved under `manifests/`; review the upstream image/source boundary.

## Documentation

- [PROVENANCE.md](PROVENANCE.md) — immutable model, drafter, image, and runtime identities
- [ATTRIBUTIONS.md](ATTRIBUTIONS.md) — people, organizations, projects, citations
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) — license boundaries and restrictions
- [docs/BENCHMARKS.md](docs/BENCHMARKS.md) — measured performance and capability
- [docs/OPTIMIZATION.md](docs/OPTIMIZATION.md) — K=7 bottleneck, tuning sweep, matched aligned A/B, and production decision
- [benchmarks/README.md](benchmarks/README.md) — exact performance, EvalPlus, and BFCL reproduction steps
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — startup and memory diagnostics

The recipe's own scripts and documentation are Apache-2.0 licensed. Model weights, drafter weights, container layers, and upstream software retain their own licenses.
