"""Declarative, default-deny registry for mobile-agent skills.

This is a platform-neutral policy layer. It does not itself grant Android permissions
or provide a native Android bridge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
import re
import time

_PERMISSION_STATES = {"GRANTED", "NOT_GRANTED", "NOT_APPLICABLE", "CHECK_FAILED", "ACTION_REQUIRED"}
_SKILL_ID = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")
_SENSITIVE_KEYS = {"text", "body", "message", "content", "token", "password", "email", "phone", "recipient"}


@dataclass(frozen=True)
class SkillSpec:
    skill_id: str
    version: str
    description: str
    input_schema: Mapping[str, Any]
    required_permissions: tuple[str, ...] = ()
    side_effect: str = "read_only"  # read_only | write | destructive | external
    requires_approval: bool = False
    timeout_seconds: int = 15

    def __post_init__(self) -> None:
        if not _SKILL_ID.fullmatch(self.skill_id):
            raise ValueError("Invalid skill_id")
        if not self.version.strip() or not self.description.strip():
            raise ValueError("Skill version and description are required")
        if self.side_effect not in {"read_only", "write", "destructive", "external"}:
            raise ValueError("Invalid side_effect")
        if self.timeout_seconds < 1 or self.timeout_seconds > 300:
            raise ValueError("timeout_seconds must be between 1 and 300")
        if not isinstance(self.input_schema, Mapping):
            raise ValueError("input_schema must be a mapping")
        props = self.input_schema.get("properties", {})
        required = self.input_schema.get("required", [])
        if not isinstance(props, Mapping) or not isinstance(required, list):
            raise ValueError("Invalid input schema")
        if any(key not in props for key in required):
            raise ValueError("Required input field is missing from properties")


@dataclass(frozen=True)
class SkillResult:
    status: str
    skill_id: str
    result: Any = None
    reason: str | None = None
    elapsed_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "skill_id": self.skill_id,
            "result": self.result,
            "reason": self.reason,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass
class _RegisteredSkill:
    spec: SkillSpec
    handler: Callable[[dict[str, Any]], Any]


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "null":
        return value is None
    return False


def _redacted_fields(data: Mapping[str, Any]) -> list[str]:
    """Return field names only; never copy user values into audit records."""
    return sorted(str(key) for key in data if str(key).lower() in _SENSITIVE_KEYS)


class SkillRegistry:
    """Explicit registration, least-privilege preflight, and auditable dispatch."""

    def __init__(self, audit_sink: Callable[[dict[str, Any]], None] | None = None) -> None:
        self._skills: dict[str, _RegisteredSkill] = {}
        self._audit_sink = audit_sink

    def register(self, spec: SkillSpec, handler: Callable[[dict[str, Any]], Any]) -> None:
        if spec.skill_id in self._skills:
            raise ValueError("Skill already registered")
        if not callable(handler):
            raise ValueError("Skill handler must be callable")
        self._skills[spec.skill_id] = _RegisteredSkill(spec, handler)

    def describe(self) -> list[dict[str, Any]]:
        return [{
            "skill_id": item.spec.skill_id,
            "version": item.spec.version,
            "description": item.spec.description,
            "required_permissions": list(item.spec.required_permissions),
            "side_effect": item.spec.side_effect,
            "requires_approval": item.spec.requires_approval,
            "timeout_seconds": item.spec.timeout_seconds,
        } for item in sorted(self._skills.values(), key=lambda entry: entry.spec.skill_id)]

    def _audit(self, skill_id: str, status: str, reason: str | None, inputs: Mapping[str, Any], elapsed_ms: int) -> None:
        if self._audit_sink is None:
            return
        # Only names of sensitive fields are recorded; values and handler output are excluded.
        event = {
            "event": "skill_execution",
            "skill_id": skill_id,
            "status": status,
            "reason": reason,
            "input_field_names": sorted(str(key) for key in inputs),
            "redacted_field_names": _redacted_fields(inputs),
            "elapsed_ms": elapsed_ms,
        }
        try:
            self._audit_sink(event)
        except Exception:
            # Audit sink failure must not cause an action to be re-run.
            pass

    def execute(
        self,
        skill_id: str,
        inputs: Mapping[str, Any],
        *,
        permission_states: Mapping[str, str],
        approved: bool = False,
    ) -> SkillResult:
        started = time.monotonic()
        registered = self._skills.get(skill_id)
        if registered is None:
            return self._result(skill_id, "REJECTED", "UNKNOWN_SKILL", inputs, started)
        spec = registered.spec
        if not isinstance(inputs, Mapping):
            return self._result(skill_id, "REJECTED", "INVALID_INPUT", {}, started)
        schema = spec.input_schema
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if any(key not in inputs for key in required):
            return self._result(skill_id, "REJECTED", "MISSING_REQUIRED_INPUT", inputs, started)
        if schema.get("additionalProperties", False) is False and any(key not in properties for key in inputs):
            return self._result(skill_id, "REJECTED", "UNDECLARED_INPUT_FIELD", inputs, started)
        for key, value in inputs.items():
            definition = properties.get(key)
            if definition is None or not isinstance(definition, Mapping):
                return self._result(skill_id, "REJECTED", "INVALID_INPUT_SCHEMA", inputs, started)
            expected = definition.get("type")
            if expected and not _matches_type(value, expected):
                return self._result(skill_id, "REJECTED", "INVALID_INPUT_TYPE", inputs, started)
            if isinstance(value, str) and len(value) > int(definition.get("maxLength", 4000)):
                return self._result(skill_id, "REJECTED", "INPUT_TOO_LONG", inputs, started)
        for permission in spec.required_permissions:
            state = permission_states.get(permission, "CHECK_FAILED")
            if state not in _PERMISSION_STATES:
                state = "CHECK_FAILED"
            if state != "GRANTED" and state != "NOT_APPLICABLE":
                return self._result(skill_id, "ACTION_REQUIRED", f"PERMISSION_{state}:{permission}", inputs, started)
        if (spec.requires_approval or spec.side_effect in {"write", "destructive", "external"}) and not approved:
            return self._result(skill_id, "NEEDS_APPROVAL", "USER_APPROVAL_REQUIRED", inputs, started)
        try:
            result = registered.handler(dict(inputs))
        except Exception:
            return self._result(skill_id, "FAILED", "HANDLER_ERROR", inputs, started)
        return self._result(skill_id, "SUCCEEDED", None, inputs, started, result=result)

    def _result(self, skill_id: str, status: str, reason: str | None, inputs: Mapping[str, Any],
                started: float, result: Any = None) -> SkillResult:
        elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
        self._audit(skill_id, status, reason, inputs, elapsed_ms)
        return SkillResult(status, skill_id, result, reason, elapsed_ms)
