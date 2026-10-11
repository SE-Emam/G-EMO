import unittest

from core.approval_broker import ApprovalBroker


class FakeClock:
    def __init__(self, value=1_800_000_000_000):
        self.value = value
    def __call__(self):
        return self.value


class FakeExecutor:
    def __init__(self):
        self.calls = []
    def execute(self, command, *, confirmed=False):
        self.calls.append((command, confirmed))
        return {"status": "HUMAN_ACTION_REQUIRED"}


class ApprovalBrokerTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.broker = ApprovalBroker(ttl_ms=1000, clock_ms=self.clock)
        self.executor = FakeExecutor()

    def test_pending_listing_does_not_expose_command_payload(self):
        pending = self.broker.stage("req-1", {"action": "send_whatsapp", "text": "private message"})
        listed = self.broker.list_pending()
        self.assertEqual(listed[0]["approval_id"], pending.approval_id)
        self.assertNotIn("private message", repr(listed))

    def test_approval_is_one_time_and_exact_pending_command(self):
        pending = self.broker.stage("req-2", {"action": "send_whatsapp", "text": "hello"})
        result = self.broker.approve(pending.approval_id, self.executor)
        self.assertEqual(result["status"], "HUMAN_ACTION_REQUIRED")
        self.assertEqual(self.executor.calls[0][0]["text"], "hello")
        self.assertTrue(self.executor.calls[0][1])
        replay = self.broker.approve(pending.approval_id, self.executor)
        self.assertEqual(replay["status"], "REJECTED")
        self.assertEqual(len(self.executor.calls), 1)

    def test_expired_approval_is_not_executed(self):
        pending = self.broker.stage("req-3", {"action": "send_whatsapp"})
        self.clock.value += 1000
        result = self.broker.approve(pending.approval_id, self.executor)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.executor.calls, [])

    def test_rejected_approval_cannot_be_replayed(self):
        pending = self.broker.stage("req-4", {"action": "post_facebook"})
        self.assertTrue(self.broker.reject(pending.approval_id))
        self.assertFalse(self.broker.reject(pending.approval_id))
        self.assertEqual(self.executor.calls, [])

    def test_invalid_command_cannot_be_staged(self):
        with self.assertRaises(ValueError):
            self.broker.stage("req-5", {"text": "missing action"})

    def test_invalid_ttl_is_rejected(self):
        with self.assertRaises(ValueError):
            ApprovalBroker(ttl_ms=0)


if __name__ == "__main__":
    unittest.main()
