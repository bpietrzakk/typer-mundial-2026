import services.email as email


def test_send_is_noop_without_api_key(monkeypatch):
    # no key set — should not touch the network at all
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    called = []
    monkeypatch.setattr(email.resend.Emails, "send", lambda p: called.append(p))
    email._send("a@b.com", "subj", "<p>x</p>")
    assert called == []


def test_send_calls_resend_when_key_set(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("EMAIL_FROM", "Test <noreply@example.com>")
    sent = {}
    monkeypatch.setattr(email.resend.Emails, "send", lambda p: sent.update(p))
    email._send("user@example.com", "Hi", "<p>body</p>")
    assert sent["from"] == "Test <noreply@example.com>"
    assert sent["to"] == ["user@example.com"]
    assert sent["subject"] == "Hi"


def test_default_sender_when_email_from_missing(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    sent = {}
    monkeypatch.setattr(email.resend.Emails, "send", lambda p: sent.update(p))
    email._send("user@example.com", "Hi", "<p>body</p>")
    assert sent["from"] == email._DEFAULT_FROM


def test_verification_email_builds_link(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("FRONTEND_URL", "https://app.test")
    sent = {}
    monkeypatch.setattr(email.resend.Emails, "send", lambda p: sent.update(p))
    email.send_verification_email("u@e.com", "tok123")
    assert "https://app.test/verify-email?token=tok123" in sent["html"]


def test_reset_email_builds_link_and_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("FRONTEND_URL", "https://app.test/")
    sent = {}
    monkeypatch.setattr(email.resend.Emails, "send", lambda p: sent.update(p))
    email.send_password_reset_email("u@e.com", "rtok")
    assert "https://app.test/reset-password?token=rtok" in sent["html"]
