import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.config import Settings
from app.errors import MailError, MailNotConfiguredError

logger = logging.getLogger(__name__)


class MailService:
    """Sends contact-form messages to the Shuru mailbox through its SMTP server.

    The mailbox is a GoDaddy Titan mailbox, so the host is GoDaddy's `smtpout.secureserver.net`
    (not `smtp.titan.email`) and the username is the full email address. The password only ever
    comes from settings (environment), never from code. The only module that talks SMTP.
    """

    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password.get_secret_value()
        self._to = settings.contact_to or settings.smtp_user
        self._timeout = settings.smtp_timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self._user and self._password and self._to)

    def send_contact(self, name: str, email: str, message: str) -> None:
        if not self.configured:
            logger.error("contact form used but SMTP is not configured (SHURU_SMTP_USER / SHURU_SMTP_PASSWORD)")
            raise MailNotConfiguredError()

        mail = EmailMessage()
        # The mailbox is the sender: the SMTP server would reject (or spam-flag) a visitor's address as From.
        # The visitor goes in Reply-To, so answering the message answers them. EmailMessage rejects header
        # values containing line breaks, which blocks header injection.
        mail["From"] = formataddr(("Shuru contact form", self._user))
        mail["To"] = self._to
        mail["Reply-To"] = formataddr((name, email))
        mail["Subject"] = f"Shuru contact form: {name}"
        mail.set_content(f"Name: {name}\nEmail: {email}\n\n{message}\n")

        try:
            if self._port == 465:
                with smtplib.SMTP_SSL(self._host, self._port, timeout=self._timeout, context=ssl.create_default_context()) as smtp:
                    smtp.login(self._user, self._password)
                    smtp.send_message(mail)
            else:
                with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.login(self._user, self._password)
                    smtp.send_message(mail)
        except (smtplib.SMTPException, OSError, ValueError) as exc:
            # Log the type and server reply, never the credentials.
            logger.error("sending contact mail failed host=%s port=%s: %s: %s", self._host, self._port, type(exc).__name__, exc)
            raise MailError() from exc
        logger.info("contact mail sent")
