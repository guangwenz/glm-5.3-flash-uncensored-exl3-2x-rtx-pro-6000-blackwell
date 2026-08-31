#!/usr/bin/env python3
"""Fail-closed unit tests for the scheduler-aware tuning harness."""
from __future__ import annotations

import importlib.util
import json
import threading
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("tuning_benchmark.py")
SPEC = importlib.util.spec_from_file_location("tuning_benchmark", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load tuning benchmark module")
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


class TokenCounterTests(unittest.TestCase):
    def test_accepts_real_integer(self) -> None:
        self.assertEqual(BENCH.token_count(512, "completion_tokens", minimum=1), 512)

    def test_rejects_boolean_and_integral_float(self) -> None:
        for value in (False, True, 512.0):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    BENCH.token_count(value, "completion_tokens", minimum=1)


class NonStreamValidationTests(unittest.TestCase):
    def run_response(self, payload: dict) -> dict:
        with mock.patch.object(BENCH, "post", return_value=payload):
            return BENCH.nonstream("fixed fixture", 512)

    def test_accepts_exact_length_response(self) -> None:
        row = self.run_response(response())
        self.assertEqual(row["completion_tokens"], 512)
        self.assertEqual(row["finish_reason"], "length")

    def test_rejects_short_or_early_stopped_response(self) -> None:
        for payload in (
            response(completion_tokens=511),
            response(finish_reason="stop"),
            response(content=""),
            response(completion_tokens=False),
            response(prompt_tokens=36.0),
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(RuntimeError):
                    self.run_response(payload)


class StreamValidationTests(unittest.TestCase):
    class FakeStream(list):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    def run_stream(self, completion_tokens: object, finish_reason: str) -> dict:
        events = [
            {"choices": [{"delta": {"reasoning": "fixture"}}]},
            {
                "usage": {
                    "prompt_tokens": 36,
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
            return BENCH.stream("fixed fixture", 512)

    def test_accepts_exact_stream(self) -> None:
        row = self.run_stream(512, "length")
        self.assertEqual(row["completion_tokens"], 512)

    def test_rejects_non_comparable_streams(self) -> None:
        for count, reason in ((511, "length"), (512, "stop"), (512.0, "length")):
            with self.subTest(count=count, reason=reason):
                with self.assertRaises(RuntimeError):
                    self.run_stream(count, reason)


class MetricSamplingTests(unittest.TestCase):
    def test_sampler_records_errors_instead_of_suppressing_them(self) -> None:
        stop = threading.Event()
        samples: list[dict] = []
        errors: list[str] = []
        with mock.patch.object(BENCH, "metrics", side_effect=OSError("fixture failure")):
            BENCH.sample_until(stop, samples, errors)
        self.assertEqual(samples, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("fixture failure", errors[0])

    def test_required_metrics_rejects_missing_value(self) -> None:
        with self.assertRaises(RuntimeError):
            BENCH.require_metrics({"required": None})

    def test_finish_sampling_rejects_stuck_sampler(self) -> None:
        class StuckSampler:
            def join(self, timeout):
                self.timeout = timeout

            def is_alive(self):
                return True

        stop = threading.Event()
        with self.assertRaisesRegex(RuntimeError, "did not stop"):
            BENCH.finish_sampling(stop, StuckSampler(), [{}], [])
        self.assertTrue(stop.is_set())

    def test_finish_sampling_rejects_no_samples(self) -> None:
        class FinishedSampler:
            def join(self, timeout):
                self.timeout = timeout

            def is_alive(self):
                return False

        with self.assertRaisesRegex(RuntimeError, "no samples"):
            BENCH.finish_sampling(threading.Event(), FinishedSampler(), [], [])


class FixtureIdentityTests(unittest.TestCase):
    def test_label_is_metadata_only(self) -> None:
        source = MODULE_PATH.read_text()
        self.assertEqual(source.count("args.label"), 1)
        self.assertIn('"label": args.label', source)


if __name__ == "__main__":
    unittest.main()
