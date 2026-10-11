import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.executor import Executor
from plugins.whatsapp_plugin import WhatsAppPlugin


class WhatsAppPluginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "settings.json"

    def tearDown(self):
        self.tmp.cleanup()
        patch.stopall()

    def configure(self, config):
        self.path.write_text(json.dumps({"whatsapp": config}), encoding="utf-8")
        return WhatsAppPlugin(self.path)

    def test_missing_token_falls_back_to_human(self):
        plugin = self.configure({"enabled": True, "transport": "cloud_api", "phone_number_id": "123", "access_token": ""})
        result = plugin.execute({"to": "أحمد", "text": "أهلا"}, confirmed=True)
        self.assertEqual(result["status"], "HUMAN_ACTION_REQUIRED")
        self.assertEqual(result["mode"], "human")

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
        with patch("plugins.whatsapp_plugin.urllib.request.urlopen", side_effect=urllib.error.HTTPError("https://example.invalid", 401, "Unauthorized", {}, None)):
            result = plugin.execute({"phone": "201000000000", "text": "Hello"}, confirmed=True)
        self.assertEqual(result["status"], "SEND_FAILED")
        self.assertEqual(result["http_status"], 401)

    def test_executor_confirmation_gate_remains_in_front_of_plugin(self):
        self.path.write_text(json.dumps({"whatsapp": {"enabled": True, "mode": "human", "transport": "human"}}), encoding="utf-8")
        executor = Executor(self.path, {"whatsapp": WhatsAppPlugin(self.path)})
        command = {"action": "send_whatsapp", "to": "أحمد", "text": "أهلا", "requires_confirmation": True}
        self.assertEqual(executor.execute(command)["status"], "CONFIRMATION_REQUIRED")
        self.assertEqual(executor.execute(command, confirmed=True)["status"], "HUMAN_ACTION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
