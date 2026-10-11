# G-EMO WhatsApp setup

## Transport selection

In the app's WhatsApp settings select one transport:

- **Human (default):** no credentials, no automatic send. The app tells the user to finish in WhatsApp.
- **Official Cloud API:** set the Meta `phone_number_id` and access token, then press **Test Connection**. Test Connection performs a GET for the phone-number metadata and does not send a message. Send requests require the app's confirmation gate. A missing token or phone ID automatically returns to human mode; a configured but rejected API request is reported as a real failure, not silently disguised as human success.
- **WhatsApp Web bridge (unofficial):** run the separate Node.js bridge below. It prints a QR code in the terminal for pairing. This is not embedded in the Android APK, and is not a guarantee of permanent background operation.

## Official Cloud API

Use a legitimate Meta WhatsApp Business Cloud API setup. Configure credentials in the app's private runtime settings; never commit a real token to Git. The current Python adapter also accepts `G_EMO_WHATSAPP_ACCESS_TOKEN` from the environment. The Cloud API requires a recipient phone number in international E.164 format (digits are sent without the leading plus). A display name alone is not enough to identify a Cloud API recipient.

## Optional whatsapp-web.js bridge

Requirements: a supported Node.js runtime and the Chromium/Puppeteer dependencies required by whatsapp-web.js. On Android/Termux, install and test those dependencies on the actual device; compatibility and persistent background operation are not guaranteed.

1. Copy this folder to a machine/device where Node.js and Puppeteer can run.
2. Run `npm install`.
3. Generate a private random secret (at least 24 characters) and export it as `G_EMO_WHATSAPP_WEBJS_TOKEN`.
4. Run `npm start`; scan the displayed QR from WhatsApp > Linked devices.
5. Keep the bridge bound to `127.0.0.1` unless you fully understand the exposure. Do not port-forward it or expose it publicly. The endpoint token is a bearer credential.

Example configuration for a same-device bridge:
- `transport`: `webjs`
- `webjs_endpoint`: `http://127.0.0.1:8787`
- `webjs_token`: same secret as the bridge environment variable

If the bridge is absent, not paired, or not configured, G-EMO returns to human mode where appropriate. If an attempted send fails after connection, it reports `SEND_FAILED` rather than claiming success.

## Security notes

`whatsapp-web.js` is an unofficial automation layer, not the official WhatsApp Business API. Linked-device sessions are sensitive. Use a dedicated environment where possible, keep the session directory private, and understand account/terms risk. Do not log message content. Successful HTTP 200 means the bridge/provider accepted the send operation; it is not a read receipt.
