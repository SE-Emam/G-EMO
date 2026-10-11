import unittest

from core.skills import SkillRegistry, SkillSpec


class SkillRegistryTests(unittest.TestCase):
    def setUp(self):
        self.audit = []
        self.registry = SkillRegistry(self.audit.append)
        self.calls = []
        self.registry.register(
            SkillSpec(
                skill_id="device.open_app",
                version="1.0.0",
                description="Open an explicitly named installed app",
                input_schema={
                    "type": "object",
                    "properties": {"package_name": {"type": "string", "maxLength": 200}},
                    "required": ["package_name"],
                    "additionalProperties": False,
                },
                required_permissions=("device_app_launch",),
                side_effect="external",
                requires_approval=True,
            ),
            lambda data: self.calls.append(data) or {"opened": data["package_name"]},
        )

    def test_unknown_skill_is_rejected(self):
        result = self.registry.execute("device.run_shell", {}, permission_states={})
        self.assertEqual((result.status, result.reason), ("REJECTED", "UNKNOWN_SKILL"))
        self.assertEqual(self.calls, [])

    def test_missing_permission_blocks_before_handler(self):
        result = self.registry.execute(
            "device.open_app", {"package_name": "com.example.app"},
            permission_states={"device_app_launch": "NOT_GRANTED"}, approved=True,
        )
        self.assertEqual(result.status, "ACTION_REQUIRED")
        self.assertIn("PERMISSION_NOT_GRANTED", result.reason)
        self.assertEqual(self.calls, [])

    def test_permission_state_missing_or_unknown_fails_closed(self):
        for states in ({}, {"device_app_launch": "SOMETHING"}):
            with self.subTest(states=states):
                result = self.registry.execute(
                    "device.open_app", {"package_name": "com.example.app"},
                    permission_states=states, approved=True,
                )
                self.assertEqual(result.status, "ACTION_REQUIRED")
                self.assertEqual(self.calls, [])

    def test_external_action_requires_approval(self):
        result = self.registry.execute(
            "device.open_app", {"package_name": "com.example.app"},
            permission_states={"device_app_launch": "GRANTED"},
        )
        self.assertEqual(result.status, "NEEDS_APPROVAL")
        self.assertEqual(self.calls, [])

    def test_approved_action_runs(self):
        result = self.registry.execute(
            "device.open_app", {"package_name": "com.example.app"},
            permission_states={"device_app_launch": "GRANTED"}, approved=True,
        )
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(result.result, {"opened": "com.example.app"})
        self.assertEqual(len(self.calls), 1)

    def test_missing_required_input_rejected(self):
        result = self.registry.execute(
            "device.open_app", {}, permission_states={"device_app_launch": "GRANTED"}, approved=True,
        )
        self.assertEqual(result.reason, "MISSING_REQUIRED_INPUT")
        self.assertEqual(self.calls, [])

    def test_undeclared_input_rejected(self):
        result = self.registry.execute(
            "device.open_app", {"package_name": "com.example.app", "shell": "rm -rf /"},
            permission_states={"device_app_launch": "GRANTED"}, approved=True,
        )
        self.assertEqual(result.reason, "UNDECLARED_INPUT_FIELD")
        self.assertEqual(self.calls, [])

    def test_wrong_type_and_overlong_input_rejected(self):
        cases = [
            ({"package_name": 123}, "INVALID_INPUT_TYPE"),
            ({"package_name": "x" * 201}, "INPUT_TOO_LONG"),
        ]
        for data, reason in cases:
            with self.subTest(reason=reason):
                result = self.registry.execute(
                    "device.open_app", data,
                    permission_states={"device_app_launch": "GRANTED"}, approved=True,
                )
                self.assertEqual(result.reason, reason)
        self.assertEqual(self.calls, [])

    def test_duplicate_skill_registration_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.register(self.registry._skills["device.open_app"].spec, lambda data: data)

    def test_audit_does_not_record_sensitive_values_or_handler_result(self):
        self.registry.execute(
            "device.open_app", {"package_name": "com.example.app"},
            permission_states={"device_app_launch": "NOT_GRANTED"},
        )
        self.assertEqual(len(self.audit), 1)
        serialized = repr(self.audit[0])
        self.assertNotIn("com.example.app", serialized)
        self.assertNotIn("opened", serialized)
        self.assertEqual(self.audit[0]["status"], "ACTION_REQUIRED")

    def test_handler_error_does_not_leak_exception(self):
        broken = SkillRegistry()
        def fail(_):
            raise RuntimeError("sensitive internal detail")
        broken.register(
            SkillSpec("test.broken", "1", "failure test",
                      {"type": "object", "properties": {}, "required": [], "additionalProperties": False}),
            fail,
        )
        result = broken.execute("test.broken", {}, permission_states={})
        self.assertEqual((result.status, result.reason), ("FAILED", "HANDLER_ERROR"))
        self.assertNotIn("sensitive internal detail", repr(result.to_dict()))

    def test_describe_excludes_handler_and_secrets(self):
        result = self.registry.describe()
        self.assertEqual(result[0]["skill_id"], "device.open_app")
        self.assertNotIn("handler", repr(result))
        self.assertNotIn("com.example.app", repr(result))


if __name__ == "__main__":
    unittest.main()
