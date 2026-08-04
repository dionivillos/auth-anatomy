# Reference documentation

This is the **how it works** documentation for auth-anatomy: the system explained
as if it were a library you were adopting — architecture, component
responsibilities, end-to-end flows, and (later) an API reference.

It complements, and is distinct from, the [lessons](../lessons/). The lessons
teach the *why* (security concepts, threats, design reasoning) and are built to
learn by doing. This reference explains the *how* and *where*: how the pieces fit
together and where each responsibility lives in the code.

| You want to… | Read |
|---|---|
| Understand the layers and how a request flows | [Architecture](architecture.md) |
| See a full feature end-to-end in code | the per-topic flow pages below |
| Learn the security reasoning behind a module | the [lessons](../lessons/) |

## Contents

- [Architecture](architecture.md) — layers, the dependency rule, transactions,
  error handling, and the request lifecycle.
- [How a session works](sessions.md) — a token from creation to validation,
  sliding expiry, and revocation (module 02).
- [How login works](login.md) — password verification, uniform timing, the
  verify-then-rehash upgrade, anti session-fixation, and logout (module 02).
- [How email sending works](emails.md) — transport injection, plain-text
  templates, and Mailpit for local capture (module 03).

More flow pages are added as the curriculum progresses.

## Rendering as a site (later)

These pages are plain Markdown with relative links, laid out under `docs/` so
they can be published as a browsable site with almost no changes. To turn it on
later, add MkDocs Material (`mkdocs.yml` with `docs_dir: docs` and a `nav:`
listing these files) and run `uv run mkdocs serve`. Nothing here needs to change
first.
