# DFlash2 and scheduler optimization

Qualified on 2026-08-31. This document explains why the recipe changed from DFlash2 K=7 to K=3, what was held constant, what was tested, and why the result is not evidence that uncensoring itself caused a slowdown.

## Outcome

The original K=7 profile preserved fast isolated decode but serialized overlapping requests. The balanced K=3 profile:

- keeps the pinned target, drafter, and runtime image;
- keeps TP2 + EP2 + DCP2, 262,144-token context, NVFP4 DSA/MLA KV, multimodal image input, tool calls, and port behavior;
- increases observed scheduler admission from one to three active requests;
- improves aggregate output throughput by 61% at concurrency 2 and 4;
- reduces the slowest latency among four 512-token requests by 38%;
- leaves near-limit prefill effectively unchanged;
- remains performance-equivalent to the aligned checkpoint in a sequential matched-runtime control.

The runtime image's embedded provenance says `DFlash2-7` because that is its build/release profile. The serving CLI supports a runtime `num_speculative_tokens` override; this recipe now deliberately sets it to 3. The drafter weights and revision are unchanged.

## Diagnosis

The client submitted concurrent requests together. Live vLLM metrics during the K=7 baseline repeatedly showed:

```text
num_requests_running = 1
num_requests_waiting = 1 or 3
num_requests_waiting_by_reason{reason="capacity"} > 0
kv_cache_usage_perc ≈ 0.603
```

A short 36-token-prompt/512-token-output request was therefore accounted as roughly 60.3% of the available hybrid KV/recurrent cache. A second equivalent allocation could not be admitted. The completion staircase at concurrency 4—approximately 3.95, 7.76, 11.51, and 15.55 seconds—was server-side capacity serialization, not client-side serialization.

`--max-num-seqs 8` is an upper scheduler limit, not a guarantee that eight requests fit. DFlash depth contributes recurrent/speculative state per active request. Reducing K lowered that per-request reservation enough to admit more requests.

On the fixed tuning fixture, K=7 drafted 14,798 positions and accepted 4,624, a 31.25% accepted-slot fraction. K=3 accepted fewer speculative tokens per verification round but used its smaller draft window more efficiently and avoided most queueing.

## Controlled experiment design

The sweep held these variables constant unless the candidate row explicitly says otherwise:

- exact uncensored target revision and DFlash2 revision from [PROVENANCE.md](../PROVENANCE.md);
- exact runtime image digest;
- the same two explicitly selected RTX PRO 6000 Blackwell 96 GB GPUs;
- RTX 5090 excluded;
- TP2 + EP2 + DCP2;
- 262,144-token context;
- image-enabled chat template and five-image limit;
- native video disabled;
- `nvfp4_ds_mla` KV cache;
- 1,024 maximum batched tokens;
- prefix caching disabled;
- the same core prompts, output lengths, temperature 0, and reasoning-aware streaming parser.

Method limitation: the historical short sweep appended each profile label to its marker text. The labels could change prompt tokenization by a small number of tokens, so the candidate table below is exploratory ranking evidence rather than a strict label-independent A/B. The published `tuning_benchmark.py` corrects this by keeping `--label` as metadata only. The production K=7-versus-K=3 table and aligned-checkpoint control were rerun with the longer standardized harness, whose measured prompts do not contain a profile label; those are the basis for the reported production improvements.

TTFT is request submission to the first emitted `content`, `reasoning_content`, or `reasoning` token. Effective prefill includes local HTTP, tokenization, and scheduler overhead and is not a kernel-only metric. Aggregate concurrency throughput is total server-reported completion tokens divided by wall time.

## Candidate sweep

The historical short tuning harness requested 512 output tokens and sampled scheduler metrics while requests were in flight. Because of the profile-label marker limitation disclosed above, values are useful for broad candidate ranking, not fine-grained matched claims. The final profile was rerun with the longer standardized benchmark.

| Candidate | Mean single decode | C2 aggregate | C4 aggregate | Maximum active at C4 | Decision |
|---|---:|---:|---:|---:|---|
| K=7 baseline | 128.85 tok/s | 126.36 tok/s | 131.41 tok/s | 1 | Rejected: capacity serialization |
| K=7 + prefix cache / aligned Mamba cache | 154.58 tok/s* | 120.26 tok/s | 129.90 tok/s | 1 | Rejected: still serialized; lower KV capacity |
| K=5 | 141.34 tok/s | 198.64 tok/s | 188.46 tok/s | 2 | Rejected: lower concurrency than K=3 |
| K=4 | 145.53 tok/s | 176.64 tok/s | 196.58 tok/s | 2 | Single-stream-first option, not selected |
| K=3 | 140.13 tok/s | 204.30 tok/s | 220.25 tok/s | 3 | Selected balance |
| K=2 | 126.00 tok/s | 196.80 tok/s | 291.17 tok/s | 4 | Throughput-first option; single-stream regression |
| K=3 + greedy draft sampling | 135.48 tok/s | 184.32 tok/s | 204.41 tok/s | 3 | Rejected: slower than probabilistic |
| K=3 + 2,048 batched tokens | 139.21 tok/s | 201.86 tok/s | 212.08 tok/s | 2 | Rejected: resident concurrency regressed |

`*` The prefix-cache single-stream result varied with acceptance and cache state and did not produce an end-to-end concurrency benefit. Reported KV capacity fell from 303,264 to 281,209 tokens. Cold and warm prefix-cache results must not be conflated.

Removing `--disable-custom-all-reduce` was also tested as a single variable. Engine initialization failed on this exact runtime/topology, so the known-good collective path was immediately restored. The failed candidate was not benchmarked or promoted.

