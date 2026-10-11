"""Bridge validated Gemini commands to the existing policy-enforcing executor."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from core.native_inbox import consume_inbox


class CommandExecutor(Protocol):
    def execute(self, command: dict[str, Any], *, confirmed: bool = False) -> dict[str, Any]: ...


def process_native_inbox(
    inbox_dir: str | Path,
    executor: CommandExecutor,
    *,
    now_ms: int | None = None,
) -> list[dict[str, Any]]:
    """Consume parsed commands and stage them with confirmation always false.

    This function intentionally has no parameter that can mark commands approved.
    A future UI approval action must separately verify the exact pending request
    before calling the executor with confirmed=True.
    """
    outcomes: list[dict[str, Any]] = []
    for record in consume_inbox(inbox_dir, now_ms=now_ms):
        command = record["command"]
        try:
            result = executor.execute(command, confirmed=False)
            if not isinstance(result, dict):
                result = {"status": "FAILED", "reason": "INVALID_EXECUTOR_RESULT"}
        except Exception:
            result = {"status": "FAILED", "reason": "EXECUTOR_ERROR"}
        outcomes.append({
            "request_id": record["request_id"],
            "status": result.get("status", "FAILED"),
            "action": command.get("action"),
            "result": result,
        })
    return outcomes
