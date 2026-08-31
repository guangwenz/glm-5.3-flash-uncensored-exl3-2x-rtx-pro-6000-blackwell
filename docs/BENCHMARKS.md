# Qualified benchmark results

Performance was rerun on 2026-08-31 against the balanced K=3 profile in [PROVENANCE.md](../PROVENANCE.md). Requests used the local loopback API, temperature 0, prefix caching disabled, and no competing benchmark workload. The original 2026-08-30 K=7 baseline and complete tuning comparison are preserved in [OPTIMIZATION.md](OPTIMIZATION.md).

## TTFT and effective prefill

Client TTFT is request submission to the first streamed output token, including a reasoning token when emitted first. Effective prefill is prompt tokens divided by this client-observed TTFT; it includes local request/tokenization/scheduling overhead and is not a kernel-only metric.

| Server prompt tokens | Trials | Median TTFT | P90 TTFT | Median effective prefill |
|---:|---:|---:|---:|---:|
| 1,035 | 3 | 0.420 s | 0.422 s | 2,462 tok/s |
| 8,197 | 3 | 2.071 s | 2.075 s | 3,959 tok/s |
| 32,771 | 3 | 7.474 s | 7.787 s | 4,385 tok/s |
| 131,078 | 2 | 29.500 s | 29.529 s | 4,443 tok/s |
| 261,802 | 1 | 59.850 s | — | 4,374 tok/s |

## Decode

Each trial requested exactly 1,024 output tokens. Decode TPS excludes TTFT and uses `(completion_tokens - 1) / (last_token_time - first_token_time)`.

| Workload | Trials | Median | Mean | Range |
|---|---:|---:|---:|---:|
| Prose | 3 | 125.69 tok/s | 122.81 | 116.12–126.63 |
| Structured | 3 | 141.65 tok/s | 139.29 | 134.06–142.15 |
| Python/code | 3 | 122.55 tok/s | 122.35 | 120.42–124.06 |

## Concurrent output

| Concurrent requests | Total output | Wall time | Aggregate output throughput |
|---:|---:|---:|---:|
| 1 | 512 | 4.156 s | 123.19 tok/s |
| 2 | 1,024 | 4.985 s | 205.40 tok/s |
| 4 | 2,048 | 9.620 s | 212.90 tok/s |

At concurrency 4, individual requests completed in 5.67, 5.85, 5.79, and 9.62 seconds. Live scheduler sampling observed up to three active requests. The fourth request waited for capacity, but the near-perfect K=7 serialization was removed.

### Publication-validation rerun

The archived qualified and aligned-control artifacts were checked before publication: all 42 streamed rows and 14 non-stream requests across the two artifacts have type-strict integer completion counts, the exact requested length, and `finish_reason=length`. The public harness was then hardened to enforce those conditions at request time, reject empty output and invalid counter types, and guard the 262,144-token limit. A complete hardened K=3 rerun also passed every assertion. It measured 59.397 seconds near 262K, decode medians of 119.95/132.80/117.58 tok/s (prose/structured/code), C1/C2/C4 aggregate throughput of 125.17/212.36/210.43 tok/s, and a 9.73-second slowest C4 request.

The hardened rerun confirms the capacity/concurrency conclusion but is not substituted into the headline matched table: it was a later standalone K=3 validation, not a simultaneous K=7 rerun. Run-to-run decode variance is reported rather than hidden. Artifact hashes and assertion counts are preserved in [`benchmarks/qualified-performance-validation.json`](../benchmarks/qualified-performance-validation.json).

## Long context and vision

- Exact 261,875-token prompt: recovered needle `864219`; 60.718 seconds end-to-end.
- Runtime language-token KV capacity reported during qualification: 303,264 tokens. Hybrid recurrent/speculative state still determines request admission.
- Generated 256×256 white image with blue circle: correctly identified as `blue circle`.
- Native video remained disabled and was not tested.

## Coding

EvalPlus 0.3.1, HumanEval+ v0.1.10, 164 tasks, one deterministic retained sample per task. Requests used a 4,096-token initial cap; only empty-content outputs were retried once at 8,192 tokens. Official EvalPlus tests ran in an isolated container.

| Suite | pass@1 |
|---|---:|
| HumanEval base | 97.6% (160/164) |
| HumanEval+ expanded | 92.7% (152/164) |

Four empty initial generations were retried once; each retry exhausted the 8,192-token cap without an extractable final solution and was retained as a failure. No successful sample benefited from retry.

## Native tool calling

BFCL V4 official evaluator, 1,390 non-live cases, native OpenAI-compatible `tools`, temperature 0, 4,096 response-token cap.

| Category | Accuracy |
|---|---:|
| Simple JavaScript | 68.00% |
| Irrelevance | 62.92% |
| Simple Python | 56.75% |
| Parallel | 53.50% |
| Multiple | 38.00% |
| Parallel + multiple | 19.00% |
| Simple Java | 3.00% |

This supports a narrow conclusion: straightforward native tool use is usable, but complex autonomous multi-tool workflows need schema validation, retries, decomposition, and human oversight. These non-live function-calling categories are not a complete browser/web/software-agent benchmark.

## Reproduction caveats

- Benchmark results apply only to the exact checkpoint, drafter, runtime digest, context, image-enabled template, and two-GPU profile.
- The first development version of the streaming harness failed to recognize `delta.reasoning`; the corrected successful run recognized `content`, `reasoning_content`, and `reasoning`. All performance numbers above come from the successful corrected run.
- The archived headline artifacts predate the final fail-closed checks, but their retained usage and finish fields pass exact-length/type/finish validation. The complete hardened publication rerun independently passed the additional live empty-output and context-bound checks.
- Historical language-only 368K numbers are intentionally excluded.
