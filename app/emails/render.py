"""Rendering plain-text email bodies from Jinja templates in ``templates/``.

Kept separate from HTML page rendering: these are plain text, so autoescaping is
off, and `StrictUndefined` makes a missing variable raise at render time — a
broken email is then caught by a test, never delivered blank to a user.
"""

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_env = Environment(
    loader=FileSystemLoader("app/emails/templates"),
    undefined=StrictUndefined,
    # These are plain-text emails, not HTML: HTML-escaping would corrupt the text
    # (e.g. turning & into &amp;). There is no HTML context, so no XSS surface.
    autoescape=False,  # noqa: S701
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def render(template_name: str, /, **context: object) -> str:
    """Render the named plain-text template with `context`."""
    return _env.get_template(template_name).render(**context)
