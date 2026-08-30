# Qualified benchmark results

Measured on 2026-08-30 against the exact profile in [PROVENANCE.md](../PROVENANCE.md). Requests used the local loopback API, temperature 0, prefix caching disabled, and no competing benchmark workload during performance measurement.

## TTFT and effective prefill

Client TTFT is request submission to the first streamed output token, including a reasoning token when emitted first. Effective prefill is prompt tokens divided by this client-observed TTFT; it includes local request/tokenization/scheduling overhead and is not a kernel-only metric.

| Server prompt tokens | Trials | Median TTFT | P90 TTFT | Median effective prefill |
|---:|---:|---:|---:|---:|
| 1,035 | 3 | 0.360 s | 0.360 s | 2,878 tok/s |
| 8,197 | 3 | 2.022 s | 2.025 s | 4,053 tok/s |
| 32,771 | 3 | 7.577 s | 7.860 s | 4,325 tok/s |
| 131,078 | 2 | 29.981 s | 29.987 s | 4,372 tok/s |
| 261,802 | 1 | 60.456 s | — | 4,330 tok/s |

## Decode

Each trial requested exactly 1,024 output tokens. Decode TPS excludes TTFT and uses `(completion_tokens - 1) / (last_token_time - first_token_time)`.

| Workload | Trials | Median | Mean | Range |
|---|---:|---:|---:|---:|
| Prose | 3 | 119.38 tok/s | 118.26 | 115.45–119.95 |
| Structured | 3 | 134.05 tok/s | 136.00 | 122.42–151.53 |
| Python/code | 3 | 132.58 tok/s | 128.38 | 117.70–134.86 |

## Concurrent output

| Concurrent requests | Total output | Wall time | Aggregate output throughput |
|---:|---:|---:|---:|
| 1 | 512 | 4.346 s | 117.82 tok/s |
| 2 | 1,024 | 8.043 s | 127.31 tok/s |
| 4 | 2,048 | 15.555 s | 131.66 tok/s |

At concurrency 4, individual requests completed at 3.95, 7.76, 11.51, and 15.55 seconds. The 262K profile is therefore optimized for a long interactive stream, not high simultaneous-user throughput.

## Long context and vision

- Exact 261,875-token prompt: recovered needle `864219`; 71.323 seconds end-to-end.
- Runtime KV pool observed: 303,264 tokens.
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
- Historical language-only 368K numbers are intentionally excluded.
