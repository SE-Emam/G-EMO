"""Base result contract shared by G-EMO plugins."""
from __future__ import annotations
from typing import Any

class NotConfiguredPlugin:
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, command: dict[str, Any], *, confirmed: bool = False) -> dict[str, Any]:
        mode = command.get("mode", "human")
        if mode == "api":
            return {"status": "NOT_CONFIGURED", "plugin": self.name, "detail": "Official API adapter and user credentials are not configured"}
        return {"status": "HUMAN_ACTION_REQUIRED", "plugin": self.name, "detail": "Open the target app and complete or verify the action manually"}
