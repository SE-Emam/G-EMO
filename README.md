# G-EMO

**Status: BLOCKED / incomplete source handoff.** This repository currently contains the uploaded `EMO-FINAL-PRODUCTION.zip` prototype, its audit, and a bootstrap script for the approved upstream baselines. It does not yet contain the full approved G-EMO implementation described by the project plan.

## Approved architecture

- Keep the existing PicoClaw runtime as the agent engine; do not fork or refactor its core.
- Keep the existing PicoClaw FUI/runtime baseline intact.
- Add only the EMO-layer provider adapter and app-shell bridge that the plan explicitly allows.
- Gemini authentication is user-owned Google OAuth. The adapter consumes the short-lived authorized token and calls **native Gemini REST** (`models/*:generateContent`), including `Authorization: Bearer` and the required project-attribution header.
- Do not use the OpenAI-compatible Gemini OAuth endpoint; the recorded OAuth test returned `400 INVALID_ARGUMENT`.
- Do not use UI scraping, undocumented APIs, shared EMO credentials, automatic billing, or persistent refresh-token storage.
- Preserve KiosAPI byte-for-byte and rerun R-KIOS-01..04 after any approved integration change.

## Upstream baselines

The approved upstream revisions are pinned in `scripts/bootstrap-upstreams.sh`:

- PicoClaw: `sipeed/picoclaw@bbf6893ca7afad27f1d00a0f5a45982a549c6ed6`
- FUI: `sipeed/picoclaw_fui@d689c94c1b67f625f70ec4111a9aa3f01be9cbb3`

Run `bash scripts/bootstrap-upstreams.sh` to clone those baselines into `research/repos/`. The script does not overwrite an existing checkout or move a dirty worktree; it stops and reports a mismatch instead.

## What is actually in this repository

- `EMO-FINAL-PRODUCTION.zip`: the submitted 13-file Python/Buildozer prototype.
- `scripts/bootstrap-upstreams.sh`: pinned clean upstream checkout helper.
- `docs/PRODUCTION_AUDIT.md`: findings against the submitted archive.
- `docs/ARCHITECTURE_DECISION.md`: approved architecture, known blockers, and the missing-source handoff required before implementation can safely continue.

The ZIP is **not** the previously tested `emo/` Go adapter, PicoClaw integration branch, or FUI OAuth bridge. Do not treat it as a complete source export.

## Current blockers

1. The full `emo/` implementation and its tests are absent from this repository/ZIP.
2. The working PicoClaw/FUI integration branches described in the architecture record are not included; the bootstrap script checks out clean upstream baselines only.
3. The recorded live Gemini runtime reached a quota response (HTTP 429); no billing action is authorized or performed here.
4. The Android web-backend rebuild is blocked by an upstream lockfile issue involving duplicate `semver@7.8.5`. Do not patch the lockfile locally as a workaround.

## Safe next step

Restore or publish the complete approved working tree/branches containing `emo/go.mod`, `emo/providers/gemini/*.go`, the relevant PicoClaw integration branch, and the FUI bridge branch. Then continue from those exact artifacts, without redesigning or replacing the already-tested adapter. Until then, this repository should remain **BLOCKED**, not be marked production-ready.
