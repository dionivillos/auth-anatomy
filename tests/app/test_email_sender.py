from email.message import EmailMessage

from app.config import settings
from app.emails.sender import build_message, send_email


class FakeTransport:
    """Records messages instead of sending them (satisfies EmailTransport)."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


def test_build_message_sets_headers_and_plaintext_body() -> None:
    message = build_message(to="alice@example.com", subject="Verify", body="Hello there")

    assert message["To"] == "alice@example.com"
    assert message["Subject"] == "Verify"
    assert message["From"] == settings.email_from
    assert message.get_content_type() == "text/plain"
    assert message.get_content().strip() == "Hello there"


def test_send_email_hands_the_message_to_the_transport() -> None:
    transport = FakeTransport()

    send_email(transport, to="bob@example.com", subject="Hi", body="Body")

    assert len(transport.sent) == 1
    assert transport.sent[0]["To"] == "bob@example.com"
    assert transport.sent[0].get_content().strip() == "Body"
