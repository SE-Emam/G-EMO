# WhatsApp integration choices

G-EMO offers three explicit transport settings under `config/settings.json`:

- `human` (default, no credentials): never claims a message was sent; asks the user to complete it in WhatsApp.
- `cloud_api`: official Meta WhatsApp Cloud API. Configure `phone_number_id` and `access_token`, then use the adapter's `test_connection()` check before enabling sends. A send is reported as `SENT` only after HTTP 200 from Graph API. Missing token automatically falls back to `human`; invalid/expired credentials or network errors return `SEND_FAILED` rather than hiding the real failure.
- `webjs`: optional local bridge configured by `webjs_endpoint` and `webjs_token`. This repository currently contains only the client contract, not the Node bridge or QR onboarding UI. It therefore falls back to human mode when the bridge is not configured.

## Security and platform caveats

- Never commit real tokens. Prefer environment variable `G_EMO_WHATSAPP_ACCESS_TOKEN` (and `G_EMO_WHATSAPP_WEBJS_TOKEN`) or Android secure storage in the production app. Empty placeholders in the tracked JSON are intentional.
- Sending requires the existing G-EMO confirmation gate. The recipient must be an E.164 phone number for Cloud API sends; a display name alone cannot identify a Cloud API recipient.
- `whatsapp-web.js` is an unofficial WhatsApp Web automation library, not the official Cloud API. QR pairing stores a linked session, may break when WhatsApp Web changes, and can carry account/terms risk. It is not bundled into the Android APK and should be treated as an optional separately operated bridge, not as a guaranteed always-on mobile service.
- A successful HTTP response only proves the provider accepted the request; it does not prove the recipient read the message.
