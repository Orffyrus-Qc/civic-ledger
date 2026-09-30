try:
    from .privacy import redact_text, looks_like_dox
    from .sources import is_allowed, is_blocked
except ImportError:
    from privacy import redact_text, looks_like_dox
    from sources import is_allowed, is_blocked


def test_redact():
    sample = "Call 416-555-0199 at 12 Maple Street Toronto M5V 1A1, email jane@gmail.com SIN 123-456-789"
    out = redact_text(sample)
    assert "[redacted-phone]" in out
    assert "[redacted-street]" in out
    assert "[redacted-email]" in out
    assert "[redacted-id]" in out
    assert "mp.smith@parl.gc.ca" in redact_text("write mp.smith@parl.gc.ca")


def test_allowlist():
    assert is_allowed("https://www.elections.ca/content.aspx")
    assert is_allowed("https://openparliament.ca/bills/")
    assert is_allowed("https://www.cbc.ca/news/politics")
    assert not is_allowed("https://www.whitepages.com/name/Someone")
    assert is_blocked("https://www.411.ca/search")
    assert not is_allowed("https://facebook.com/someone.private")


def test_dox_flag():
    assert looks_like_dox("posting a home address and personal cell")
    assert not looks_like_dox("ethics disclosure of publicly held assets")


if __name__ == "__main__":
    test_redact()
    test_allowlist()
    test_dox_flag()
    print("privacy tests ok")
