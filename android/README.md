# Native Android integration (partial; not release-ready)

The repository now contains an initial native service source and XML declarations:
- `src/com/emam/emo/GeminiAccessibilityService.java`
- `res/xml/gemo_accessibility_service.xml`
- `extra_manifest_application_arguments.xml`

**Important:** these files are not proven to be packaged in the APK yet. The current `buildozer.spec` must include the supported python-for-android Java source, resource XML, and application-manifest options, and the resulting merged manifest must be inspected in CI. Until that configuration and build proof exist, the installed APK must be treated as having no usable Gemini accessibility bridge.

## Security boundaries in the initial service source

- Explicit user opt-in through Android Accessibility Settings is required by the platform.
- Event source is restricted to the Google Gemini Android package ID `com.google.android.apps.bard`, which matches the current Google Play listing.
- The service inspects only bounded accessibility event text and persists only text explicitly addressed with `EMO:`; it does not intentionally save general screen contents.
- Password events and event class names that appear to be authentication/consent screens are rejected.
- No UI gestures, taps, arbitrary app automation, clipboard reads, or credentials are implemented by this service.
- Commands written to the private inbox remain untrusted and must pass the Python inbox validator and parser before any action is considered.
- The command queue is app-private and uses per-request files to avoid partial writes.

## Required completion gates

1. Wire native Java source and XML into the Buildozer/python-for-android build using documented configuration options.
2. Add an app UI that accurately reports whether the native service is packaged and enabled; it must never claim to grant permissions automatically.
3. Connect the inbox consumer to the command dispatcher and the skill registry, with per-action approval.
4. Add tests for merged-manifest declarations, service allow-list, command extraction, queue validation, permission-denial handling, and app lifecycle.
5. Build the APK in CI, inspect the merged manifest, install on emulator, and verify the service is visible in Android Accessibility Settings.
6. Perform a physical-device end-to-end test and retain redacted evidence.

## Status

- Native Java service source: **IMPLEMENTED, NOT BUILD-VERIFIED**.
- Service metadata and manifest fragment: **ADDED, NOT MERGED-MANIFEST-VERIFIED**.
- Buildozer packaging configuration: **BLOCKED / NOT UPDATED**.
- Python inbox validator: **IMPLEMENTED; CI verification pending**.
- Gemini-to-skill end-to-end execution: **NOT IMPLEMENTED / NOT VERIFIED**.

A successful Python unit-test run or APK build alone does not establish Android Accessibility integration or functional Gemini-to-agent execution.