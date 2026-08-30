#!/usr/bin/env python3
"""Generate one deterministic HumanEval+ sample; retry only empty output once at 8192 tokens."""
import concurrent.futures
import json
import re
import threading
import time
import urllib.request
from pathlib import Path

from evalplus.data import get_human_eval_plus

BASE = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "glm-5.3-flash-uncensored-exl3"
OUT = Path(__file__).with_name("humanevalplus_raw.jsonl")
META = Path(__file__).with_name("humanevalplus_generation_metrics.json")
LOCK = threading.Lock()


def clean_code(text):
    text = text.strip()
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.S | re.I)
    if match:
        text = match.group(1).strip()
    return text


def request_solution(task_id, problem, attempt=0):
    prompt = (
        "Solve this HumanEval Python programming task. Return only a complete, valid Python "
        "solution containing the required imports and the exact requested function. Do not "
        "include Markdown fences, tests, examples, commentary, or explanations.\n\n"
        + problem["prompt"]
    )
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 4096 if attempt == 0 else 8192,
    }
    req = urllib.request.Request(
        BASE,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as response:
        data = json.load(response)
    elapsed = time.perf_counter() - start
    message = data["choices"][0]["message"]
    code = clean_code(message.get("content") or "")
    if not code and attempt == 0:
        return request_solution(task_id, problem, 1)
    return {
        "task_id": task_id,
        "solution": code,
        "elapsed_s": elapsed,
        "finish_reason": data["choices"][0]["finish_reason"],
        "usage": data.get("usage", {}),
        "reasoning_chars": len(message.get("reasoning_content") or message.get("reasoning") or ""),
    }


def main():
    problems = get_human_eval_plus()
    done = {}
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                done[row["task_id"]] = row
    pending = [(task_id, p) for task_id, p in problems.items() if task_id not in done]
    print(json.dumps({"total": len(problems), "resuming": len(done), "pending": len(pending)}), flush=True)

    def run(item):
        task_id, problem = item
        for attempt in range(3):
            try:
                return request_solution(task_id, problem)
            except Exception as exc:
                if attempt == 2:
                    return {"task_id": task_id, "solution": "", "error": repr(exc)}
                time.sleep(2 ** attempt)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for index, row in enumerate(pool.map(run, pending), 1):
            done[row["task_id"]] = row
            ordered = [done[k] for k in problems if k in done]
            OUT.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in ordered))
            if index % 10 == 0 or index == len(pending):
                print(json.dumps({"completed_this_run": index, "total_complete": len(done), "last": row["task_id"]}), flush=True)

    rows = [done[k] for k in problems]
    metrics = {
        "dataset": "HumanEval+ v0.1.10 via evalplus 0.3.1",
        "tasks": len(rows),
        "temperature": 0,
        "initial_max_tokens": 4096,
        "empty_output_retry_max_tokens": 8192,
        "empty_output_retry_policy": "one retry only; retry output replaces initial request metrics",
        "concurrency": 4,
        "generation_failures": sum(1 for r in rows if r.get("error") or not r.get("solution")),
        "finish_reasons": {},
        "total_prompt_tokens": sum(r.get("usage", {}).get("prompt_tokens", 0) for r in rows),
        "total_completion_tokens": sum(r.get("usage", {}).get("completion_tokens", 0) for r in rows),
        "mean_request_s": sum(r.get("elapsed_s", 0) for r in rows) / len(rows),
    }
    for row in rows:
        reason = row.get("finish_reason", "error")
        metrics["finish_reasons"][reason] = metrics["finish_reasons"].get(reason, 0) + 1
    META.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics), flush=True)


if __name__ == "__main__":
    main()
