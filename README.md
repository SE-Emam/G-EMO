# G-EMO — Gemini-assisted Android automation prototype

> **Status: prototype / not production-ready.** Static review found integration and runtime blockers that must be resolved before safe installation or real-account use.

The uploaded archive is retained as `EMO-FINAL-PRODUCTION.zip`. It contains a small Python command parser, early UI-automation stubs for WhatsApp/Facebook/Canva, a polling loop using `uiautomator2`, and a Buildozer spec.

## Critical limitation

The runtime architecture is inconsistent: `uiautomator2` generally controls an Android device through an external Python process and ADB, while the Buildozer file attempts to package the same code as an on-device app. The archive contains no implemented Android AccessibilityService. Several plugin paths are placeholders and do not complete the actions they imply.

See [docs/PRODUCTION_AUDIT.md](docs/PRODUCTION_AUDIT.md) for evidence and remediation order.

## Safety

Do not use this prototype with real accounts or sensitive conversations until architecture, permissions, approval flow, and tests have been implemented and reviewed. Keep external side effects user-confirmed and never commit credentials.

## Validation status

- Python source syntax: **PASS** for all 13 Python files in the archive.
- Functional integration tests in submitted archive: **NONE**.
- Android build / device test: **NOT RUN**.
- Production readiness: **BLOCKED**.
