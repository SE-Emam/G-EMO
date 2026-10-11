# G-EMO Security Notes

## Credential protection implemented on this branch

- core/secure_storage.py uses Android Keystore to hold an AES-256-GCM encryption key; only the IV and ciphertext are stored in app-private SharedPreferences.
- Provider credentials are no longer read from or written to settings.json by the production WhatsApp adapter.
- The setup UI never pre-populates secret fields with saved credentials. It offers explicit credential deletion.
- The app attempts a one-time migration of legacy plaintext tokens to encrypted storage. It removes legacy token fields from settings JSON even if migration cannot encrypt them; in that failure case the old token is discarded and must be entered again after secure storage becomes available.
- If Android Keystore is unavailable, the UI blocks saving entered credentials. There is no plaintext-file fallback.
- Environment variables remain an explicit deployment override for controlled environments; they are not written to settings files.
- WhatsApp sends require explicit executor confirmation; human mode is the default.
- API versions, phone-number IDs, recipients, and message sizes are validated before requests.
- Provider error bodies are not returned to callers.
- The optional bridge requires bearer authentication, caps request bodies, defaults to loopback binding, and the Python client rejects plain HTTP for remote bridge URLs.

## Verification still required

1. **Android runtime verification is automated but must pass on the current PR head.** `.github/workflows/android-emulator.yml` builds x86_64 and device APKs, installs the x86_64 APK in an Android 35 emulator, and uses a private one-shot marker to run the actual Pyjnius/Android Keystore path across app launches. The runtime gate checks AES-GCM round-trip, restart persistence, deletion, legacy token migration, and runtime settings JSON. A workflow definition is not evidence of success: inspect its run and artifacts before closing this gate.
2. **Key lifecycle needs device tests.** Test create, encrypt/decrypt, update, delete, app restart, app-data restore behavior, and recovery when the Keystore key is invalidated or unavailable.
3. **Legacy migration must be exercised on Android.** Confirm plaintext access_token and webjs_token fields are removed after migration; when Keystore is unavailable, verify no secret remains in settings JSON.
4. **Native Android AccessibilityService is not implemented or device-tested.**
5. **APK signing, install, and real-device tests are not verified.**
6. **The unofficial whatsapp-web.js bridge is not security-equivalent to Meta Cloud API.** Its browser session is sensitive account access; keep it on loopback or behind authenticated HTTPS, never expose it directly to the public internet. Puppeteer/Termux compatibility has not been validated on-device.
7. **Live Meta credentials and message delivery have not been tested.** CI uses mocked provider responses.

## Release gates

- Require a passing `.github/workflows/android-emulator.yml` run on the final PR head; retain the Keystore self-test report, runtime settings inspection, and emulator logcat artifacts.
- Build/install the APK on a supported physical Android device and repeat the Keystore encrypt/decrypt/migration/deletion tests before production release.
- Inspect app-private settings JSON and verify it contains no provider token fields or token values.
- Run the full CI suite on the final PR head and inspect each job result.
- Test Meta connection with a dedicated test account; perform a controlled live delivery only with explicit operator consent.
- Keep the PR in draft until the Android verification gates pass.
