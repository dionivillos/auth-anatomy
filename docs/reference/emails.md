# How email sending works

The email layer separates *what* to send from *how* it is delivered, so business
code never talks to SMTP directly and tests never touch the network.

## The cast

| Piece | File | Role |
|---|---|---|
| Sender / transport | [`app/emails/sender.py`](../../app/emails/sender.py) | build a message, hand it to an injected transport |
| Template rendering | [`app/emails/render.py`](../../app/emails/render.py) | plain-text Jinja templates |
| Templates | [`app/emails/templates/`](../../app/emails/templates/) | the message bodies |
| Local capture | [`docker-compose.yml`](../../docker-compose.yml) | Mailpit — a fake SMTP inbox for dev |

## Transport injection

The key idea is a small `Protocol`:

```python
class EmailTransport(Protocol):
    def send(self, message: EmailMessage) -> None: ...
```

Business code builds an `email.message.EmailMessage` and calls `transport.send`.
*Which* transport it gets is injected:

- **Production:** `SMTPTransport(host, port)` opens an SMTP connection and sends.
  In development that host/port is Mailpit; in a real deployment it is a relay.
- **Tests:** a `FakeTransport` that just appends messages to a list. No SMTP
  server, no Docker, no network — the test asserts on what *would* have been sent.

`get_email_transport()` is the FastAPI dependency that yields the configured
`SMTPTransport`; tests override it (or pass a fake directly) exactly like
`get_session`. This is the same "keep I/O at the edges, inject it for tests"
pattern used for the database.

`build_message` assembles a plain-text message from the configured
`EMAIL_FROM`; `send_email(transport, to=, subject=, body=)` is the one-liner that
builds and sends.

## Rendering plain-text bodies

`render(template_name, **context)` renders a Jinja template from
`app/emails/templates/`. Two deliberate settings
([`app/emails/render.py`](../../app/emails/render.py)):

- **`autoescape=False`.** These are plain-text emails, not HTML. HTML-escaping
  would corrupt the text (`&` → `&amp;`). There is no HTML context and therefore
  no XSS surface — which is why the bandit lint warning is suppressed *here* with
  a comment, and nowhere near actual HTML.
- **`StrictUndefined`.** A template variable that the caller forgot to pass raises
  at render time instead of silently producing a blank. A broken email is then
  caught by a test, never delivered blank to a user's inbox.

The module 18/19 flows build their `verify_url` / `reset_url`, render the matching
template, and send it through the injected transport.

## Mailpit (local capture)

`docker compose up -d` starts Mailpit, which speaks SMTP on `:1025` (what the app
sends to, per `SMTP_HOST`/`SMTP_PORT`) and serves a web inbox at
<http://localhost:8025>. Nothing is delivered to real mailboxes in development —
every message the app sends lands in Mailpit's UI, which is how you eyeball the
verification and reset emails while building the flows.
