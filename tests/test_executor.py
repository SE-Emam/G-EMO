import json
import tempfile
import unittest
from pathlib import Path
from core.executor import Executor
from plugins.whatsapp_plugin import WhatsAppPlugin

class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "settings.json"
        self.path.write_text(json.dumps({"whatsapp": {"enabled": True, "mode": "human"}}), encoding="utf-8")
        self.executor = Executor(self.path, {"whatsapp": WhatsAppPlugin()})
        self.command = {"action": "send_whatsapp", "to": "أحمد", "text": "أهلا", "requires_confirmation": True}

    def tearDown(self):
        self.tmp.cleanup()

    def test_confirmation_required(self):
        self.assertEqual(self.executor.execute(self.command)["status"], "CONFIRMATION_REQUIRED")

    def test_human_mode_does_not_claim_success(self):
        self.assertEqual(self.executor.execute(self.command, confirmed=True)["status"], "HUMAN_ACTION_REQUIRED")

    def test_disabled_plugin_blocked(self):
        self.path.write_text(json.dumps({"whatsapp": {"enabled": False, "mode": "human"}}), encoding="utf-8")
        self.assertEqual(self.executor.execute(self.command, confirmed=True)["status"], "DISABLED")

if __name__ == "__main__":
    unittest.main()
