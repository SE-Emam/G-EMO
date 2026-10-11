import json
import tempfile
import unittest
from pathlib import Path

from core.native_command_pipeline import process_native_inbox
from core.native_inbox import GEMINI_PACKAGE


class RecordingExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, command, *, confirmed=False):
        self.calls.append((command, confirmed))
        return {"status": "CONFIRMATION_REQUIRED", "action": command["action"]}


class NativeCommandPipelineTests(unittest.TestCase):
    def test_valid_command_is_staged_unconfirmed(self):
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory)
            (inbox / "request.json").write_text(json.dumps({
                "request_id": "req-1",
                "source_package": GEMINI_PACKAGE,
                "timestamp_ms": 1_800_000_000_000,
                "command": "ابعت واتساب لأحمد: أهلا",
            }, ensure_ascii=False), encoding="utf-8")
            executor = RecordingExecutor()
            result = process_native_inbox(inbox, executor, now_ms=1_800_000_000_000)
            self.assertEqual(result[0]["status"], "CONFIRMATION_REQUIRED")
            self.assertEqual(len(executor.calls), 1)
            self.assertFalse(executor.calls[0][1])

    def test_invalid_record_never_reaches_executor(self):
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory)
            (inbox / "request.json").write_text(json.dumps({
                "request_id": "req-2",
                "source_package": "com.example.untrusted",
                "timestamp_ms": 1_800_000_000_000,
                "command": "ابعت واتساب لأحمد: أهلا",
            }, ensure_ascii=False), encoding="utf-8")
            executor = RecordingExecutor()
            self.assertEqual(process_native_inbox(inbox, executor, now_ms=1_800_000_000_000), [])
            self.assertEqual(executor.calls, [])

    def test_executor_exception_is_non_leaking_and_does_not_stop_batch(self):
        class BrokenExecutor:
            def execute(self, command, *, confirmed=False):
                raise RuntimeError("private provider token")
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory)
            (inbox / "request.json").write_text(json.dumps({
                "request_id": "req-3",
                "source_package": GEMINI_PACKAGE,
                "timestamp_ms": 1_800_000_000_000,
                "command": "ابعت واتساب لأحمد: أهلا",
            }, ensure_ascii=False), encoding="utf-8")
            result = process_native_inbox(inbox, BrokenExecutor(), now_ms=1_800_000_000_000)
            self.assertEqual(result[0]["status"], "FAILED")
            self.assertNotIn("private provider token", repr(result))


if __name__ == "__main__":
    unittest.main()
