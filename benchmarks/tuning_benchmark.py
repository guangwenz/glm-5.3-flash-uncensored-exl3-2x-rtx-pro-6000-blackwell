#!/usr/bin/env python3
"""Short fixed-fixture benchmark for DFlash depth and scheduler tuning."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import statistics
import threading
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
MODEL = "glm-5.3-flash-uncensored-exl3"


def get(path: str, timeout: int = 30) -> str:
    with urllib.request.urlopen(BASE + path, timeout=timeout) as response:
        return response.read().decode()


def post(path: str, payload: dict, timeout: int = 600) -> dict:
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def metrics() -> dict[str, float | None]:
    text = get("/metrics")
    out: dict[str, float | None] = {}
    names = [
        "vllm:spec_decode_num_drafts_total",
        "vllm:spec_decode_num_draft_tokens_total",
        "vllm:spec_decode_num_accepted_tokens_total",
        "vllm:num_requests_running",
        "vllm:num_requests_waiting",
    ]
    for name in names:
        match = re.search(
            r"^" + re.escape(name) + r"\{[^\n]*\}\s+([0-9.eE+-]+)$",
            text,
            re.MULTILINE,
        )
        out[name] = float(match.group(1)) if match else None
    return out


def token_count(value: object, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise RuntimeError(f"{name} must be an integer >= {minimum}, got {value!r}")
    return value


def require_metrics(values: dict[str, float | None]) -> None:
    missing = [name for name, value in values.items() if value is None]
    if missing:
        raise RuntimeError(f"required Prometheus metrics missing: {missing}")


def stream(prompt: str, max_tokens: int = 512) -> dict:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    request = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    first = None
    usage = None
    finish = None
    with urllib.request.urlopen(request, timeout=600) as response:
        for raw in response:
            line = raw.decode().strip()
            if not line.startswith("data: "):
                continue
            body = line[6:]
            if body == "[DONE]":
                break
            event = json.loads(body)
            if event.get("usage"):
                usage = event["usage"]
            for choice in event.get("choices", []):
                delta = choice.get("delta") or {}
                emitted = (
                    delta.get("content")
                    or delta.get("reasoning_content")
                    or delta.get("reasoning")
                    or ""
                )
                if emitted and first is None:
                    first = time.perf_counter()
                if choice.get("finish_reason"):
                    finish = choice["finish_reason"]
    end = time.perf_counter()
    if first is None or usage is None:
        raise RuntimeError(f"incomplete stream first={first} usage={usage}")
    prompt_count = token_count(usage.get("prompt_tokens"), "prompt_tokens", minimum=1)
    count = token_count(usage.get("completion_tokens"), "completion_tokens", minimum=1)
    if count != max_tokens or finish != "length":
        raise RuntimeError(
            f"truncated/non-comparable stream: completion_tokens={count}, "
            f"requested={max_tokens}, finish_reason={finish!r}"
        )
    decode = max(end - first, 1e-9)
    return {
        "prompt_tokens": prompt_count,
        "completion_tokens": count,
        "ttft_s": first - start,
        "decode_s": decode,
        "decode_tok_s": max(count - 1, 0) / decode,
        "e2e_s": end - start,
        "finish_reason": finish,
    }


def nonstream(prompt: str, max_tokens: int = 512) -> dict:
    start = time.perf_counter()
    response = post(
        "/v1/chat/completions",
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_tokens,
        },
    )
    usage = response.get("usage") or {}
    choices = response.get("choices") or []
    if len(choices) != 1:
        raise RuntimeError(f"expected one choice, got {len(choices)}")
    choice = choices[0]
    message = choice.get("message") or {}
    emitted = (
        message.get("content")
        or message.get("reasoning_content")
        or message.get("reasoning")
        or ""
    )
    if not emitted:
        raise RuntimeError("non-stream response emitted no content or reasoning")
    prompt_count = token_count(usage.get("prompt_tokens"), "prompt_tokens", minimum=1)
    count = token_count(usage.get("completion_tokens"), "completion_tokens", minimum=1)
    finish = choice.get("finish_reason")
    if count != max_tokens or finish != "length":
        raise RuntimeError(
            f"truncated/non-comparable response: completion_tokens={count}, "
            f"requested={max_tokens}, finish_reason={finish!r}"
        )
    return {
        "elapsed_s": time.perf_counter() - start,
        "prompt_tokens": prompt_count,
        "completion_tokens": count,
        "finish_reason": finish,
    }


def sample_until(
    stop: threading.Event, samples: list[dict], errors: list[str]
) -> None:
    while not stop.is_set():
        try:
            sample = metrics()
            require_metrics(sample)
            samples.append(sample)
        except Exception as exc:
            errors.append(repr(exc))
            return
        stop.wait(0.05)


def finish_sampling(
    stop: threading.Event,
    sampler: threading.Thread,
    samples: list[dict],
    errors: list[str],
) -> None:
    stop.set()
    sampler.join(2)
    if sampler.is_alive():
        raise RuntimeError("scheduler metric sampler did not stop within 2 seconds")
    if errors:
        raise RuntimeError(f"scheduler metric sampling failed: {errors[0]}")
    if not samples:
        raise RuntimeError("scheduler metric sampling produced no samples")


def summary(values: list[float]) -> dict:
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    global BASE, MODEL
    if os.geteuid() == 0:
        raise SystemExit("Run the benchmark as an unprivileged user, not root.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--label", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=2)
    parser.add_argument("--tokens", type=int, default=512)
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials must be at least 1")
    if args.tokens < 2:
        parser.error("--tokens must be at least 2")
    if not args.out.parent.is_dir():
        parser.error("--out parent directory must already exist")
    BASE = args.base_url.rstrip("/")
    MODEL = args.model

    models = json.loads(get("/v1/models"))
    record = next((item for item in models["data"] if item["id"] == MODEL), None)
    if (
        record is None
        or type(record.get("max_model_len")) is not int
        or record["max_model_len"] < 262144
    ):
        raise RuntimeError("expected model alias and at least 262,144-token context")

    prompts = {
        "prose": "Explain three major unsolved problems in fundamental physics in detailed continuous prose.",
        "structured": "Generate exactly 100 distinct JSON objects as one valid JSON array with id, name, category, active, and three scores. Output JSON only.",
        "code": "Write a complete Python asynchronous bounded work queue with retries, exponential backoff, graceful shutdown, type hints, docstrings, and runnable example. Output code only.",
    }
    initial_metrics = metrics()
    require_metrics(initial_metrics)
    result = {
        "label": args.label,
        "timestamp": time.time(),
        "model_record": record,
        "tokens": args.tokens,
        "trials": args.trials,
        "decode": [],
        "concurrency": [],
        "metrics_before": initial_metrics,
    }
    stream("Warm up the model with a concise paragraph. Marker warmup.", 64)
    for kind, prompt in prompts.items():
        rows = [
            stream(
                prompt + f"\nFixed trial marker {kind}-{trial}",
                args.tokens,
            )
            for trial in range(args.trials)
        ]
        result["decode"].append(
            {
                "workload": kind,
                "runs": rows,
                "tps": summary([row["decode_tok_s"] for row in rows]),
                "ttft": summary([row["ttft_s"] for row in rows]),
            }
        )
        args.out.write_text(json.dumps(result, indent=2))

    base_prompt = (
        "Write a detailed technical explanation of lock-free queues and include pseudocode."
    )
    for concurrency in (1, 2, 4):
        prompts = [
            base_prompt + f" Fixed concurrency marker c{concurrency}-{index}."
            for index in range(concurrency)
        ]
        samples: list[dict] = []
        sample_errors: list[str] = []
        stop = threading.Event()
        sampler = threading.Thread(
            target=sample_until,
            args=(stop, samples, sample_errors),
            daemon=True,
        )
        sampler.start()
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=concurrency
        ) as executor:
            rows = list(executor.map(lambda prompt: nonstream(prompt, args.tokens), prompts))
        wall = time.perf_counter() - start
        finish_sampling(stop, sampler, samples, sample_errors)
        total = sum(row["completion_tokens"] for row in rows)
        result["concurrency"].append(
            {
                "concurrency": concurrency,
                "wall_s": wall,
                "total_completion_tokens": total,
                "aggregate_output_tok_s": total / wall,
                "requests": rows,
                "max_running": max(
                    (
                        sample.get("vllm:num_requests_running") or 0
                        for sample in samples
                    ),
                    default=0,
                ),
                "max_waiting": max(
                    (
                        sample.get("vllm:num_requests_waiting") or 0
                        for sample in samples
                    ),
                    default=0,
                ),
            }
        )
        args.out.write_text(json.dumps(result, indent=2))

    result["metrics_after"] = metrics()
    before = result["metrics_before"]
    after = result["metrics_after"]
    require_metrics(before)
    require_metrics(after)
    drafts = (
        after["vllm:spec_decode_num_drafts_total"]
        - before["vllm:spec_decode_num_drafts_total"]
    )
    drafted = (
        after["vllm:spec_decode_num_draft_tokens_total"]
        - before["vllm:spec_decode_num_draft_tokens_total"]
    )
    accepted = (
        after["vllm:spec_decode_num_accepted_tokens_total"]
        - before["vllm:spec_decode_num_accepted_tokens_total"]
    )
    result["spec_delta"] = {
        "drafts": drafts,
        "draft_tokens": drafted,
        "accepted_tokens": accepted,
        "accepted_per_draft": accepted / drafts if drafts else None,
        "accepted_fraction": accepted / drafted if drafted else None,
    }
    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
