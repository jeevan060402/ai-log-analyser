import re
from typing import Dict, List, Pattern, Tuple

class LogRedactor:
    """
    Sanitizes log messages by masking PII, credentials, tokens, and sensitive IPs
    BEFORE they are indexed, stored, or processed by AI models.
    Specific token rules precede generic regexes to preserve semantic clarity.
    """
    
    PATTERNS: List[Tuple[str, Pattern, str]] = [
        ("BEARER_TOKEN", re.compile(r'(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{15,}'), r'\g<1>[REDACTED_TOKEN]'),
        ("STRIPE_KEY", re.compile(r'sk_(live|test)_[0-9a-zA-Z]{20,}'), r'[REDACTED_STRIPE_KEY]'),
        ("JWT_TOKEN", re.compile(r'eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'), r'[REDACTED_JWT]'),
        ("CREDIT_CARD", re.compile(r'\b(?:\d{4}[ -]?){3}\d{4}\b'), r'[REDACTED_CARD]'),
        ("EMAIL", re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'), r'[REDACTED_EMAIL]'),
        ("IPV4", re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'), r'[REDACTED_IP]'),
        ("GENERIC_KEY", re.compile(r'(?i)(api[_-]?key|secret|token|password|auth|passwd)[\s:=]+([a-zA-Z0-9_\-\.]{8,})'), r'\g<1>=[REDACTED_SECRET]'),
    ]

    def __init__(self, custom_masks: Dict[str, str] = None):
        self.custom_masks = custom_masks or {}

    def sanitize(self, text: str) -> str:
        if not text:
            return text
        sanitized = text
        for _, pattern, replacement in self.PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        for target, replacement in self.custom_masks.items():
            sanitized = sanitized.replace(target, replacement)
        return sanitized
