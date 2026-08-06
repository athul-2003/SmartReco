import smtplib
from unittest.mock import MagicMock

from app.config import Settings
from app.services import email


def test_send_email_logs_when_smtp_not_configured(monkeypatch, caplog):
    monkeypatch.setattr(
        email, "get_settings", lambda: Settings(_env_file=None, smtp_host="")
    )

    with caplog.at_level("INFO"):
        email.send_email("user@example.com", "Subject", "Body text")

    assert "logging email instead of sending" in caplog.text
    assert "user@example.com" in caplog.text


def _fake_smtp():
    fake = MagicMock()
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    return fake


def test_send_email_sends_via_smtp_without_auth_when_unconfigured(monkeypatch):
    # No smtp_user/password - MailHog-style local dev catcher, no auth/TLS.
    fake_smtp = _fake_smtp()
    monkeypatch.setattr(smtplib, "SMTP", lambda host, port: fake_smtp)
    monkeypatch.setattr(
        email,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            smtp_host="mailhog",
            smtp_port=1025,
            digest_from_email="digest@smartreco.dev",
        ),
    )

    email.send_email("user@example.com", "Subject", "Body text")

    fake_smtp.send_message.assert_called_once()
    sent_message = fake_smtp.send_message.call_args[0][0]
    assert sent_message["To"] == "user@example.com"
    assert sent_message["From"] == "digest@smartreco.dev"
    assert sent_message["Subject"] == "Subject"
    fake_smtp.login.assert_not_called()
    fake_smtp.starttls.assert_not_called()


def test_send_email_authenticates_when_credentials_configured(monkeypatch):
    fake_smtp = _fake_smtp()
    monkeypatch.setattr(smtplib, "SMTP", lambda host, port: fake_smtp)
    monkeypatch.setattr(
        email,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="me@gmail.com",
            smtp_password="app-password",
        ),
    )

    email.send_email("user@example.com", "Subject", "Body text")

    fake_smtp.starttls.assert_called_once()
    fake_smtp.login.assert_called_once_with("me@gmail.com", "app-password")
