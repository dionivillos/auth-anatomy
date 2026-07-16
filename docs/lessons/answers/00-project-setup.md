# Answers — 00 Project setup

Answers to the self-check questions in [`../00-project-setup.md`](../00-project-setup.md). Try to
answer from memory first; use this only to check yourself afterward.

**1. Why does `authcore` forbid importing FastAPI or SQLAlchemy, and what would break that
guarantee?**

`authcore` holds domain logic that should be testable and reasoned about in complete isolation:
hashing a password, validating a JWT's claims, computing a TOTP code. None of that requires an
HTTP framework or a database — it takes plain values in and returns plain values (or dataclasses)
out. Keeping it framework-free means its tests run in milliseconds with no app/DB fixtures, and
the module can be read and verified as pure algorithms, which matters a lot for code whose bugs
are security bugs. It also enforces a one-directional dependency graph: `app` depends on
`authcore`, never the reverse, so `authcore` can never accidentally end up needing a request
context or a live session to run its own tests.

The guarantee breaks the moment any `authcore` module does `import fastapi` or
`from sqlalchemy import ...`, or accepts a framework object (a `Request`, a SQLAlchemy `Session`)
as a function argument instead of a plain value. The `authcore` — no FastAPI, no SQLAlchemy, no
network, no filesystem" rule in CLAUDE.md's "Architecture" section exists precisely to make this
checkable by a linter contract or a dedicated test, not just a convention.

**2. Why is enabling `mypy --strict` on an empty skeleton cheaper than enabling it after several
modules of code exist?**

`strict = true` turns on a whole bundle of checks at once — `disallow_untyped_defs`,
`disallow_any_generics`, `warn_return_any`, `no_implicit_reexport`, and others. Turning it on
against an already-written codebase surfaces every violation across every file simultaneously,
which typically means a dedicated retrofit effort (mypy's own docs on introducing strict mode to
existing code recommend doing it file-by-file with per-module overrides, precisely because doing
it all at once is painful). Starting strict from the first commit means every line of code is
written to already satisfy it — the cost is paid continuously, in tiny increments, instead of
accumulating into a single expensive migration later.

**3. In the branch protection rule configured for this repository, why does
`enforce_admins: false` not weaken protection against unreviewed external contributions?**

`enforce_admins` only controls whether *repository administrators* are also bound by the
branch protection rules (required review, required status checks) when merging. Setting it to
`false` exempts admins specifically — it grants no bypass whatsoever to anyone else. A non-admin
contributor (including anyone opening a PR from a fork) still must satisfy
`required_pull_request_reviews` (Code Owner approval) and `required_status_checks` (the `ci` job
passing) before GitHub allows the merge button to be used at all; they have no admin exemption to
fall back on, regardless of this setting.

The reason the exemption exists at all: GitHub never allows a PR author to approve their own PR,
even as an admin. If `enforce_admins` were `true`, a solo maintainer opening their own PR could
never satisfy "1 approval required" and would be permanently locked out of merging their own
work. `enforce_admins: false` is what lets the repo owner keep working solo while every other
contributor remains fully gated.

**4. What is the difference between what pre-commit checks locally and what CI checks remotely,
and why have both instead of relying on just one?**

`pre-commit` runs as a git hook on the developer's own machine at commit time, giving the fastest
possible feedback loop — you find out about a lint error or a type error before the commit even
exists, instead of after pushing and waiting for a CI run. But it's a local hook: it's only as
strong as the developer's local setup, and it can be skipped entirely with `git commit --no-verify`
or simply not installed on a machine.

CI (GitHub Actions) runs the same categories of checks, but on a clean environment on GitHub's
infrastructure, on every push and PR, regardless of what any individual contributor has installed
or chosen to bypass locally. It's the one that's wired into branch protection as a required status
check, so it's the actual enforcement point — nothing merges into `main` without CI being green,
whereas pre-commit is a convenience that makes CI failures rare rather than a guarantee that
prevents them.
