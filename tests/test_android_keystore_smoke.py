import json
import tempfile
import unittest
from pathlib import Path

from core.android_keystore_smoke import (
    MARKER_NAME,
    REPORT_NAME,
    ROUNDTRIP_NAME,
    MIGRATION_NAME,
    LEGACY_ACCESS_VALUE,
    LEGACY_WEBJS_VALUE,
    run_requested_self_test,
)


class MemoryStore:
    def __init__(self):
        self.values = {}

    def set(self, name, value):
        self.values[name] = value

    def get(self, name):
        return self.values.get(name, "")

    def delete(self, name):
        self.values.pop(name, None)


class AndroidKeystoreSmokeFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.settings_path = self.root / "settings.json"
        self.settings_path.write_text(json.dumps({"whatsapp": {"transport": "human"}}), encoding="utf-8")
        self.marker = self.root / MARKER_NAME
        self.marker.touch()
        self.store = MemoryStore()

    def tearDown(self):
        self.temp.cleanup()

    def write_settings(self, value):
        self.settings_path.write_text(json.dumps(value), encoding="utf-8")

    def test_full_phase_flow_checks_restart_delete_and_migration(self):
        run_requested_self_test(self.settings_path, self.store, self.write_settings)
        first = json.loads((self.root / REPORT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(first["phase"], "roundtrip_written")
        self.assertIn(ROUNDTRIP_NAME, self.store.values)

        run_requested_self_test(self.settings_path, self.store, self.write_settings)
        second = json.loads((self.root / REPORT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(second["phase"], "migration_prepared")
        settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
        self.assertEqual(settings["whatsapp"]["access_token"], LEGACY_ACCESS_VALUE)
        self.assertEqual(settings["whatsapp"]["webjs_token"], LEGACY_WEBJS_VALUE)

        # Emulate the app's startup migration, which runs before the next self-test phase.
        for field, secret_name in (("access_token", ROUNDTRIP_NAME), ("webjs_token", MIGRATION_NAME)):
            self.store.set(secret_name, settings["whatsapp"].pop(field))
        self.write_settings(settings)

        run_requested_self_test(self.settings_path, self.store, self.write_settings)
        final = json.loads((self.root / REPORT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(final["status"], "PASS")
        self.assertIn("restart_persistence", final["checks"])
        self.assertIn("legacy_plaintext_fields_removed", final["checks"])
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.store.get(ROUNDTRIP_NAME), "")
        self.assertEqual(self.store.get(MIGRATION_NAME), "")
        self.assertNotIn("access_token", json.loads(self.settings_path.read_text())["whatsapp"])

    def test_missing_store_fails_closed_and_removes_marker(self):
        run_requested_self_test(self.settings_path, None, self.write_settings)
        report = json.loads((self.root / REPORT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
