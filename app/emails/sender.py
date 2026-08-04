"""Sending email.

The sender is split from the *transport* on purpose: business code builds an
`EmailMessage` and hands it to a transport, and which transport is used is
injected. In production that is `SMTPTransport` (talking to Mailpit locally, a
real relay in deployment); in tests it is a fake that just records what would
have been sent, so no network or Docker is needed.
"""

import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.config import settings


class EmailTransport(Protocol):
    """Anything that can deliver an :class:`email.message.EmailMessage`."""

    def send(self, message: EmailMessage) -> None: ...


class SMTPTransport:
    """Delivers a message over SMTP, opening one connection per send.

    That is simple and perfectly fine at this volume; a pooled/async transport
    would be an optimisation for later.
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

    def send(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self._host, self._port) as smtp:
            smtp.send_message(message)


def get_email_transport() -> EmailTransport:
    """FastAPI dependency yielding the configured transport (overridden in tests)."""
    return SMTPTransport(settings.smtp_host, settings.smtp_port)


def build_message(*, to: str, subject: str, body: str) -> EmailMessage:
    """Assemble a plain-text message from the configured sender address."""
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    return message


def send_email(transport: EmailTransport, *, to: str, subject: str, body: str) -> None:
    """Build a plain-text message and deliver it through `transport`."""
    transport.send(build_message(to=to, subject=subject, body=body))
