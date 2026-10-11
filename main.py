"""G-EMO setup screen. Provider secrets are never persisted in settings JSON."""
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
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex

from core.secure_storage import AndroidKeystoreTokenStore, SecureStorageError
from core.android_keystore_smoke import run_requested_self_test
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
                self.settings_path.write_text(json.dumps({"whatsapp": {"enabled": True, "mode": "human", "transport": "human"}}, indent=2), encoding="utf-8")
        self.status = None
        self.secret_store = None
        self._secure_storage_error = ""
        self._initialize_secure_storage()
        self.settings = self._load_settings()
        # Only runs when an explicit private marker is placed in app data (emulator CI).
        run_requested_self_test(self.settings_path, self.secret_store, self._write_settings)

        root = BoxLayout(orientation="vertical", padding=18, spacing=10)
        root.size_hint_y = None
        root.bind(minimum_height=root.setter("height"))
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
        self.accessibility_status = Label(
            text="Gemini bridge status: checking Android service and opt-in…",
            color=GRAY, halign="left", valign="middle",
            size_hint_y=None, height="48dp"
        )
        root.add_widget(self.accessibility_status)
        permission_check = Button(
            text="Check Gemini Accessibility Status",
            size_hint_y=None, height="44dp", background_normal="", background_color=BLUE
        )
        permission_check.bind(on_press=self.check_accessibility_status)
        root.add_widget(permission_check)
        permission_settings = Button(
            text="Open Android Accessibility Settings",
            size_hint_y=None, height="44dp", background_normal="", background_color=BLUE
        )
        permission_settings.bind(on_press=self.open_accessibility_settings)
        root.add_widget(permission_settings)
        Clock.schedule_once(self.check_accessibility_status, 0)
        root.add_widget(Label(text="WhatsApp transport", color=DARK, size_hint_y=None, height="24dp", halign="left"))
        self.transport = Spinner(
            text=self.settings.get("whatsapp", {}).get("transport", "human"),
            values=("human", "cloud_api", "webjs"),
            size_hint_y=None, height="46dp"
        )
        root.add_widget(self.transport)
        self.phone_id = self._field(root, "Meta phone_number_id", self.settings.get("whatsapp", {}).get("phone_number_id", ""))
        # Secrets are deliberately not loaded into widgets or written back to JSON.
        self.access_token = self._field(root, "Meta access token (encrypted Android Keystore)", "", password=True)
        self.webjs_endpoint = self._field(root, "WhatsApp Web bridge URL", self.settings.get("whatsapp", {}).get("webjs_endpoint", "http://127.0.0.1:8787"))
        self.webjs_token = self._field(root, "Bridge bearer token (encrypted Android Keystore)", "", password=True)

        self.status = Label(text=self._initial_status(), color=GRAY, size_hint_y=None, height="76dp", halign="left", valign="middle")
        root.add_widget(self.status)
        save_button = Button(text="Save WhatsApp Settings", size_hint_y=None, height="48dp", background_normal="", background_color=BLUE)
        save_button.bind(on_press=self.save_settings)
        root.add_widget(save_button)
        test_button = Button(text="Test Selected Connection", size_hint_y=None, height="48dp", background_normal="", background_color=BLUE)
        test_button.bind(on_press=self.test_connection)
        root.add_widget(test_button)
        clear_button = Button(text="Delete Stored Credentials", size_hint_y=None, height="44dp", background_normal="", background_color=(0.65, 0.12, 0.12, 1))
        clear_button.bind(on_press=self.clear_credentials)
        root.add_widget(clear_button)
        root.add_widget(Label(
            text="Credentials are encrypted with AES-256-GCM using a key held by Android Keystore. If secure storage is unavailable, saving credentials is blocked; no plaintext fallback is used.",
            color=GRAY, halign="left", valign="middle",
            size_hint_y=None, height="72dp"
        ))
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        scroll.add_widget(root)
        return scroll

    def check_accessibility_status(self, *_):
        """Report actual Android service/opt-in state; never grant it automatically."""
        try:
            from jnius import autoclass
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            component = autoclass("android.content.ComponentName")(
                activity, "com.emam.emo.GeminiAccessibilityService"
            )
            try:
                activity.getPackageManager().getServiceInfo(component, 0)
            except Exception:
                self.accessibility_status.text = (
                    "BLOCKED — native Gemini service is not registered in this installed APK."
                )
                return "NOT_PACKAGED"
            secure_settings = autoclass("android.provider.Settings$Secure")
            enabled = secure_settings.getString(
                activity.getContentResolver(),
                secure_settings.ENABLED_ACCESSIBILITY_SERVICES
            ) or ""
            accepted = {
                item.strip().lower()
                for item in enabled.split(":")
                if item.strip()
            }
            expected = {
                "com.emam.emo/com.emam.emo.geminiaccessibilityservice",
                "com.emam.emo/.geminiaccessibilityservice",
            }
            if accepted.intersection(expected):
                self.accessibility_status.text = (
                    "GRANTED — G-EMO Accessibility Service is enabled. Command flow is not yet end-to-end verified."
                )
                return "GRANTED"
            self.accessibility_status.text = (
                "ACTION REQUIRED — enable G-EMO manually in Android Accessibility Settings."
            )
            return "ACTION_REQUIRED"
        except Exception:
            self.accessibility_status.text = (
                "CHECK FAILED — Android permission state could not be read on this runtime."
            )
            return "CHECK_FAILED"

    def open_accessibility_settings(self, *_):
        """Open system settings only; the user must explicitly enable the service."""
        try:
            from jnius import autoclass
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            intent_class = autoclass("android.content.Intent")
            settings_class = autoclass("android.provider.Settings")
            activity.startActivity(
                intent_class(settings_class.ACTION_ACCESSIBILITY_SETTINGS)
            )
            return True
        except Exception:
            self.accessibility_status.text = (
                "UNAVAILABLE — could not open Android Accessibility Settings on this runtime."
            )
            return False

    def _initial_status(self):
        if self._secure_storage_error:
            return "SECURE STORAGE UNAVAILABLE — credentials cannot be saved. No plaintext fallback is permitted."
        return "Ready — human mode is the safe default. Secret fields are blank by design."

    def _initialize_secure_storage(self):
        try:
            self.secret_store = AndroidKeystoreTokenStore()
        except SecureStorageError as exc:
            self._secure_storage_error = str(exc)
            self.secret_store = None
        # One-time migration: attempt to encrypt legacy plaintext tokens, then always
        # remove them from settings JSON. If encryption fails, discard the exposed copy.
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            whatsapp = data.get("whatsapp", {}) if isinstance(data, dict) else {}
            if isinstance(whatsapp, dict):
                legacy = {
                    "access_token": "whatsapp_access_token",
                    "webjs_token": "whatsapp_webjs_token",
                }
                for old_key, secret_name in legacy.items():
                    secret = whatsapp.get(old_key)
                    if secret:
                        if self.secret_store is not None:
                            try:
                                self.secret_store.set(secret_name, str(secret))
                            except SecureStorageError:
                                self._secure_storage_error = "Legacy credential could not be encrypted and was removed; re-enter it after secure storage is available."
                        else:
                            self._secure_storage_error = "Legacy plaintext credential was removed because Android Keystore is unavailable."
                    whatsapp.pop(old_key, None)
                data["whatsapp"] = whatsapp
                self._write_settings(data)
        except (OSError, json.JSONDecodeError, TypeError):
            # Do not attempt to recover credentials from malformed settings.
            pass

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

    def _write_settings(self, settings):
        temp_path = self.settings_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(temp_path, 0o600)
        temp_path.replace(self.settings_path)

    def save_settings(self, *_):
        if (self.access_token.text.strip() or self.webjs_token.text.strip()) and self.secret_store is None:
            self.status.text = "BLOCKED — Android Keystore is unavailable. Credentials were not saved anywhere."
            return False
        try:
            if self.secret_store is not None:
                if self.access_token.text.strip():
                    self.secret_store.set("whatsapp_access_token", self.access_token.text.strip())
                if self.webjs_token.text.strip():
                    self.secret_store.set("whatsapp_webjs_token", self.webjs_token.text.strip())
        except SecureStorageError:
            self.status.text = "BLOCKED — encryption/storage failed. No plaintext credential was written."
            return False

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
            "api_version": whatsapp.get("api_version") or "v22.0",
            "webjs_endpoint": self.webjs_endpoint.text.strip(),
            "monitor": False,
        })
        # Defensive cleanup in case an older version left plaintext fields behind.
        whatsapp.pop("access_token", None)
        whatsapp.pop("webjs_token", None)
        settings["whatsapp"] = whatsapp
        try:
            self._write_settings(settings)
        except OSError:
            self.status.text = "SAVE FAILED — settings could not be written."
            return False
        self.status.text = "Saved non-secret settings. Credentials, if supplied, were stored only in Android Keystore-backed encrypted storage."
        return settings

    def clear_credentials(self, *_):
        if self.secret_store is None:
            self.status.text = "Secure storage unavailable; cannot verify credential deletion."
            return False
        try:
            self.secret_store.delete("whatsapp_access_token")
            self.secret_store.delete("whatsapp_webjs_token")
            self.access_token.text = ""
            self.webjs_token.text = ""
            self.status.text = "Stored WhatsApp credentials deleted."
            return True
        except SecureStorageError:
            self.status.text = "Credential deletion failed. Do not assume stored credentials were removed."
            return False

    def test_connection(self, *_):
        settings = self.save_settings()
        if not settings:
            return
        if settings["whatsapp"].get("transport") == "human":
            self.status.text = "HUMAN MODE selected. No connection required and no message was sent."
            return
        self.status.text = "Testing selected connection… no message will be sent."

        def run_test():
            result = WhatsAppPlugin(self.settings_path, secret_store=self.secret_store).test_connection()
            Clock.schedule_once(lambda _dt: self._show_test_result(result), 0)

        threading.Thread(target=run_test, daemon=True).start()

    def _show_test_result(self, result):
        status = result.get("status", "CONNECTION_FAILED")
        if status == "CONNECTED":
            phone = result.get("display_phone_number") or result.get("phone_number_id") or ""
            self.status.text = f"CONNECTED — {phone}. Connection verified; no message was sent."
        elif status == "HUMAN_FALLBACK":
            self.status.text = "HUMAN MODE — setup incomplete or manual transport selected. Use WhatsApp manually."
        else:
            self.status.text = f"CONNECTION FAILED — {result.get('http_status', '')} {result.get('detail', '')}"


if __name__ == "__main__":
    EmoSetupApp().run()
