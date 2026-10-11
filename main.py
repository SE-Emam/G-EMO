"""G-EMO setup screen with explicit WhatsApp transport configuration."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.utils import get_color_from_hex

from plugins.whatsapp_plugin import WhatsAppPlugin


BLUE = get_color_from_hex("#0846ED")
DARK = get_color_from_hex("#303846")
GRAY = get_color_from_hex("#606875")


class EmoSetupApp(App):
    title = "EMO"

    def build(self):
        self.settings_path = Path(self.user_data_dir) / "settings.json"
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.settings_path.exists():
            bundled = Path(__file__).parent / "config" / "settings.json"
            if bundled.exists():
                self.settings_path.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                self.settings_path.write_text(json.dumps({"whatsapp": {"enabled": True, "mode": "human", "transport": "human", "phone_number_id": "", "access_token": "", "api_version": "v22.0", "webjs_endpoint": "", "webjs_token": "", "monitor": False}}, indent=2), encoding="utf-8")
        self.settings = self._load_settings()

        root = BoxLayout(orientation="vertical", padding=18, spacing=10)
        root.add_widget(Label(
            text="[b]G-EMO[/b] — Setup",
            markup=True, font_size="25sp", color=BLUE,
            size_hint_y=None, height="44dp"
        ))
        root.add_widget(Label(
            text="No separate chat. Configure optional WhatsApp transports below. Sending still requires explicit confirmation.",
            halign="left", valign="middle", color=DARK,
            size_hint_y=None, height="54dp"
        ))

        root.add_widget(Label(text="WhatsApp transport", color=DARK, size_hint_y=None, height="24dp", halign="left"))
        self.transport = Spinner(
            text=self.settings.get("whatsapp", {}).get("transport", "human"),
            values=("human", "cloud_api", "webjs"),
            size_hint_y=None, height="46dp"
        )
        root.add_widget(self.transport)

        self.phone_id = self._field(root, "Meta phone_number_id", self.settings.get("whatsapp", {}).get("phone_number_id", ""))
        self.access_token = self._field(root, "Cloud API access token (private app storage)", self.settings.get("whatsapp", {}).get("access_token", ""), password=True)
        self.webjs_endpoint = self._field(root, "WhatsApp Web bridge URL", self.settings.get("whatsapp", {}).get("webjs_endpoint", "http://127.0.0.1:8787"))
        self.webjs_token = self._field(root, "Bridge bearer token", self.settings.get("whatsapp", {}).get("webjs_token", ""), password=True)

        self.status = Label(text="Ready — human mode is the safe default.", color=GRAY, size_hint_y=None, height="58dp", halign="left", valign="middle")
        root.add_widget(self.status)

        save_button = Button(text="Save WhatsApp Settings", size_hint_y=None, height="48dp", background_normal="", background_color=BLUE)
        save_button.bind(on_press=self.save_settings)
        root.add_widget(save_button)
        test_button = Button(text="Test Cloud API Connection", size_hint_y=None, height="48dp", background_normal="", background_color=BLUE)
        test_button.bind(on_press=self.test_connection)
        root.add_widget(test_button)
        root.add_widget(Label(
            text="Security: settings are stored in this app's private files directory, but tokens are not yet encrypted with Android Keystore. Use a test token until secure native storage is implemented. The webjs option requires a separately running bridge.",
            color=GRAY, halign="left", valign="middle"
        ))
        return root

    def _field(self, root, caption, value, password=False):
        root.add_widget(Label(text=caption, color=DARK, size_hint_y=None, height="22dp", halign="left"))
        field = TextInput(text=str(value or ""), password=password, multiline=False, size_hint_y=None, height="44dp")
        root.add_widget(field)
        return field

    def _load_settings(self):
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def save_settings(self, *_):
        settings = self._load_settings()
        whatsapp = settings.get("whatsapp")
        if not isinstance(whatsapp, dict):
            whatsapp = {}
        transport = self.transport.text if self.transport.text in {"human", "cloud_api", "webjs"} else "human"
        whatsapp.update({
            "enabled": True,
            "mode": "human" if transport == "human" else "api",
            "transport": transport,
            "phone_number_id": self.phone_id.text.strip(),
            "access_token": self.access_token.text.strip(),
            "api_version": whatsapp.get("api_version") or "v22.0",
            "webjs_endpoint": self.webjs_endpoint.text.strip(),
            "webjs_token": self.webjs_token.text.strip(),
            "monitor": False,
        })
        settings["whatsapp"] = whatsapp
        temp_path = self.settings_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(temp_path, 0o600)
        temp_path.replace(self.settings_path)
        self.status.text = "Saved to app-private settings. Missing Cloud API credentials automatically use human mode."
        return settings

    def test_connection(self, *_):
        settings = self.save_settings()
        if settings["whatsapp"].get("transport") != "cloud_api":
            self.status.text = "Select cloud_api to test Meta credentials. No message will be sent."
            return
        self.status.text = "Testing connection… no message will be sent."
        def run_test():
            result = WhatsAppPlugin(self.settings_path).test_connection()
            Clock.schedule_once(lambda _dt: self._show_test_result(result), 0)
        threading.Thread(target=run_test, daemon=True).start()

    def _show_test_result(self, result):
        status = result.get("status", "CONNECTION_FAILED")
        if status == "CONNECTED":
            phone = result.get("display_phone_number") or result.get("phone_number_id") or ""
            self.status.text = f"CONNECTED — {phone}. Connection verified; no message was sent."
        elif status == "HUMAN_FALLBACK":
            self.status.text = "HUMAN MODE — credentials missing. Use WhatsApp manually."
        else:
            self.status.text = f"CONNECTION FAILED — {result.get('http_status', '')} {result.get('detail', '')}"

if __name__ == "__main__":
    EmoSetupApp().run()
