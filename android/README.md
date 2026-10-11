# Native Android integration (required)

The Python core cannot register itself as an Android AccessibilityService. The production APK needs a native Android service declared in the manifest and an explicit user opt-in through Android Settings.

Required implementation gates:

1. Declare only the G-EMO AccessibilityService with `BIND_ACCESSIBILITY_SERVICE` and an accessibility-service metadata XML file.
2. Restrict accepted events to the verified Gemini package ID(s); do not collect text from unrelated apps.
3. Never capture passwords, authentication screens, clipboard contents, or arbitrary screen recordings.
4. Forward only bounded, relevant text to the command parser, with an explicit EMO prefix and visible opt-in state.
5. Use Android foreground-service rules where applicable; do not promise guaranteed 24/7 operation.
6. Require confirmation before messaging, publishing, email sending, or destructive operations.
7. Add instrumentation tests on supported Android versions and at least one physical device before calling the APK production-ready.

**Status:** specification documented; native service implementation and Python bridge are not yet complete. Buildozer alone does not create the required AccessibilityService.
