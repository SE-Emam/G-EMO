"""In-memory, one-time approval broker for pending mobile-agent actions."""
from __future__ import annotations

from dataclasses import dataclass
import time
import uuid
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class PendingApproval:
    approval_id: str
    request_id: str
    command: dict[str, Any]
    created_at_ms: int
    expires_at_ms: int


class ApprovalBroker:
    """Hold exact pending commands in memory; never persist them or auto-approve."""

    def __init__(self, *, ttl_ms: int = 120_000, clock_ms: Callable[[], int] | None = None) -> None:
        if ttl_ms < 1 or ttl_ms > 600_000:
            raise ValueError("ttl_ms must be between 1 and 600000")
        self.ttl_ms = ttl_ms
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self._pending: dict[str, PendingApproval] = {}

    def stage(self, request_id: str, command: Mapping[str, Any]) -> PendingApproval:
        if not isinstance(request_id, str) or not request_id or len(request_id) > 64:
            raise ValueError("Invalid request_id")
        if not isinstance(command, Mapping) or not isinstance(command.get("action"), str):
            raise ValueError("Invalid command")
        now = self._clock_ms()
        approval_id = uuid.uuid4().hex
        pending = PendingApproval(
            approval_id=approval_id,
            request_id=request_id,
            command=dict(command),
            created_at_ms=now,
            expires_at_ms=now + self.ttl_ms,
        )
        self._pending[approval_id] = pending
        self._purge_expired(now)
        return pending

    def list_pending(self) -> list[dict[str, Any]]:
        now = self._clock_ms()
        self._purge_expired(now)
        return [{
            "approval_id": item.approval_id,
            "request_id": item.request_id,
            "action": item.command["action"],
            "expires_at_ms": item.expires_at_ms,
        } for item in self._pending.values()]

    def approve(self, approval_id: str, executor: Any) -> dict[str, Any]:
        now = self._clock_ms()
        self._purge_expired(now)
        pending = self._pending.pop(approval_id, None)
        if pending is None:
            return {"status": "REJECTED", "reason": "UNKNOWN_EXPIRED_OR_ALREADY_USED_APPROVAL"}
        try:
            result = executor.execute(pending.command, confirmed=True)
            if not isinstance(result, dict):
                return {"status": "FAILED", "reason": "INVALID_EXECUTOR_RESULT"}
            return {
                "status": result.get("status", "FAILED"),
                "request_id": pending.request_id,
                "action": pending.command["action"],
                "result": result,
            }
        except Exception:
            return {"status": "FAILED", "reason": "EXECUTOR_ERROR", "request_id": pending.request_id}

    def reject(self, approval_id: str) -> bool:
        return self._pending.pop(approval_id, None) is not None

    def _purge_expired(self, now: int) -> None:
        expired = [key for key, item in self._pending.items() if item.expires_at_ms <= now]
        for key in expired:
            self._pending.pop(key, None)
