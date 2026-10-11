# G-EMO Security Notes

## Current controls

- WhatsApp sends require an explicit executor confirmation.
- Human mode is the default; missing credentials do not trigger a network request.
- Cloud API versions and phone-number IDs are validated before URL construction.
- Recipients and message size are validated before a send request.
- Provider error bodies are not returned to the caller.
- The optional bridge requires a bearer token, caps request bodies, defaults to loopback binding, and rejects non-loopback binding unless explicitly overridden.
- The Python client permits plain HTTP bridge URLs only for loopback hosts; remote bridge endpoints must use HTTPS.
- Automated regression tests cover these controls.

## Production blockers — do not treat this branch as production-ready

1. **Android Keystore-backed secret storage is not implemented.** The current Kivy screen persists access tokens in app-private JSON. App-private storage is not equivalent to encryption at rest. Do not use a long-lived production token in this build.
2. **Native Android AccessibilityService is not implemented or device-tested.** No accessibility-driven action should be represented as verified.
3. **APK signing, install, and real-device tests are not verified.**
4. **The unofficial whatsapp-web.js bridge is not security-equivalent to Meta Cloud API.** Its browser session is sensitive account access; keep it on loopback or behind authenticated HTTPS, never expose it directly to the public internet. The Puppeteer/Termux runtime has not been validated on-device.
5. **Live Meta credentials and live message delivery have not been tested.** CI mocks network responses; it does not prove provider-side permissions or delivery.

## Required release gates

- Implement and test a native Android Keystore-backed token provider; never silently fall back to plaintext token persistence.
- Add Android instrumentation/device tests for secret persistence, app restart, logout/token clearing, accessibility permissions, and confirmation behavior.
- Run the complete CI suite on the final PR head and inspect the job logs.
- Test Meta connection using a dedicated test account and verify an actual controlled delivery only with explicit operator consent.
- Keep the PR in draft until each blocker has evidence attached.
