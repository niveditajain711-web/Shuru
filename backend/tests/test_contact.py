import smtplib

from app.config import Settings
from app.errors import MailError, MailNotConfiguredError
from app.rate_limit import RateLimiter
from app.services import mail_service
from app.services.mail_service import MailService
import pytest

VALID = {"name": "Asha", "email": "asha@example.com", "message": "Hello there"}


def post(client, **overrides):
    return client.post("/api/contact", json={**VALID, **overrides})


def test_contact_sends_mail(client, mailer):
    response = post(client)
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert mailer.sent == [("Asha", "asha@example.com", "Hello there")]


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "   "},
        {"name": "Asha\nBcc: evil@example.com"},
        {"email": "not-an-email"},
        {"email": "a@b.com\nBcc: x@y.com"},
        {"message": " "},
        {"message": "x" * 5001},
    ],
)
def test_invalid_contact_is_rejected(client, mailer, overrides):
    assert post(client, **overrides).status_code == 422
    assert mailer.sent == []


def test_honeypot_is_ignored_silently(client, mailer):
    assert post(client, website="http://spam.example").status_code == 200
    assert mailer.sent == []


def test_rate_limit(client, mailer):
    assert [post(client).status_code for _ in range(4)] == [200, 200, 200, 429]
    assert len(mailer.sent) == 3


def test_mail_failure_is_a_plain_message(client, mailer):
    mailer.error = MailError()
    response = post(client)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "mail_failed"


def test_rate_limiter_window():
    limiter = RateLimiter(1, 3600)
    assert limiter.allow("a") and not limiter.allow("a") and limiter.allow("b")


# --- MailService against a fake SMTP server connection ---


class FakeSMTP:
    instances: list["FakeSMTP"] = []
    fail_login = False

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.started_tls, self.sent = host, port, False, []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, user, password):
        if FakeSMTP.fail_login:
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")
        self.user, self.password = user, password

    def send_message(self, mail):
        self.sent.append(mail)


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.instances, FakeSMTP.fail_login = [], False
    monkeypatch.setattr(mail_service.smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setattr(mail_service.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def settings(**kw) -> Settings:
    return Settings(_env_file=None, smtp_user="me@shuru.biz", smtp_password="secret", **kw)


def test_mail_service_sends_from_mailbox_with_reply_to(smtp):
    MailService(settings()).send_contact("Asha", "asha@example.com", "Hi")
    (conn,) = smtp.instances
    assert (conn.host, conn.port, conn.user, conn.password) == ("smtpout.secureserver.net", 465, "me@shuru.biz", "secret")
    (mail,) = conn.sent
    assert mail["To"] == "me@shuru.biz"
    assert "me@shuru.biz" in mail["From"]
    assert "asha@example.com" in mail["Reply-To"]
    assert "Hi" in mail.get_content()
    assert "secret" not in mail.as_string()


def test_mail_service_uses_starttls_on_other_ports(smtp):
    MailService(settings(smtp_port=587)).send_contact("Asha", "asha@example.com", "Hi")
    assert smtp.instances[0].started_tls


def test_login_failure_becomes_mail_error(smtp):
    smtp.fail_login = True
    with pytest.raises(MailError):
        MailService(settings()).send_contact("Asha", "asha@example.com", "Hi")


def test_unconfigured_mail_service(smtp):
    with pytest.raises(MailNotConfiguredError):
        MailService(Settings(_env_file=None)).send_contact("Asha", "asha@example.com", "Hi")
    assert smtp.instances == []
