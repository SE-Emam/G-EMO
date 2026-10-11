"""Opt-in, one-shot Android Keystore integration test used by emulator CI.

The test runs only when a private marker file is created in the app data directory.
It uses fixed dummy strings, never logs secret values, and removes the marker at completion.
"""
from __future__ import annotations

import json
from pathlib import Path

MARKER_NAME = ".gemo_android_keystore_self_test"
REPORT_NAME = ".gemo_android_keystore_self_test.json"
ROUNDTRIP_NAME = "whatsapp_access_token"
MIGRATION_NAME = "whatsapp_webjs_token"
ROUNDTRIP_VALUE = "G-EMO-ANDROID-KEYSTORE-SELF-TEST-NOT-A-REAL-CREDENTIAL"
LEGACY_ACCESS_VALUE = "G-EMO-MIGRATION-TEST-ACCESS-NOT-A-REAL-CREDENTIAL"
LEGACY_WEBJS_VALUE = "G-EMO-MIGRATION-TEST-WEBJS-NOT-A-REAL-CREDENTIAL"


def _write_report(path: Path, report: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
    temporary.replace(path)


def run_requested_self_test(settings_path: Path, store, write_settings) -> None:
    """Run one phase per app launch while the private marker exists."""
    marker = settings_path.parent / MARKER_NAME
    if not marker.exists():
        return

    report_path = settings_path.parent / REPORT_NAME
    try:
        if store is None:
            raise RuntimeError("Android Keystore adapter unavailable")
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {"phase": "start", "checks": []}

        phase = report.get("phase", "start")
        checks = list(report.get("checks", []))

        if phase == "start":
            store.set(ROUNDTRIP_NAME, ROUNDTRIP_VALUE)
            if store.get(ROUNDTRIP_NAME) != ROUNDTRIP_VALUE:
                raise RuntimeError("AES-GCM encrypt/decrypt round trip mismatch")
            checks.extend(["key_creation", "aes_gcm_encrypt_decrypt"])
            _write_report(report_path, {"phase": "roundtrip_written", "checks": checks})

        elif phase == "roundtrip_written":
            if store.get(ROUNDTRIP_NAME) != ROUNDTRIP_VALUE:
                raise RuntimeError("Encrypted value did not survive app restart")
            checks.append("restart_persistence")
            store.delete(ROUNDTRIP_NAME)
            if store.get(ROUNDTRIP_NAME) != "":
                raise RuntimeError("Credential remained after deletion")
            checks.append("credential_deletion")

            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            whatsapp = settings.setdefault("whatsapp", {})
            whatsapp["access_token"] = LEGACY_ACCESS_VALUE
            whatsapp["webjs_token"] = LEGACY_WEBJS_VALUE
            write_settings(settings)
            _write_report(report_path, {"phase": "migration_prepared", "checks": checks})

        elif phase == "migration_prepared":
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            whatsapp = settings.get("whatsapp", {})
            if "access_token" in whatsapp or "webjs_token" in whatsapp:
                raise RuntimeError("Legacy plaintext token fields survived migration")
            if store.get(ROUNDTRIP_NAME) != LEGACY_ACCESS_VALUE:
                raise RuntimeError("Legacy access token was not migrated to encrypted storage")
            if store.get(MIGRATION_NAME) != LEGACY_WEBJS_VALUE:
                raise RuntimeError("Legacy bridge token was not migrated to encrypted storage")
            checks.extend(["legacy_plaintext_fields_removed", "legacy_tokens_migrated"])
            store.delete(ROUNDTRIP_NAME)
            store.delete(MIGRATION_NAME)
            if store.get(ROUNDTRIP_NAME) or store.get(MIGRATION_NAME):
                raise RuntimeError("Migrated credentials remained after deletion")
            checks.append("migrated_credentials_deleted")
            _write_report(report_path, {"status": "PASS", "phase": "complete", "checks": checks})
            marker.unlink(missing_ok=True)

        elif phase == "complete" and report.get("status") == "PASS":
            marker.unlink(missing_ok=True)
        else:
            raise RuntimeError("Unknown Android Keystore self-test phase")

    except Exception as exc:
        # Error type and fixed diagnostic are reported; never include credential values.
        _write_report(report_path, {
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc)[:240],
            "checks": report.get("checks", []) if "report" in locals() and isinstance(report, dict) else [],
        })
        marker.unlink(missing_ok=True)
