import pytest
from jinja2 import UndefinedError

from app.emails.render import render


def test_render_fills_the_template_variables() -> None:
    body = render(
        "verify_email.txt",
        display_name="Alice",
        verify_url="http://localhost:8000/verify-email?token=abc",
        expires_minutes=30,
    )

    assert "Hi Alice," in body
    assert "http://localhost:8000/verify-email?token=abc" in body
    assert "30 minutes" in body


def test_render_raises_on_a_missing_variable() -> None:
    # StrictUndefined: a forgotten variable fails loudly instead of rendering
    # a blank spot into a real email.
    with pytest.raises(UndefinedError):
        render("verify_email.txt", display_name="Alice", verify_url="http://x")
