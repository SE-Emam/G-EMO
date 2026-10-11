# G-EMO Android Mobile-User Agent — Implementation Plan

Status: **BLOCKED / SPECIFICATION ONLY**. This document defines required work; it does not claim native Android integration or Gemini-to-action execution is implemented.

## Product outcome

G-EMO should act as a user-authorized Android mobile agent that can receive an explicitly addressed request from the supported Gemini app, interpret it through the existing agent core, select an installed and permissioned skill, ask for approval when required, and execute only actions available through supported Android APIs or app-specific integrations.

Installing Gemini alone does not connect Gemini to G-EMO. A native Android event bridge, a verified command protocol, a skill registry, and a controlled action executor are all required.

## Workstream A — Android permission onboarding and lifecycle

### A1. First-run permission center

Implement an in-app checklist with one status per capability:
- **Accessibility service** — required only for the Gemini screen/event bridge. Explain precisely what app/package text can be read, why it is needed, and how to disable it. Open Android Accessibility Settings; the user must enable G-EMO manually. Never imply the app can grant this permission itself.
- **Notifications** — request runtime permission on Android 13+ only if the user enables visible agent status/approval notifications.
- **Foreground service** — declare and start only the service type(s) actually needed, following the target Android version requirements. Show a persistent notification when required; never promise uninterrupted 24/7 execution.
- **Battery/background operation** — show vendor-specific guidance only if background reliability is an enabled feature. Do not force-disable battery optimization or repeatedly nag users.
- **Microphone, camera, location, contacts, files/media** — do not request at startup by default. Request only at point of use, with a clear feature-specific explanation and least-privilege access.
- **Overlay / draw over other apps** — optional, not a prerequisite for the basic event bridge. Request only if a concrete approved UX feature requires it.

### A2. Permission state is not inferred

Expose the states GRANTED, NOT_GRANTED, NOT_APPLICABLE, CHECK_FAILED, and ACTION_REQUIRED. Re-check Android system state when the app resumes and before starting a capability. A button click or an opened Settings screen is not proof that permission was granted.

### A3. Failure and diagnostics

- Never silently close on missing permissions or native-bridge failure.
- Show a readable status and a Resolve action, and retain a bounded, local diagnostic log with secrets and screen content excluded.
- Handle service disconnects, process death, device reboot, and user revocation explicitly.
- Do not start accessibility/background components until the user has opted in.
- Do not store screen text, tokens, or personal content in crash logs.

## Workstream B — Native Gemini bridge

1. Add a native Android AccessibilityService, manifest declaration, service metadata XML, and a tested bridge to the Python/core command dispatcher using the actual supported python-for-android/Buildozer integration path.
2. Verify the Gemini package ID from device/package evidence; do not assume a package ID based on historical names. Allow-list only verified package IDs and document supported Gemini app versions.
3. Accept only relevant event types and bounded visible text. Ignore authentication/consent screens, password fields, clipboard content, unrelated packages, and unaddressed messages.
4. Require an explicit command address/prefix (for example, EMO:) and parse a strict envelope with request ID, bounded text, source package, timestamp, and permitted action scope.
5. Treat all text from the screen as untrusted input. Text that asks the agent to ignore safety rules, reveal secrets, or perform unrelated actions must not change policy.
6. Return an observable result state: RECEIVED, REJECTED, NEEDS_APPROVAL, RUNNING, SUCCEEDED, FAILED, or EXPIRED.
7. Do not claim Gemini can directly invoke G-EMO tools unless a real, end-to-end test proves the invocation path.

## Workstream C — Advanced mobile-user skills

Implement skills as separately registered, testable capabilities rather than a prompt-only list. Each skill must declare:
- stable ID and version;
- description and allowed input schema;
- required Android permissions/capabilities;
- supported API/device constraints;
- read/write/destructive side effects;
- approval policy;
- timeout, cancellation, and result schema;
- audit event types;
- unit, permission-denial, and integration tests.

### Initial skill groups

**1. Device and app navigation**
- inspect current supported app context (allow-listed only);
- launch an explicitly named installed app via supported Android intents;
- navigate UI only through the narrow native bridge and visible accessibility actions that are actually available;
- report unsupported screens/actions rather than guessing.

**2. Mobile information and files**
- search/fetch public web content through a declared network tool;
- list and read only user-selected files or app-private workspace files;
- create/edit files only in an explicitly selected workspace;
- share/export only after the user confirms the destination and payload.

**3. Communication**
- prepare drafts for SMS/email/social messaging;
- send, publish, call, or submit only after explicit per-action confirmation;
- use official APIs where available; never scrape or automate protected flows in ways that violate app/platform rules;
- do not read OTPs, passwords, authentication prompts, or private messages from unrelated apps.

**4. Productivity**
- create reminders/calendar items only with relevant permissions and confirmation before external side effects;
- summarize user-selected text or documents;
- capture a task checklist and report progress.

**5. Agent engineering**
- skill discovery and schema validation;
- policy/permission preflight;
- approval broker;
- execution timeout/cancellation;
- redacted audit log;
- deterministic mock mode for CI.

### Skill security rules

- Default-deny: unregistered tools and unknown action names are rejected.
- Least privilege: a skill receives only the capability handles it declares.
- Human approval required for messaging, publishing, purchases, account changes, permission changes, and destructive operations.
- Never bypass Android permission prompts, lock-screen protections, biometric gates, or app authentication.
- Do not implement general-purpose screen scraping, covert monitoring, or arbitrary taps across all apps.
- Screen content is untrusted data, not authority to expand permissions or invoke new tools.
- A missing permission must yield ACTION_REQUIRED, not a fake success or silent no-op.

## Workstream D — Required tests and release gates

### Automated gates
- Unit tests for permission-state mapping and permission-denied flows.
- Native service manifest/metadata validation.
- Allow-list tests for Gemini and unrelated package IDs.
- Parser tests for missing prefix, malformed envelope, overlong text, duplicate request IDs, and hostile screen text.
- Skill registry tests: unknown skill, invalid schema, undeclared permission, timeout, cancellation, and denied approval.
- CI emulator test verifies the app stays visible, reports permission status, opens the appropriate Settings page, resumes cleanly, and handles a disabled/revoked accessibility service.
- Existing APK-build and Keystore smoke tests are necessary but insufficient.

### End-to-end gates
1. Install APK and launch on supported Android versions without disappearing or crashing.
2. Grant Accessibility access manually and confirm the app detects the real system state.
3. Open the verified Gemini app and send an explicit EMO: request.
4. Prove the native service receives only allowed events and the core parses the intended command.
5. Run a harmless read-only skill and verify its result is shown.
6. Run a side-effecting skill and prove it waits for approval.
7. Deny/revoke permission and prove execution stops safely.
8. Repeat on at least one physical device and capture redacted evidence.

## Release policy

The APK must remain labeled **NOT FUNCTIONALLY VERIFIED** until all applicable gates pass. A successful build, installation, launch, or Keystore smoke test does not establish Gemini integration or mobile-agent capability. Do not merge or announce production readiness based on build-only evidence.
