import unittest

from core.brain import parse_command


class ParseCommandTests(unittest.TestCase):
    def test_whatsapp_english(self):
        result = parse_command("please use WhatsApp")
        self.assertEqual(result["plugin"], "whatsapp")
        self.assertEqual(result["action"], "send")

    def test_facebook_english(self):
        result = parse_command("open Facebook")
        self.assertEqual(result["plugin"], "facebook")
        self.assertEqual(result["action"], "monitor_or_post")

    def test_canva_arabic(self):
        result = parse_command("افتح كانفا")
        self.assertEqual(result["plugin"], "canva")
        self.assertEqual(result["action"], "create")

    def test_telegram_arabic(self):
        result = parse_command("استخدم تليجرام")
        self.assertEqual(result["plugin"], "telegram")
        self.assertEqual(result["action"], "send")

    def test_unknown_command(self):
        result = parse_command("what is the weather")
        self.assertEqual(result["plugin"], "none")
        self.assertEqual(result["raw"], "what is the weather")


if __name__ == "__main__":
    unittest.main()
