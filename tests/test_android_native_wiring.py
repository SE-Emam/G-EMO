import unittest
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class AndroidNativeWiringTests(unittest.TestCase):
    def test_buildozer_includes_java_source_resource_and_manifest_fragment(self):
        spec = (ROOT / "buildozer.spec").read_text(encoding="utf-8")
        self.assertIn("android.add_src = android/src", spec)
        self.assertIn("android.res_xml = android/res/xml/gemo_accessibility_service.xml", spec)
        self.assertIn("android.extra_manifest_application_arguments = android/extra_manifest_application_arguments.xml", spec)
        self.assertIn("p4a.commit = d2ee8c5", spec)

    def test_accessibility_metadata_is_narrow_and_does_not_enable_gestures(self):
        path = ROOT / "android/res/xml/gemo_accessibility_service.xml"
        root = ET.parse(path).getroot()
        self.assertEqual(root.tag, "accessibility-service")
        self.assertEqual(root.attrib[ANDROID_NS + "packageNames"], "com.google.android.apps.bard")
        self.assertEqual(root.attrib[ANDROID_NS + "canRetrieveWindowContent"], "false")
        self.assertEqual(root.attrib[ANDROID_NS + "canPerformGestures"], "false")
        self.assertIn("typeWindowContentChanged", root.attrib[ANDROID_NS + "accessibilityEventTypes"])

    def test_manifest_fragment_declares_system_bound_service(self):
        fragment = (ROOT / "android/extra_manifest_application_arguments.xml").read_text(encoding="utf-8")
        root = ET.fromstring("<application>" + fragment + "</application>")
        service = root.find("service")
        self.assertIsNotNone(service)
        self.assertEqual(service.attrib[ANDROID_NS + "name"], "com.emam.emo.GeminiAccessibilityService")
        self.assertEqual(service.attrib[ANDROID_NS + "permission"], "android.permission.BIND_ACCESSIBILITY_SERVICE")
        self.assertEqual(service.attrib[ANDROID_NS + "exported"], "true")
        metadata = service.find("meta-data")
        self.assertEqual(metadata.attrib[ANDROID_NS + "resource"], "@xml/gemo_accessibility_service")

    def test_java_service_uses_explicit_prefix_and_package_allowlist(self):
        source = (ROOT / "android/src/com/emam/emo/GeminiAccessibilityService.java").read_text(encoding="utf-8")
        self.assertIn('GEMINI_PACKAGE = "com.google.android.apps.bard"', source)
        self.assertIn('EMO\\\\s*', source)
        self.assertIn("event.isPassword()", source)
        self.assertIn("getFilesDir()", source)
        self.assertNotIn("dispatchGesture(", source)
        self.assertNotIn("getPrimaryClip(", source)


if __name__ == "__main__":
    unittest.main()
