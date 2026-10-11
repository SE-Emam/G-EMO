import unittest
from core.brain import ParseError, parse_command

class BrainTests(unittest.TestCase):
    def test_whatsapp_arabic(self):
        result = parse_command("يا EMO ابعت واتساب لأحمد: أنا في الطريق")
        self.assertEqual(result["action"], "send_whatsapp")
        self.assertEqual(result["to"], "أحمد")
        self.assertEqual(result["text"], "أنا في الطريق")
        self.assertTrue(result["requires_confirmation"])

    def test_facebook_post(self):
        result = parse_command("يا EMO انشر على فيسبوك: إعلان جديد")
        self.assertEqual(result["action"], "post_facebook")
        self.assertEqual(result["text"], "إعلان جديد")

    def test_missing_prefix_rejected(self):
        with self.assertRaises(ParseError):
            parse_command("ابعت واتساب لأحمد: أهلا")

    def test_ambiguous_command_rejected(self):
        with self.assertRaises(ParseError):
            parse_command("يا EMO ابعت واتساب لأحمد")

if __name__ == "__main__":
    unittest.main()
