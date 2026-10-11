"""WhatsApp adapter with safe automatic human fallback.

Supported transports:
- human: never sends; asks the user to complete the action.
- cloud_api: official Meta WhatsApp Cloud API; requires phone_number_id + access_token.
- webjs: optional user-run whatsapp-web.js bridge; unofficial and not bundled here.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class WhatsAppPlugin:
    def __init__(self, settings_path: str | Path = "config/settings.json", timeout: float = 12.0) -> None:
        self.settings_path = Path(settings_path)
        self.timeout = timeout

    def _config(self) -> dict[str, Any]:
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            item = data.get("whatsapp", {})
            return item if isinstance(item, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def send_human(command: dict[str, Any], detail: str = "Open WhatsApp and complete the action manually") -> dict[str, Any]:
        return {
            "status": "HUMAN_ACTION_REQUIRED",
            "plugin": "whatsapp",
            "mode": "human",
            "detail": detail,
            "to": command.get("to"),
            "text": command.get("text"),
        }

    def test_connection(self) -> dict[str, Any]:
        """Validate Cloud API credentials without sending a message."""
        config = self._config()
        token = os.getenv("G_EMO_WHATSAPP_ACCESS_TOKEN") or config.get("access_token")
        phone_id = config.get("phone_number_id")
        if not token or not phone_id:
            return {"status": "HUMAN_FALLBACK", "plugin": "whatsapp", "detail": "Cloud API credentials missing"}
        version = str(config.get("api_version") or "v22.0")
        url = f"https://graph.facebook.com/{version}/{urllib.parse.quote(str(phone_id), safe='')}?fields=id,display_phone_number,verified_name"
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                if response.status == 200:
                    return {"status": "CONNECTED", "plugin": "whatsapp", "phone_number_id": body.get("id"), "display_phone_number": body.get("display_phone_number")}
                return {"status": "CONNECTION_FAILED", "plugin": "whatsapp", "http_status": response.status}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {"status": "CONNECTION_FAILED", "plugin": "whatsapp", "detail": str(exc)}

    def _send_cloud_api(self, command: dict[str, Any], config: dict[str, Any], token: str) -> dict[str, Any]:
        phone_id = config.get("phone_number_id")
        recipient = command.get("phone") or command.get("to_phone")
        message = command.get("text")
        if not phone_id or not recipient or not isinstance(message, str) or not message.strip():
            return {"status": "INVALID_REQUEST", "plugin": "whatsapp", "detail": "phone_number_id, recipient phone (E.164), and non-empty text are required"}
        version = str(config.get("api_version") or "v22.0")
        url = f"https://graph.facebook.com/{version}/{urllib.parse.quote(str(phone_id), safe='')}/messages"
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": str(recipient).replace("+", ""),
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }).encode("utf-8")
        request = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                if response.status == 200:
                    return {"status": "SENT", "plugin": "whatsapp", "transport": "cloud_api", "http_status": 200, "message_id": (body.get("messages") or [{}])[0].get("id")}
                return {"status": "SEND_FAILED", "plugin": "whatsapp", "http_status": response.status}
        except urllib.error.HTTPError as exc:
            # Do not silently downgrade API failures to human mode: credentials exist,
            # so report the actual API failure rather than implying a message was sent.
            try:
                detail = json.loads(exc.read().decode("utf-8"))
            except (ValueError, json.JSONDecodeError):
                detail = {"message": "Meta Graph API request failed"}
            return {"status": "SEND_FAILED", "plugin": "whatsapp", "http_status": exc.code, "detail": detail}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {"status": "SEND_FAILED", "plugin": "whatsapp", "detail": str(exc)}

    def _send_webjs(self, command: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        endpoint = config.get("webjs_endpoint")
        bridge_token = os.getenv("G_EMO_WHATSAPP_WEBJS_TOKEN") or config.get("webjs_token")
        if not endpoint or not bridge_token:
            return self.send_human(command, "whatsapp-web.js bridge is not configured; use WhatsApp manually")
        payload = json.dumps({"to": command.get("phone") or command.get("to_phone"), "text": command.get("text")}).encode("utf-8")
        request = urllib.request.Request(str(endpoint).rstrip("/") + "/send", data=payload, headers={"Authorization": f"Bearer {bridge_token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                if response.status == 200 and body.get("status") == "SENT":
                    return {"status": "SENT", "plugin": "whatsapp", "transport": "webjs", "http_status": 200}
                return {"status": "SEND_FAILED", "plugin": "whatsapp", "http_status": response.status, "detail": body}
        except (urllib.error.URLError, TimeoutError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            return {"status": "SEND_FAILED", "plugin": "whatsapp", "detail": str(exc)}

    def execute(self, command: dict[str, Any], *, confirmed: bool = False) -> dict[str, Any]:
        if not confirmed:
            return {"status": "CONFIRMATION_REQUIRED", "plugin": "whatsapp"}
        config = self._config()
        # The golden rule: absent credentials always mean human mode, never a crash.
        token = os.getenv("G_EMO_WHATSAPP_ACCESS_TOKEN") or config.get("access_token")
        transport = str(config.get("transport") or command.get("mode") or "human").lower()
        if transport == "cloud_api":
            if not token or not config.get("phone_number_id"):
                return self.send_human(command, "Cloud API credentials incomplete; automatically falling back to human mode")
            return self._send_cloud_api(command, config, str(token))
        if transport == "webjs":
            return self._send_webjs(command, config)
        return self.send_human(command)
