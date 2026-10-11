import json
import os
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.executor import Executor
from plugins.whatsapp_plugin import WhatsAppPlugin
from core.secure_storage import SecureStorageError


class TestSettingsSecretStore:
    """Test-only adapter: fixtures emulate secure secret lookup without Android."""
    def __init__(self, path):
        self.path = Path(path)
        self.values = {}

    def get(self, name):
        if name in self.values:
            return self.values[name]
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            whatsapp = data.get("whatsapp", {})
            key = {"whatsapp_access_token": "access_token", "whatsapp_webjs_token": "webjs_token"}[name]
            return whatsapp.get(key, "")
        except (OSError, json.JSONDecodeError, KeyError):
            return ""

    def set(self, name, value):
        self.values[name] = value

    def delete(self, name):
        self.values.pop(name, None)


class WhatsAppPluginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "settings.json"

    def tearDown(self):
        self.tmp.cleanup()
        patch.stopall()

    def configure(self, config):
        self.path.write_text(json.dumps({"whatsapp": config}), encoding="utf-8")
        return WhatsAppPlugin(self.path, secret_store=TestSettingsSecretStore(self.path))

    def test_missing_token_falls_back_to_human(self):
        plugin = self.configure({"enabled": True, "transport": "cloud_api", "phone_number_id": "123", "access_token": ""})
        result = plugin.execute({"to": "أحمد", "text": "أهلا"}, confirmed=True)
        self.assertEqual(result["status"], "HUMAN_ACTION_REQUIRED")
        self.assertEqual(result["mode"], "human")

    def test_test_connection_missing_credentials_falls_back_without_network(self):
        plugin = self.configure({"transport": "cloud_api", "phone_number_id": "", "access_token": ""})
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen") as mocked:
            result = plugin.test_connection()
        self.assertEqual(result["status"], "HUMAN_FALLBACK")
        mocked.assert_not_called()

    def test_test_connection_http_200_reports_connected(self):
        plugin = self.configure({"transport": "cloud_api", "phone_number_id": "123", "access_token": "test-token"})
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"id":"123","display_phone_number":"+201000000000"}'
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen", return_value=Response()):
            result = plugin.test_connection()
        self.assertEqual(result["status"], "CONNECTED")
        self.assertEqual(result["display_phone_number"], "+201000000000")

    def test_webjs_connection_check_reports_connected(self):
        plugin = self.configure({"transport": "webjs", "webjs_endpoint": "http://127.0.0.1:8787", "webjs_token": "bridge-test-token"})
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"status":"CONNECTED"}'
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen", return_value=Response()):
            result = plugin.test_connection()
        self.assertEqual(result["status"], "CONNECTED")
        self.assertEqual(result["transport"], "webjs")

    def test_webjs_without_bridge_falls_back_to_human(self):
        plugin = self.configure({"transport": "webjs", "webjs_endpoint": "", "webjs_token": ""})
        result = plugin.execute({"to_phone": "201000000000", "text": "Hello"}, confirmed=True)
        self.assertEqual(result["status"], "HUMAN_ACTION_REQUIRED")

    def test_human_transport_never_claims_sent(self):
        plugin = self.configure({"transport": "human"})
        self.assertEqual(plugin.execute({"text": "hello"}, confirmed=True)["status"], "HUMAN_ACTION_REQUIRED")

    def test_cloud_api_missing_phone_id_falls_back(self):
        plugin = self.configure({"transport": "cloud_api", "access_token": "test-token"})
        self.assertEqual(plugin.execute({"text": "hello"}, confirmed=True)["status"], "HUMAN_ACTION_REQUIRED")

    def test_cloud_api_posts_and_checks_http_200(self):
        plugin = self.configure({"transport": "cloud_api", "phone_number_id": "123", "access_token": "test-token", "api_version": "v22.0"})
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"messages":[{"id":"wamid.test"}]}'
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen", return_value=Response()) as mocked:
            result = plugin.execute({"phone": "201000000000", "text": "Hello"}, confirmed=True)
        self.assertEqual(result["status"], "SENT")
        self.assertEqual(result["http_status"], 200)
        mocked.assert_called_once()

    def test_api_http_error_is_not_misreported_as_human_fallback(self):
        plugin = self.configure({"transport": "cloud_api", "phone_number_id": "123", "access_token": "test-token"})
        import urllib.error
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen", side_effect=urllib.error.HTTPError("https://example.invalid", 401, "Unauthorized", {}, io.BytesIO(b"{}"))):
            result = plugin.execute({"phone": "201000000000", "text": "Hello"}, confirmed=True)
        self.assertEqual(result["status"], "SEND_FAILED")
        self.assertEqual(result["http_status"], 401)

    def test_executor_confirmation_gate_remains_in_front_of_plugin(self):
        self.path.write_text(json.dumps({"whatsapp": {"enabled": True, "mode": "human", "transport": "human"}}), encoding="utf-8")
        executor = Executor(self.path, {"whatsapp": WhatsAppPlugin(self.path)})
        command = {"action": "send_whatsapp", "to": "أحمد", "text": "أهلا", "requires_confirmation": True}
        self.assertEqual(executor.execute(command)["status"], "CONFIRMATION_REQUIRED")
        self.assertEqual(executor.execute(command, confirmed=True)["status"], "HUMAN_ACTION_REQUIRED")

    def test_webjs_rejects_plain_http_remote_endpoint_without_network(self):
        plugin = self.configure({"transport": "webjs", "webjs_endpoint": "http://192.0.2.10:8787", "webjs_token": "bridge-test-token"})
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen") as mocked:
            result = plugin.test_connection()
        self.assertEqual(result["status"], "HUMAN_FALLBACK")
        mocked.assert_not_called()

    def test_webjs_rejects_url_with_embedded_credentials(self):
        plugin = self.configure({"transport": "webjs", "webjs_endpoint": "http://user:pass@127.0.0.1:8787", "webjs_token": "bridge-test-token"})
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen") as mocked:
            result = plugin.test_connection()
        self.assertEqual(result["status"], "HUMAN_FALLBACK")
        mocked.assert_not_called()

    def test_cloud_api_rejects_invalid_recipient_without_network(self):
        plugin = self.configure({"transport": "cloud_api", "phone_number_id": "123", "access_token": "test-token"})
        for recipient in ("abc", "+201234", "201234567890123456", "2012 34567890"):
            with self.subTest(recipient=recipient):
                with patch("plugins.whatsapp_plugin.urllib.request.urlopen") as mocked:
                    result = plugin.execute({"phone": recipient, "text": "Hello"}, confirmed=True)
                self.assertEqual(result["status"], "INVALID_REQUEST")
                mocked.assert_not_called()

    def test_cloud_api_rejects_oversized_message_without_network(self):
        plugin = self.configure({"transport": "cloud_api", "phone_number_id": "123", "access_token": "test-token"})
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen") as mocked:
            result = plugin.execute({"phone": "201000000000", "text": "x" * 4097}, confirmed=True)
        self.assertEqual(result["status"], "INVALID_REQUEST")
        mocked.assert_not_called()

    def test_cloud_api_rejects_invalid_api_version_without_network(self):
        plugin = self.configure({"transport": "cloud_api", "phone_number_id": "123", "access_token": "test-token", "api_version": "v22.0/../../evil"})
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen") as mocked:
            result = plugin.execute({"phone": "201000000000", "text": "Hello"}, confirmed=True)
        self.assertEqual(result["status"], "INVALID_REQUEST")
        mocked.assert_not_called()

    def test_cloud_api_does_not_expose_provider_error_body(self):
        plugin = self.configure({"transport": "cloud_api", "phone_number_id": "123", "access_token": "test-token"})
        import urllib.error
        secret_detail = b'{"error":{"message":"sensitive provider detail"}}'
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen", side_effect=urllib.error.HTTPError("https://graph.facebook.com", 401, "Unauthorized", {}, io.BytesIO(secret_detail))):
            result = plugin.execute({"phone": "201000000000", "text": "Hello"}, confirmed=True)
        self.assertEqual(result["status"], "SEND_FAILED")
        self.assertNotIn("sensitive provider detail", str(result))

    def test_plugin_never_reads_plaintext_tokens_from_settings_without_secure_store(self):
        self.configure({"transport": "cloud_api", "phone_number_id": "123", "access_token": "must-not-be-used"})
        plugin = WhatsAppPlugin(self.path)
        with patch("plugins.whatsapp_plugin.AndroidKeystoreTokenStore", side_effect=SecureStorageError("keystore unavailable")), patch.dict(os.environ, {"G_EMO_WHATSAPP_ACCESS_TOKEN": ""}):
            result = plugin.execute({"phone": "201000000000", "text": "Hello"}, confirmed=True)
        self.assertEqual(result["status"], "HUMAN_ACTION_REQUIRED")

    def test_test_secret_store_adapter_is_explicitly_injected(self):
        adapter = TestSettingsSecretStore(self.path)
        self.path.write_text(json.dumps({"whatsapp": {"access_token": "test-only-secret"}}), encoding="utf-8")
        self.assertEqual(adapter.get("whatsapp_access_token"), "test-only-secret")
        # This is a test-only fixture; production plugin defaults never read secrets from JSON.


if __name__ == "__main__":
    unittest.main()
