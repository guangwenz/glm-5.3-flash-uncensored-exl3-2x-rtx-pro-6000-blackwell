#!/usr/bin/env python3
"""Fail-closed tests for the standardized performance benchmark."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("performance_benchmark.py")
SPEC = importlib.util.spec_from_file_location("performance_benchmark", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load performance benchmark module")
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)


def response(
    *,
    prompt_tokens: object = 36,
    completion_tokens: object = 512,
    finish_reason: str = "length",
    content: str = "fixture output",
) -> dict:
    return {
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"content": content},
            }
        ],
    }


class CounterAndTokenizerTests(unittest.TestCase):
    def test_counter_is_type_strict(self) -> None:
        self.assertEqual(BENCH.token_count(32, "count", 1), 32)
        for value in (False, True, 32.0, 0):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    BENCH.token_count(value, "count", 1)

    def test_tokenizer_requires_integer_id_list(self) -> None:
        with mock.patch.object(BENCH, "post_json", return_value={"tokens": [1, 2, 3]}):
            self.assertEqual(BENCH.tokenize("fixture"), 3)
        for tokens in (None, [1, False], [1, 2.0], "1,2"):
            with self.subTest(tokens=tokens):
                with mock.patch.object(BENCH, "post_json", return_value={"tokens": tokens}):
                    with self.assertRaises(RuntimeError):
                        BENCH.tokenize("fixture")


class NonStreamTests(unittest.TestCase):
    def run_response(self, payload: dict) -> dict:
        with mock.patch.object(BENCH, "post_json", return_value=payload):
            return BENCH.nonstream_one("fixed fixture", 512)

    def test_accepts_exact_nonempty_response(self) -> None:
        row = self.run_response(response())
        self.assertEqual(row["completion_tokens"], 512)
        self.assertEqual(row["finish_reason"], "length")

    def test_rejects_invalid_response(self) -> None:
        invalid = (
            response(completion_tokens=511),
            response(finish_reason="stop"),
            response(content=""),
            response(completion_tokens=False),
            response(prompt_tokens=36.0),
            response(prompt_tokens=262000),
        )
        for payload in invalid:
            with self.subTest(payload=payload):
                with self.assertRaises(RuntimeError):
                    self.run_response(payload)


class StreamTests(unittest.TestCase):
    class FakeStream(list):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    def run_stream(
        self,
        completion_tokens: object = 32,
        finish_reason: str = "length",
        prompt_tokens: object = 1035,
    ) -> dict:
        events = [
            {"choices": [{"delta": {"reasoning_content": "fixture"}}]},
            {
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                },
                "choices": [],
            },
            {"choices": [{"delta": {}, "finish_reason": finish_reason}]},
        ]
        lines = [f"data: {json.dumps(event)}\n".encode() for event in events]
        lines.append(b"data: [DONE]\n")
        with mock.patch.object(
            BENCH.urllib.request,
            "urlopen",
            return_value=self.FakeStream(lines),
        ):
            return BENCH.stream_chat("fixed fixture", 32)

    def test_accepts_exact_stream(self) -> None:
        row = self.run_stream()
        self.assertEqual(row["completion_tokens"], 32)
        self.assertEqual(row["finish_reason"], "length")

    def test_rejects_invalid_stream(self) -> None:
        invalid = (
            (31, "length", 1035),
            (32, "stop", 1035),
            (32.0, "length", 1035),
            (32, "length", 262120),
        )
        for count, reason, prompt in invalid:
            with self.subTest(count=count, reason=reason, prompt=prompt):
                with self.assertRaises(RuntimeError):
                    self.run_stream(count, reason, prompt)


if __name__ == "__main__":
    unittest.main()
