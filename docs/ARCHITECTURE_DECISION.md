# G-EMO Architecture Decision and Implementation Gate

**Status: BLOCKED — the current ZIP is not the complete implementation source.**

## Binding decisions

1. **Runtime:** PicoClaw only, based on the approved upstream baseline `sipeed/picoclaw@bbf6893ca7afad27f1d00a0f5a45982a549c6ed6`.
2. **FUI baseline:** `sipeed/picoclaw_fui@d689c94c1b67f625f70ec4111a9aa3f01be9cbb3`.
3. **Integration boundary:** existing EMO provider contract → thin EMO Gemini OAuth adapter → native Gemini REST → existing agent/tool loop.
4. **OAuth:** Google/Gemini user-owned OAuth. OAuth was already proven in the prior Step 5A record. Go-side OAuth is not to be reimplemented; the adapter receives an already-authorized short-lived token.
5. **Endpoint:** native Gemini REST only. The tested OpenAI-compatible endpoint with the user OAuth token returned `400 INVALID_ARGUMENT`; do not route OAuth through it.
6. **Security:** token remains memory-only/foreground-scoped, logs are length/status-only and redacted, no shared EMO key, no backend refresh, no device-persisted refresh token, no automatic billing.
7. **Compatibility:** KiosAPI contract and behavior must remain byte-identical. R-KIOS-01..04 are mandatory after any approved change.
8. **Change scope:** only the additive EMO adapter, the authorized FUI auth bridge/onboarding additions, and docs/tests are in scope. No broad core/provider/FUI refactor, undocumented APIs, UI scraping, or lockfile hacks.

## Evidence from the recorded implementation plan

The prior `PROVIDER_ARCHITECTURE.md` record documents:

- `emo/providers/gemini/` adapter, mapping, token/session state machine, owner-scoped store, verification gate, and 15 unit tests.
- Native Gemini REST behavior live-tested for model discovery, basic/system/multi-turn chat, tool calling, and verbatim `thought_signature` preservation.
- KiosAPI R-KIOS-01..04 passing before/after integration.
- Step 7 runtime and FUI flows substantially implemented in separate local branches.
- The live runtime reached HTTP 429 quota exhaustion; no billing action was taken.
- The packaged web backend remained blocked by the upstream duplicate `semver@7.8.5` lockfile issue. The prescribed remedy is an upstream fix followed by rebuilding/restaging the Android web binary; no local lockfile workaround is permitted.

These are historical records from the project document, not fresh live tests performed in this repository session.

## Historical acceptance matrix (recorded 2026-10-01)

| Criterion | Recorded status | Evidence / limitation |
|---|---|---|
| AC-01 Google authentication | PASS | Live Credential Manager/OAuth proof flow. |
| AC-02 officially supported mechanism | PASS | AuthorizationClient + Credential Manager; no undocumented API, scraping, WebView, or Android loopback. |
| AC-03 no EMO-owned/shared Gemini key | PASS | User-owned OAuth only; secret sweeps recorded zero credential material. |
| AC-04 default only after verification | PASS-mechanism | Verification gate rejects proof-less, mismatched, incapable, or unattributed records; default requires CONNECTED. |
| AC-05 real agent session after onboarding | PARTIAL | Isolated shell session was live; runtime-gateway Gemini session was not fully wired in the frozen core. |
| AC-06 external provider support | PARTIAL | Coexistence/switching mechanism with KiosAPI tested; catalog/add-flow UX not complete. |
| AC-07 model selection | PASS | Live model discovery plus capability gate. |
| AC-08 provider switching | PASS-mechanism | Validated-target flip; sibling provider rows remain untouched. |
| AC-09 per-user isolation | PASS | Owner-enforced store denies cross-user Get/List/Delete. |
| AC-10 no credentials in logs/docs/analytics/Git | PASS | Redaction/refusal tests and secret sweeps recorded. |
| AC-11 no automatic billing | PASS | No billing API; project attribution header is not a billing action. |
| AC-12 disconnect without side effects | PASS-mechanism | Revoke/purge and owner-scoped deletion tested; product button depends on shell integration. |
| AC-13 native adapter uses user OAuth | PASS | Live adapter test used the user token through native REST. |
| AC-14 thought_signature regression | PASS | Key preservation and verbatim echo tested. |
| AC-15 scrub boundary | PASS | Payloads preserved verbatim; only logs are scrubbed. |
| AC-16 KiosAPI R-KIOS-01..04 | PASS | Factory, device default/runtime, live pong/stop, and regression recorded. |

## Historical Step 7 residuals

- **Runtime:** request formation and tool-loop behavior were proven. Final live state reached Gemini HTTP 429 QUOTA-EXCEEDED; no billing action was taken.
- **App shell:** the FUI onboarding/bridge flow was reported live in a separate local branch: Welcome → Google auth → Gemini authorization → verification/model selection → CONNECTED → setDefault; switch-back to KiosAPI was also recorded.
- **Web binary:** BLOCKED by upstream duplicate `semver@7.8.5` during frontend install. Required action is upstream lockfile correction, then `make build-launcher-android-arm64`, restage, and rebuild APK. Local lockfile hacks are prohibited.
- **IAM:** the project-attribution header was required; after IAM propagation, identical requests eventually succeeded before quota exhaustion. Do not change scopes or enable billing as a workaround.

## Current repository evidence

The current `SE-Emam/G-EMO` repository contains the uploaded `EMO-FINAL-PRODUCTION.zip` (249,171 bytes), a short README, and audit/docs added in this PR. The archive contains 13 Python files but does not include:

- `emo/go.mod` and the previously tested `emo/providers/gemini/*.go` implementation;
- the PicoClaw integration branch `emo-step7-gemini`;
- the FUI branch and its `EmoAuthBridge`/onboarding additions;
- the prior test harness and runtime proof artifacts.

The archive's `uiautomator2`/Buildozer prototype is not a substitute for the approved architecture. Replacing it with an AccessibilityService that scrapes Gemini UI would violate the explicit no-scraping constraint and bypass the existing OAuth/provider/runtime work.

## Required next gate

**Do not merge an invented replacement implementation.** Restore or upload the complete approved source from the `emo/`, PicoClaw, and FUI working branches, then:

1. Verify exact commit identities and clean worktrees for PicoClaw, FUI, and `emo/`.
2. Confirm the existing adapter and tests are byte-identical to the previously validated implementation.
3. Apply only the recorded allowed-list changes.
4. Resolve the project quota/IAM condition through the authorized account owner; do not enable billing or change scopes automatically.
5. Wait for the upstream web lockfile correction; rebuild and restage the web backend and APK without local lockfile edits.
6. Run the full AC-01..AC-16 acceptance matrix, real runtime/tool-loop checks, secret sweeps, and R-KIOS-01..04.
7. Mark production readiness only when the actual shipped app shell, runtime, provider switching, disconnect/revoke, and physical-device tests pass.

## Decision

This PR documents the mismatch and hard stops. It does **not** claim that the submitted ZIP completes G-EMO, and it does not change the approved runtime/provider architecture.
