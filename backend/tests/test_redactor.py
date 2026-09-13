from app.core.redactor import LogRedactor

def test_redact_sensitive_credentials():
    redactor = LogRedactor()
    raw = (
        "Failed login for admin@company.org with Bearer eyJhbGciOiJIUzI1NiJ9.token.sig "
        "using key sk_live_98127398127391823981273 and IP 192.168.1.42 with card 4111-2222-3333-4444"
    )
    clean = redactor.sanitize(raw)
    assert "[REDACTED_EMAIL]" in clean
    assert "admin@company.org" not in clean
    assert "[REDACTED_TOKEN]" in clean
    assert "[REDACTED_STRIPE_KEY]" in clean
    assert "sk_live_" not in clean
    assert "[REDACTED_IP]" in clean
    assert "192.168.1.42" not in clean
    assert "[REDACTED_CARD]" in clean
    assert "4111-2222-3333-4444" not in clean
