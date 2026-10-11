# G-EMO Production-Readiness Audit

**Review target:** `EMO-FINAL-PRODUCTION.zip`  
**Review type:** static source review and Python syntax parsing  
**Overall result:** **BLOCKED — not production-ready**

## Scope and evidence

The archive contains 33 ZIP entries, including 13 Python files, duplicated source/config/spec files, icon assets, and no test suite. All 13 Python files parsed successfully with Python's AST parser. This does not prove imports, runtime behavior, Android packaging, or device integration.

## Findings

### P0 — Entry-point import can fail before service startup
**Evidence:** `service/background.py` reads `/sdcard/Download/agent_config.json` at module import time. The archive instead supplies `config/settings.json`; the hard-coded file is not guaranteed to exist. Importing `app.py` imports `service.background`, so startup can terminate immediately.

**Required fix:** one validated configuration loader, a documented schema, explicit errors, and no I/O side effects during module import.

### P0 — Android runtime architecture is inconsistent
**Evidence:** `core/watcher.py` imports `uiautomator2` and calls `u2.connect()`; `buildozer.spec` attempts to package the project as an Android app with `uiautomator2` as an in-app requirement. No Android AccessibilityService implementation is present. The normal `uiautomator2` model uses an external Python controller plus ADB/device-side support, not a self-contained Android accessibility service.

**Impact:** the claimed on-device/headless app cannot be considered buildable or operational from the supplied files.

**Required fix:** choose and implement one architecture end-to-end: (1) external controller with explicit ADB/device setup, or (2) native Android app with a real AccessibilityService, lifecycle handling, user-granted settings, and a narrow bridge to the business layer. Do not mix the two runtime models.

### P1 — The watcher does not prove text came from Gemini
**Evidence:** `core/watcher.py` polls generic `android.widget.EditText` elements and treats changed text as a command. It does not verify the foreground package or distinguish user input from model output.

**Impact:** unrelated text fields can trigger actions, while Gemini responses may never be detected.

**Required fix:** app/package-aware event handling and an explicit, testable command boundary. Require confirmation before external side effects.

### P1 — Plugin execution is mostly stub behavior
**Evidence:**
- `plugins/whatsapp_plugin.py`: human mode opens WhatsApp and attempts to click an element named `بحث`; it does not select a recipient or send a message. The API branch only returns a placeholder string.
- `plugins/facebook_plugin.py`: the API branch returns a string without making an HTTP request; the configured page token is not used to perform a request.
- `plugins/canva_plugin.py`: opens an app and returns a status string; it does not create a design.
- `core/executor.py`: imports WhatsApp, Facebook, and Canva handlers; Telegram is parsed but not dispatched.

**Required fix:** define capability contracts, validate prerequisites, implement real calls where intended, return structured results, and test success/failure paths. Never report an action as complete when only an app was opened.

### P1 — Configuration paths conflict
**Evidence:** `main.py` looks for `/sdcard/Download/emo_config.json` then falls back to `config/settings.json`; `service/background.py` instead requires `/sdcard/Download/agent_config.json` with no fallback. WhatsApp and Facebook are enabled by default despite incomplete integrations.

**Required fix:** a single configuration source and loader; disable incomplete integrations by default; validate fields and permissions before enabling a plugin.

### P1 — Broad exception suppression hides failures
**Evidence:** `core/watcher.py` catches every exception and silently continues with `except: pass`.

**Impact:** connection failures and permission errors can be invisible.

**Required fix:** catch expected exceptions, emit redacted structured logs, expose health state, and use bounded retries/backoff.

### P1 — Unsafe shell command construction
**Evidence:** `plugins/facebook_plugin.py` interpolates notification title/content into a `termux-notification` command via `os.system()`.

**Impact:** quotes or shell metacharacters in text can alter the command.

**Required fix:** use `subprocess.run([...], shell=False)`, validate inputs, and never pass untrusted content through a shell.

### P2 — Duplicate files create ambiguity
**Evidence:** duplicate pairs include `README.md`/`README_1.md`, `app.py`/`app_1.py`, `buildozer.spec`/`buildozer_1.spec`, `config/settings.json`/`config/settings_1.json`, and duplicated `core/*_1.py` files.

**Required fix:** remove duplicates after confirming equivalence and keep one canonical path per module/config/spec.

### P2 — Android manifest/build configuration is insufficient
**Evidence:** `buildozer.spec` lists `BIND_ACCESSIBILITY_SERVICE` as a permission, but no accessibility service implementation/manifest metadata exists. Listing a permission does not implement or activate an AccessibilityService.

**Required fix:** implement/register the service correctly if this architecture is selected, request user-granted access through system settings, and test on a real device. A successful package build alone would not prove automation works.

### P2 — No reproducible tests or dependency setup
**Evidence:** no test files, dependency manifest, CI workflow, or device-test evidence are included.

**Required fix:** add parser/config/dispatcher unit tests, mocked plugin tests, static checks, build checks, and a documented device acceptance suite.

## Remediation order

1. Decide: external ADB controller vs native Android AccessibilityService.
2. Unify configuration and remove import-time file reads.
3. Establish a trusted Gemini-originated command boundary.
4. Add structured execution results and approval gates for sending/publishing.
5. Implement and test integrations; keep unfinished plugins disabled.
6. Fix shell execution, logging, health reporting, and retry behavior.
7. Add automated tests and real-device acceptance evidence.

## Gate status

| Gate | Status | Evidence |
|---|---|---|
| Python syntax | PASS | 13/13 Python files parsed |
| Import/startup | BLOCKED | hard-coded external config read at import time |
| Android architecture | BLOCKED | controller model conflicts with packaged-app approach |
| Command provenance | BLOCKED | generic EditText polling without package/output validation |
| Plugin completeness | BLOCKED | integrations contain placeholders/stubs |
| Configuration consistency | FAIL | two different hard-coded config filenames |
| Security hardening | FAIL | silent exception handling and shell interpolation |
| Automated tests | BLOCKED | no tests supplied |
| Real-device test | NOT RUN | no device evidence supplied |
| Production readiness | **BLOCKED** | P0/P1 findings remain open |

## Non-claims

This audit does not claim the APK builds, the app can control Gemini, or any message/post/design action works. Those behaviors require implementation and runtime/device evidence.
