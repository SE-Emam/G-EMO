"""Consume explicit commands written by the native Android accessibility bridge.

The bridge is optional outside Android. Inbox records are untrusted and must pass
package, age, size, prefix, and parser checks before they can reach an executor.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from core.brain import ParseError, parse_command

GEMINI_PACKAGE = "com.google.android.apps.bard"
MAX_RECORD_BYTES = 8192
MAX_COMMAND_AGE_MS = 120_000


def android_files_dir() -> Path | None:
    """Return Android app-private files directory, or None off-device/unavailable."""
    try:
        from jnius import autoclass
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        return Path(str(activity.getFilesDir().getAbsolutePath()))
    except Exception:
        return None


def consume_inbox(inbox_dir: str | Path, *, now_ms: int | None = None) -> list[dict[str, Any]]:
    """Consume and validate pending records; invalid records are deleted fail-closed."""
    root = Path(inbox_dir)
    if not root.is_dir():
        return []
    current = int(time.time() * 1000) if now_ms is None else now_ms
    accepted: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            if path.stat().st_size > MAX_RECORD_BYTES:
                continue
            raw = path.read_text(encoding="utf-8")
            record = json.loads(raw)
            if not isinstance(record, dict):
                continue
            request_id = record.get("request_id")
            package = record.get("source_package")
            timestamp = record.get("timestamp_ms")
            command_text = record.get("command")
            if not isinstance(request_id, str) or not request_id or len(request_id) > 64:
                continue
            if package != GEMINI_PACKAGE:
                continue
            if not isinstance(timestamp, int) or abs(current - timestamp) > MAX_COMMAND_AGE_MS:
                continue
            if not isinstance(command_text, str) or not command_text.strip() or len(command_text) > 1000:
                continue
            # Native bridge extracts only text after EMO:, but require the prefix again
            # at this trust boundary so a forged/stale file cannot invoke a skill.
            addressed = "EMO: " + command_text.strip()
            try:
                command = parse_command(addressed)
            except ParseError:
                continue
            accepted.append({
                "request_id": request_id,
                "source_package": package,
                "timestamp_ms": timestamp,
                "command": command,
            })
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            # Invalid files are never executed; continue processing other records.
            pass
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
    return accepted
