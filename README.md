# G-EMO

**G-EMO** is an Android automation companion that lets a user issue commands through the existing Gemini app and, with explicit Android Accessibility permission, route supported requests to locally installed app workflows.

- **Package ID:** `com.emam.emo`
- **Project name:** EMO
- **No paid model/API is required for command interpretation.** Gemini remains the user's existing app; G-EMO does not call a paid model endpoint.
- **No root required.**
- **No custom chat UI.**

> **Important technical limitation:** Android does not provide a universal, reliable, or guaranteed 24/7 way to read another app's private conversation. Accessibility events expose only UI content the target app makes accessible, and Android background-execution limits vary by OS/vendor. The app must detect uncertainty and fail closed rather than guess or silently execute.
>
> **API mode is per-plugin, not a promise of free access.** A plugin may use an official API only when the user has configured legitimate credentials and the service permits the requested operation. WhatsApp, Facebook, Canva, Drive, and email do not share one universal API. Human mode may require the user to confirm or finish actions in the target app.

## Current verified status (2026-10-12)

**NOT RELEASE-READY — Gemini-to-agent execution is not yet proven.** The repository now has native AccessibilityService source/configuration, an in-app permission status/settings control, a Python command inbox validator, a default-deny skill registry, and a one-time approval broker. These are implementation increments, not proof of a working end-to-end product. The approval broker is not yet connected to a user approval screen; the native inbox is not yet wired through a complete UI-to-skill execution flow; the APK build and merged manifest are still awaiting current CI evidence; no physical-device Gemini command test has passed. Do not treat the previously supplied APK as functional or install a new build as a verified release until the documented gates pass.

## Architecture

```text
G-EMO/
├── core/
│   ├── watcher.py       # Normalizes explicitly received accessibility text/events
│   ├── brain.py         # Deterministic intent parser; strict JSON action schema
│   └── executor.py      # Settings gate, confirmation gate, plugin dispatch
├── plugins/
│   ├── base.py
│   ├── whatsapp_plugin.py
│   ├── facebook_plugin.py
│   ├── telegram_plugin.py
│   ├── canva_plugin.py
│   ├── drive_plugin.py
│   └── email_plugin.py
├── service/
│   └── background.py    # Lifecycle contract; Android native service integration required
├── config/settings.json
├── tests/
├── android/             # Native Android Accessibility/service shell
├── apk_final/           # Release APK output (generated; not source-controlled)
├── icon.png             # EMO icon asset
└── README.md
```

## Command flow

1. The user explicitly enables G-EMO's Accessibility service in Android Settings.
2. The watcher accepts only relevant, visible/accessibility-exposed text from the Gemini app; it must not collect unrelated apps or credentials.
3. The parser emits a validated action object. Unknown or ambiguous commands are rejected.
4. The executor checks plugin enablement, mode, required fields, and whether confirmation is required.
5. Human mode opens a supported target-app workflow and reports that the user may need to complete it. It does not claim an action succeeded without evidence.
6. API mode dispatches only to an implemented official API adapter with user-provided credentials. Unconfigured adapters return `NOT_CONFIGURED`.

## Plugin settings

See `config/settings.json`. Every plugin has an explicit `enabled` switch and `mode` (`human` or `api`). Monitoring is opt-in. Sensitive actions must require confirmation regardless of mode.

## Security and privacy rules

- Never store passwords, session cookies, or Gemini conversation history.
- Do not capture unrelated apps or run hidden screen scraping.
- Do not send messages, publish posts, delete files, forward email, or make purchases without a clear confirmation step.
- API credentials must be stored in Android's secure storage in the production app; never commit credentials to this repository.
- Log action type and result only; do not log message bodies or personal content.
- A timeout, parser error, unsupported UI, ambiguous recipient, or unavailable permission must stop execution.

## Development status

This repository is being rebuilt to the G-EMO specification. A passing Python unit test suite does not prove Android Accessibility integration, reliable background operation, API access, device compatibility, APK size, or RAM usage. Those require separate Android/device verification.

## Build

The final Android package must be built and verified in an Android-capable environment. The release artifact belongs in `apk_final/` as a generated output and is not committed by default. Do not advertise the 42 MB / 90 MB targets as measured until a release APK and device measurements exist.
