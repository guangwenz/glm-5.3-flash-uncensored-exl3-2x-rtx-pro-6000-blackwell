#!/usr/bin/env python3
import concurrent.futures
import json
import os
import statistics
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
MODEL = "glm-5.3-flash-uncensored-exl3"
OUT = Path(__file__).with_name("performance.json")
SEGMENT = "The archive contains ordinary numbered records with no special instruction. "
MAX_MODEL_LEN = 262144


def post_json(path, payload, timeout=600):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def tokenize(text):
    tokens = post_json("/tokenize", {"model": MODEL, "prompt": text}, 120).get("tokens")
    if type(tokens) is not list or any(type(token) is not int for token in tokens):
        raise RuntimeError("/tokenize must return a list of integer token IDs")
    return len(tokens)


def token_count(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise RuntimeError(f"{name} must be an integer >= {minimum}, got {value!r}")
    return value


def make_prompt(target_tokens, nonce):
    suffix = (
        f"\nBenchmark nonce {nonce}. Summarize the archive briefly, then state the nonce."
    )
    seg_tokens = tokenize(SEGMENT)
    n = max(1, (target_tokens - tokenize(suffix)) // seg_tokens)
    for _ in range(5):
        text = SEGMENT * n + suffix
        count = tokenize(text)
        delta = target_tokens - count
        if abs(delta) < seg_tokens:
            return text, count
        n = max(1, n + delta // seg_tokens)
    return text, count


def stream_chat(prompt, max_tokens):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    first = None
    usage = None
    finish = None
    with urllib.request.urlopen(req, timeout=600) as response:
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
                emitted = delta.get("content") or delta.get("reasoning_content") or delta.get("reasoning") or ""
                if emitted and first is None:
                    first = time.perf_counter()
                if choice.get("finish_reason"):
                    finish = choice["finish_reason"]
    end = time.perf_counter()
    if first is None or usage is None:
        raise RuntimeError(f"missing stream timing or usage: first={first}, usage={usage}")
    prompt_tokens = token_count(usage.get("prompt_tokens"), "prompt_tokens", 1)
    completion_tokens = token_count(
        usage.get("completion_tokens"), "completion_tokens", 1
    )
    if completion_tokens != max_tokens or finish != "length":
        raise RuntimeError(
            f"truncated/non-comparable stream: completion_tokens={completion_tokens}, "
            f"requested={max_tokens}, finish_reason={finish!r}"
        )
    if prompt_tokens + max_tokens > MAX_MODEL_LEN:
        raise RuntimeError(
            f"request exceeds context: {prompt_tokens}+{max_tokens}>{MAX_MODEL_LEN}"
        )
    ttft = first - start
    decode_seconds = max(end - first, 1e-9)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "ttft_s": ttft,
        "prefill_tok_s_client": prompt_tokens / ttft,
        "decode_window_s": decode_seconds,
        "decode_tok_s_client": max(completion_tokens - 1, 0) / decode_seconds,
        "e2e_s": end - start,
        "finish_reason": finish,
    }


def percentile(values, p):
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def summarize(rows, key):
    vals = [r[key] for r in rows]
    return {
        "n": len(vals),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "p90": percentile(vals, 0.90),
        "min": min(vals),
        "max": max(vals),
    }


def nonstream_one(prompt, max_tokens=512):
    start = time.perf_counter()
    result = post_json(
        "/v1/chat/completions",
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_tokens,
        },
        600,
    )
    elapsed = time.perf_counter() - start
    usage = result.get("usage") or {}
    choices = result.get("choices") or []
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
    prompt_tokens = token_count(usage.get("prompt_tokens"), "prompt_tokens", 1)
    completion_tokens = token_count(
        usage.get("completion_tokens"), "completion_tokens", 1
    )
    finish = choice.get("finish_reason")
    if completion_tokens != max_tokens or finish != "length":
        raise RuntimeError(
            f"truncated/non-comparable response: completion_tokens={completion_tokens}, "
            f"requested={max_tokens}, finish_reason={finish!r}"
        )
    if prompt_tokens + max_tokens > MAX_MODEL_LEN:
        raise RuntimeError(
            f"request exceeds context: {prompt_tokens}+{max_tokens}>{MAX_MODEL_LEN}"
        )
    return {
        "elapsed_s": elapsed,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "finish_reason": finish,
    }


def main():
    if os.geteuid() == 0:
        raise SystemExit("Run the benchmark as an unprivileged user, not root.")
    with urllib.request.urlopen(BASE + "/v1/models", timeout=30) as response:
        model_rows = json.load(response).get("data") or []
    record = next((row for row in model_rows if row.get("id") == MODEL), None)
    if (
        record is None
        or type(record.get("max_model_len")) is not int
        or record["max_model_len"] < MAX_MODEL_LEN
    ):
        raise RuntimeError("expected model alias and 262,144-token context")
    results = {
        "endpoint": BASE,
        "model": MODEL,
        "definitions": {
            "ttft": "client wall time from POST start through local loopback to first non-empty content or reasoning delta",
            "prefill_tok_s_client": "API-reported prompt_tokens divided by TTFT; includes local HTTP, scheduling, tokenization, and first-token work",
            "decode_tok_s_client": "(completion_tokens - 1) divided by wall time from first non-empty delta to stream completion",
        },
        "context_runs": [],
        "decode_runs": [],
        "concurrency_runs": [],
    }

    warm, _ = make_prompt(1024, "warmup")
    stream_chat(warm, 32)

    schedule = [(1024, 3), (8192, 3), (32768, 3), (131072, 2), (261800, 1)]
    for target, trials in schedule:
        rows = []
        for trial in range(trials):
            prompt, content_tokens = make_prompt(target, f"ctx-{target}-{trial}")
            row = stream_chat(prompt, 32)
            row.update({"target_content_tokens": target, "actual_content_tokens": content_tokens, "trial": trial})
            rows.append(row)
            results["context_runs"].append(row)
            OUT.write_text(json.dumps(results, indent=2))
        print(json.dumps({
            "context": target,
            "ttft": summarize(rows, "ttft_s"),
            "prefill": summarize(rows, "prefill_tok_s_client"),
        }), flush=True)

    decode_prompts = {
        "prose": "Explain the biggest unsolved mysteries in fundamental physics in detailed continuous prose.",
        "structured": "Generate exactly 180 distinct JSON objects as one valid JSON array. Each object needs integer id, short name, category, boolean active, and three numeric scores. Output JSON only.",
        "code": "Write a complete production-quality Python implementation of an asynchronous bounded work queue with retries, exponential backoff, graceful shutdown, type hints, docstrings, and a runnable example. Output code only.",
    }
    for workload, prompt in decode_prompts.items():
        for trial in range(3):
            row = stream_chat(prompt + f"\nUnique run marker: {workload}-{trial}", 1024)
            row.update({"workload": workload, "trial": trial})
            results["decode_runs"].append(row)
            OUT.write_text(json.dumps(results, indent=2))
        rows = [r for r in results["decode_runs"] if r["workload"] == workload]
        print(json.dumps({"decode": workload, "tps": summarize(rows, "decode_tok_s_client")}), flush=True)

    base_prompt = "Write a detailed technical explanation of lock-free queues and include pseudocode."
    for concurrency in (1, 2, 4):
        prompts = [base_prompt + f" Unique request {concurrency}-{i}." for i in range(concurrency)]
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            rows = list(pool.map(nonstream_one, prompts))
        wall = time.perf_counter() - start
        total = sum(r["completion_tokens"] for r in rows)
        entry = {
            "concurrency": concurrency,
            "wall_s": wall,
            "total_completion_tokens": total,
            "aggregate_output_tok_s": total / wall,
            "requests": rows,
        }
        results["concurrency_runs"].append(entry)
        OUT.write_text(json.dumps(results, indent=2))
        print(json.dumps(entry), flush=True)

    OUT.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