## Standardized K=7 versus K=3 result

The longer benchmark requested exactly 1,024 output tokens for each decode fixture.

| Metric | K=7 baseline | K=3 qualified | Change |
|---|---:|---:|---:|
| Prose decode, mean | 118.26 tok/s | 122.81 tok/s | +3.85% |
| Structured decode, mean | 136.00 tok/s | 139.29 tok/s | +2.42% |
| Code decode, mean | 128.38 tok/s | 122.35 tok/s | -4.70% |
| Concurrency 1 aggregate | 117.82 tok/s | 123.19 tok/s | +4.56% |
| Concurrency 2 aggregate | 127.31 tok/s | 205.40 tok/s | +61.33% |
| Concurrency 4 aggregate | 131.66 tok/s | 212.90 tok/s | +61.70% |
| Slowest of four 512-token requests | 15.55 s | 9.62 s | -38.16% |
| Maximum observed active requests | 1 | 3 | +2 requests |
| Near-262K TTFT | 60.456 s | 59.850 s | -1.00% |
| Near-262K effective prefill | 4,330 tok/s | 4,374 tok/s | +1.01% |

K=3 decode medians were 125.69 tok/s prose, 141.65 tok/s structured, and 122.55 tok/s code.

Percentage changes are calculated from the full-precision JSON artifacts rather than the rounded values displayed in the tables.

Before publication, retained K=3 and aligned-control artifacts were checked for exact requested completion counts and `finish_reason=length`. The standardized harness was then hardened to reject invalid counter types, early stop, empty output, and context overflow, and its complete K=3 publication-validation rerun passed. That later standalone run confirmed the concurrency result (C2 212.36 tok/s, C4 210.43 tok/s, slowest C4 request 9.73 seconds) but was not used to recompute the matched K=7 table because K=7 was not rerun in the same validation window. Hashes and assertion counts are in [`benchmarks/qualified-performance-validation.json`](../benchmarks/qualified-performance-validation.json).

## Matched aligned-checkpoint control

The aligned and uncensored checkpoints were loaded sequentially on the same two GPUs under the qualified K=3 runtime profile. Runtime image, DFlash2 drafter, context, KV format, image template, prefix-cache state, prompts, output lengths, and benchmark parser were held constant.

| Metric | Aligned control | Uncensored target | Uncensored difference |
|---|---:|---:|---:|
| Prose decode, mean | 117.19 tok/s | 122.81 tok/s | +4.79% |
| Structured decode, mean | 135.42 tok/s | 139.29 tok/s | +2.86% |
| Code decode, mean | 127.09 tok/s | 122.35 tok/s | -3.73% |
| Concurrency 1 aggregate | 127.17 tok/s | 123.19 tok/s | -3.13% |
| Concurrency 2 aggregate | 196.05 tok/s | 205.40 tok/s | +4.77% |
| Concurrency 4 aggregate | 207.13 tok/s | 212.90 tok/s | +2.78% |
| Near-262K TTFT | 60.403 s | 59.850 s | uncensored 0.92% faster |

This shows no general checkpoint-level slowdown under matched serving conditions. It does **not** recreate the former aligned production service, which used a different native adaptive-MTP/ReplaySSM runtime, prefix-cache policy, scheduler limits, communication path, and checkpoint encoding.

The local aligned control corresponded to the `GLM-5.3-Flash-tr3-4bpw` lineage credited in [ATTRIBUTIONS.md](../ATTRIBUTIONS.md). No immutable public Hub revision was recovered for that retained local copy, so this A/B is transparent but not fully externally reproducible. It must not be interpreted as a universal aligned-versus-uncensored benchmark.

## Final capability qualification

After restoring the uncensored target following the matched control:

- `/v1/models` advertised the expected alias and 262,144-token maximum;
- exact text fixture passed;
- native OpenAI-compatible tool call and arguments passed;
- generated-pixel still image was identified as `blue circle`;
- exact needle `864219` was recovered from an exact 261,875-token prompt in 60.718 seconds;
- DFlash2 was active at K=3 with probabilistic drafting and standard rejection;
- service was enabled and active with zero post-restoration restarts;
- no fatal engine, traceback, or CUDA out-of-memory lines appeared after final startup;
- native video remained disabled and unqualified.

## Reproduction

Run the standard benchmark:

```bash
python3 benchmarks/performance_benchmark.py
```

Run the short scheduler-aware fixture:

```bash
python3 benchmarks/tuning_benchmark.py \
  --label k3-qualified \
  --out benchmarks/tuning-k3-qualified.json
```

The public launcher and validator deliberately accept only K=3. Changing only `.env` to K=2/4/5/7 is rejected. Candidate reproduction requires a disposable Git branch that changes both the exact DFlash default and its validator constraint, records that temporary tree identity, restarts to full readiness, and changes no other variable. Restore the clean qualified K=3 tree after experiments. Do not publish raw logs or artifacts without checking for host paths, addresses, GPU identifiers, or credentials.

## Attribution and license boundary

The target, quantization/calibration lineage, DFlash2 authors, runtime contributors, benchmark projects, and recipe author are credited in [ATTRIBUTIONS.md](../ATTRIBUTIONS.md). License boundaries and complete notices are in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). In particular, the pinned DFlash2 checkpoint is CC BY-NC-ND 4.0 and restricted to non-commercial use unless separately licensed. This repository contains launch logic and measurements, not model weights, drafter weights, runtime layers, aligned-control weights, or third-party dataset rows.
