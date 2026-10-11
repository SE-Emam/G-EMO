""""WhatsApp adapter with conservative transport validation and human fallback."""
from __future__ import annotations

import ipaddress
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


_API_VERSION = re.compile(r"^v[0-9]{1,3}\\.[0-9]{1,2}$")
_PHONE = re.compile(r"^\\+?[0-9]{8,15}$")
_MAX_MESSAGE_CHARS = 4096


class WhatsAppPlugin:
    def __init__(self, settings_path: str | Path = "config/settings.json", timeout: float = 12.0) -> None:
        self.settings_path = Path(settings_path)
        self.timeout = max(1.0, min(float(timeout), 30.0))

    def _config(self) -> dict[str, Any]:
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            item = data.get("whatsapp", {})
            return item if isinstance(item, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _api_version(config: dict[str, Any]) -> str | None:
        version = str(config.get("api_version") or "v22.0")
        return version if _API_VERSION.fullmatch(version) else None

    @staticmethod
    def _webjs_url(endpoint: Any, path: str) -> str | None:
        """Allow loopback HTTP only; remote bridge URLs must use HTTPS."""
        if not isinstance(endpoint, str) or not endpoint or len(endpoint) > 2048:
            return None
        try:
            parsed = urllib.parse.urlsplit(endpoint)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                return None
            if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
                return None
            hostname = parsed.hostname.rstrip(".").lower()
            is_loopback = hostname == "localhost"
            try:
                is_loopback = is_loopback or ipaddress.ip_address(hostname).is_loopback
            except ValueError:
                pass
            if parsed.scheme == "http" and not is_loopback:
                return None
            if parsed.port is not None and not (1 <= parsed.port <= 65535):
                return None
            base = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
            return base + path
        except ValueError:
            return None

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
        """Check the selected transport without sending a message."""
        config = self._config()
        transport = str(config.get("transport") or "human").lower()
        if transport == "human":
            return {"status": "HUMAN_FALLBACK", "plugin": "whatsapp", "detail": "Human mode is selected; no API connection is required"}
        if transport == "webjs":
            url = self._webjs_url(config.get("webjs_endpoint"), "/health")
            bridge_token = os.getenv("G_EMO_WHATSAPP_WEBJS_TOKEN") or config.get("webjs_token")
            if not url or not bridge_token:
                return {"status": "HUMAN_FALLBACK", "plugin": "whatsapp", "detail": "Bridge URL must be loopback HTTP or remote HTTPS; bridge credentials are required"}
            request = urllib.request.Request(url, headers={"Authorization": f"Bearer {bridge_token}"}, method="GET")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                    if response.status == 200 and isinstance(body, dict) and body.get("status") == "CONNECTED":
                        return {"status": "CONNECTED", "plugin": "whatsapp", "transport": "webjs"}
                    return {"status": "CONNECTION_FAILED", "plugin": "whatsapp", "http_status": response.status, "detail": "Bridge is not connected"}
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
                return {"status": "CONNECTION_FAILED", "plugin": "whatsapp", "detail": "Bridge connection failed; verify the endpoint and bridge logs"}
        if transport != "cloud_api":
            return {"status": "HUMAN_FALLBACK", "plugin": "whatsapp", "detail": "Unknown transport; human mode is the safe fallback"}
        token = os.getenv("G_EMO_WHATSAPP_ACCESS_TOKEN") or config.get("access_token")
        phone_id = config.get("phone_number_id")
        version = self._api_version(config)
        if not token or not phone_id or not version or not re.fullmatch(r"[0-9]{1,32}", str(phone_id)):
            return {"status": "HUMAN_FALLBACK", "plugin": "whatsapp", "detail": "Cloud API credentials or API version are invalid"}
        url = f"https://graph.facebook.com/{version}/{urllib.parse.quote(str(phone_id), safe='')}?fields=id,display_phone_number,verified_name"
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                if response.status == 200 and isinstance(body, dict) and body.get("id") == str(phone_id):
                    return {"status": "CONNECTED", "plugin": "whatsapp", "transport": "cloud_api", "phone_number_id": body.get("id"), "display_phone_number": body.get("display_phone_number")}
                return {"status": "CONNECTION_FAILED", "plugin": "whatsapp", "http_status": response.status, "detail": "Meta returned an unexpected response"}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
            return {"status": "CONNECTION_FAILED", "plugin": "whatsapp", "detail": "Meta connection failed; verify credentials and network"}

    def _send_cloud_api(self, command: dict[str, Any], config: dict[str, Any], token: str) -> dict[str, Any]:
        phone_id = config.get("phone_number_id")
        recipient = command.get("phone") or command.get("to_phone")
        message = command.get("text")
        version = self._api_version(config)
        if (not phone_id or not re.fullmatch(r"[0-9]{1,32}", str(phone_id)) or not version
                or not isinstance(recipient, str) or not _PHONE.fullmatch(recipient)
                or not isinstance(message, str) or not message.strip() or len(message) > _MAX_MESSAGE_CHARS):
            return {"status": "INVALID_REQUEST", "plugin": "whatsapp", "detail": "Valid phone_number_id, international phone number, and text of 1..4096 characters are required"}
        url = f"https://graph.facebook.com/{version}/{urllib.parse.quote(str(phone_id), safe='')}/messages"
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient.lstrip("+"),
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }).encode("utf-8")
        request = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                messages = body.get("messages") if isinstance(body, dict) else None
                message_id = messages[0].get("id") if isinstance(messages, list) and messages and isinstance(messages[0], dict) else None
                if response.status == 200 and message_id:
                    return {"status": "SENT", "plugin": "whatsapp", "transport": "cloud_api", "http_status": 200, "message_id": message_id}
                return {"status": "SEND_FAILED", "plugin": "whatsapp", "http_status": response.status, "detail": "Meta did not confirm message acceptance"}
        except urllib.error.HTTPError as exc:
            # Never return raw provider error bodies, which may contain private metadata.
            return {"status": "SEND_FAILED", "plugin": "whatsapp", "http_status": exc.code, "detail": "Meta Graph API rejected the request"}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
            return {"status": "SEND_FAILED", "plugin": "whatsapp", "detail": "Meta request failed; check network and provider logs"}

    def _send_webjs(self, command: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        url = self._webjs_url(config.get("webjs_endpoint"), "/send")
        bridge_token = os.getenv("G_EMO_WHATSAPP_WEBJS_TOKEN") or config.get("webjs_token")
        if not url or not bridge_token:
            return self.send_human(command, "Bridge URL or credentials are invalid; use WhatsApp manually")
        recipient = command.get("phone") or command.get("to_phone")
        message = command.get("text")
        if not isinstance(recipient, str) or not _PHONE.fullmatch(recipient) or not isinstance(message, str) or not message.strip() or len(message) > _MAX_MESSAGE_CHARS:
            return {"status": "INVALID_REQUEST", "plugin": "whatsapp", "detail": "Valid international phone number and text of 1..4096 characters are required"}
        payload = json.dumps({"to": recipient.lstrip("+"), "text": message}).encode("utf-8")
        request = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {bridge_token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                if response.status == 200 and isinstance(body, dict) and body.get("status") == "SENT":
                    return {"status": "SENT", "plugin": "whatsapp", "transport": "webjs", "http_status": 200}
                return {"status": "SEND_FAILED", "plugin": "whatsapp", "http_status": response.status, "detail": "Bridge did not confirm message acceptance"}
        except (urllib.error.URLError, TimeoutError, urllib.error.HTTPError, json.JSONDecodeError, UnicodeDecodeError):
            return {"status": "SEND_FAILED", "plugin": "whatsapp", "detail": "Bridge send failed; check bridge status and logs"}

    def execute(self, command: dict[str, Any], *, confirmed: bool = False) -> dict[str, Any]:
        if not confirmed:
            return {"status": "CONFIRMATION_REQUIRED", "plugin": "whatsapp"}
        config = self._config()
        token = os.getenv("G_EMO_WHATSAPP_ACCESS_TOKEN") or config.get("access_token")
        transport = str(config.get("transport") or command.get("mode") or "human").lower()
        if transport == "cloud_api":
            if not token or not config.get("phone_number_id"):
                return self.send_human(command, "Cloud API credentials incomplete; automatically falling back to human mode")
            return self._send_cloud_api(command, config, str(token))
        if transport == "webjs":
            return self._send_webjs(command, config)
        return self.send_human(command)
