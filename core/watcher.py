"""Accessibility event normalization boundary.

The Android AccessibilityService must call this only for explicitly allowed
Gemini-package events. Python cannot itself subscribe to Android accessibility.
"""
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class ObservedText:
    package_name: str
    text: str
    event_type: str

class GeminiWatcher:
    def __init__(self, allowed_package: str = "com.google.android.apps.bard") -> None:
        self.allowed_package = allowed_package

    def accept(self, package_name: str, text: str, event_type: str = "") -> ObservedText | None:
        if package_name != self.allowed_package:
            return None
        cleaned = " ".join((text or "").split())
        if not cleaned or len(cleaned) > 4000:
            return None
        return ObservedText(package_name=package_name, text=cleaned, event_type=event_type)
