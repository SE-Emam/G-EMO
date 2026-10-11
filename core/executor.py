"""Policy-enforcing plugin dispatcher for G-EMO."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

class Plugin(Protocol):
    def execute(self, command: dict[str, Any], *, confirmed: bool = False) -> dict[str, Any]: ...

class ExecutionError(RuntimeError):
    pass

class Executor:
    def __init__(self, settings_path: str | Path, plugins: dict[str, Plugin]) -> None:
        self.settings_path = Path(settings_path)
        self.plugins = plugins

    def _settings(self) -> dict[str, Any]:
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExecutionError("Settings unavailable or invalid; execution blocked") from exc
        if not isinstance(data, dict):
            raise ExecutionError("Settings must be a JSON object")
        return data

    def execute(self, command: dict[str, Any], *, confirmed: bool = False) -> dict[str, Any]:
        action = command.get("action")
        if not isinstance(action, str) or not action:
            raise ExecutionError("Missing action")
        plugin_name = action.split("_", 1)[-1] if action.startswith(("send_", "read_", "post_", "monitor_", "open_", "search_")) else action
        # Explicit action-to-plugin map avoids deriving arbitrary module names.
        action_plugins = {
            "send_whatsapp": "whatsapp", "read_whatsapp": "whatsapp",
            "post_facebook": "facebook", "monitor_facebook": "facebook",
            "send_telegram": "telegram", "open_canva": "canva",
            "search_drive": "drive", "send_email": "email",
        }
        plugin_name = action_plugins.get(action)
        if not plugin_name:
            raise ExecutionError("Unsupported action")
        config = self._settings().get(plugin_name, {})
        if not isinstance(config, dict) or config.get("enabled") is not True:
            return {"status": "DISABLED", "plugin": plugin_name}
        mode = config.get("mode")
        if mode not in {"human", "api"}:
            raise ExecutionError("Plugin mode must be human or api")
        plugin = self.plugins.get(plugin_name)
        if plugin is None:
            return {"status": "NOT_IMPLEMENTED", "plugin": plugin_name, "mode": mode}
        if command.get("requires_confirmation", True) and not confirmed:
            return {"status": "CONFIRMATION_REQUIRED", "plugin": plugin_name, "action": action}
        return plugin.execute({**command, "mode": mode}, confirmed=confirmed)
