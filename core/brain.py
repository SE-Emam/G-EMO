"""Strict, deterministic command parsing for G-EMO.

This module intentionally does not call a model or infer missing recipients/content.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

ALLOWED_ACTIONS = {
    "send_whatsapp", "read_whatsapp", "post_facebook", "monitor_facebook",
    "send_telegram", "open_canva", "search_drive", "send_email",
}

@dataclass(frozen=True)
class Command:
    action: str
    to: str | None = None
    text: str | None = None
    query: str | None = None
    requires_confirmation: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class ParseError(ValueError):
    """Raised when an instruction cannot be safely parsed."""


def parse_command(raw_text: str) -> dict[str, Any]:
    """Parse a small, explicit Arabic command set; reject ambiguity."""
    if not isinstance(raw_text, str):
        raise ParseError("Command must be text")
    text = " ".join(raw_text.strip().split())
    if not text or len(text) > 4000:
        raise ParseError("Command is empty or too long")
    if not re.match(r"^(?:يا\s+)?emo\b|^(?:يا\s+)?إيمو\b", text, re.IGNORECASE):
        raise ParseError("Missing explicit EMO command prefix")
    body = re.sub(r"^(?:(?:يا\s+)?emo|(?:يا\s+)?إيمو)\s*[,،:：-]?\s*", "", text, flags=re.IGNORECASE).strip()

    # Arabic prepositions include لِـ, لأحمد, and إليه forms; preserve recipient text.
    recipient_prefix = r"(?:لـ|لأ|لل|ل|إلى|الى)"
    patterns = [
        (rf"^(?:ابعت|أرسل|ارسل)\s+واتساب\s+{recipient_prefix}\s*([^:：]+)\s*[:：]\s*(.+)$", "send_whatsapp"),
        (rf"^(?:ابعت|أرسل|ارسل)\s+واتساب\s+{recipient_prefix}\s*(.+?)\s+(?:رسالة|بيقول|نصها)\s+(.+)$", "send_whatsapp"),
        (r"^(?:انشر|انشرلي|انشر لي)\s+(?:على|علي)\s+فيسبوك\s*[:：]?\s*(.+)$", "post_facebook"),
        (rf"^(?:ابعت|أرسل|ارسل)\s+تيليجرام\s+{recipient_prefix}\s*([^:：]+)\s*[:：]\s*(.+)$", "send_telegram"),
        (r"^(?:افتح|شغل)\s+كانفا$", "open_canva"),
        (r"^(?:ابحث|دور)\s+في\s+درايف\s+عن\s+(.+)$", "search_drive"),
    ]
    for pattern, action in patterns:
        match = re.match(pattern, body, re.IGNORECASE)
        if not match:
            continue
        groups = [g.strip() for g in match.groups()]
        if action in {"send_whatsapp", "send_telegram"}:
            recipient, message = groups
            if not recipient or not message:
                raise ParseError("Recipient and message are required")
            return Command(action=action, to=recipient, text=message).to_dict()
        if action == "post_facebook":
            if not groups[0]:
                raise ParseError("Post text is required")
            return Command(action=action, text=groups[0]).to_dict()
        if action == "search_drive":
            return Command(action=action, query=groups[0]).to_dict()
        return Command(action=action).to_dict()
    raise ParseError("Unsupported or ambiguous command; no action was executed")
