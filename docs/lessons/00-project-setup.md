# 00 — Project setup

## Concepts

Before writing a single line of authentication logic, this module sets up the scaffolding that
every later module relies on: a reproducible Python environment, a linter/formatter, a strict
type checker, a test runner, and CI that enforces all of it on every push. None of this is
auth-specific, but the quality bar for the rest of the curriculum depends on it being right from
the start.

- **uv** manages the Python version, the virtual environment, and dependency resolution/locking
  in one tool, replacing the pip + venv + pip-tools combination.
- **ruff** replaces flake8 + black + isort with a single fast binary for linting and formatting.
- **mypy --strict** catches type errors before runtime — particularly valuable in `authcore`,
  where a wrong type on a token or a claim can silently become a security bug.
- **pytest + coverage** is the test runner; coverage numbers become a real quality gate from
  module 4 onward (authcore ≥ 85%, global ≥ 75%).
- **pre-commit** runs ruff and mypy locally before a commit ever reaches CI, so feedback is
  immediate instead of round-tripping through GitHub Actions.
- **GitHub Actions** re-runs the same checks (lint, format, typecheck, test+coverage) on every
  push and PR, so `main` can never silently drift out of a green state.

## Threats addressed

Not applicable — this module has no attack surface. Its job is to make every later module's
security work verifiable (tests that actually run, types that actually get checked) rather than
aspirational.

## Design decisions

- **`authcore` vs `app` split, established from the repository layout in module 0.** `authcore`
  is planned as a pure Python package (no FastAPI, no SQLAlchemy, no I/O) from the very first
  commit, even though it's empty until module 1. Deciding the boundary before there's code to
  misplace is cheaper than refactoring it in later.
- **`fastapi[standard-no-fastapi-cloud-cli]` instead of `fastapi[standard]`.** The `standard`
  extra pulls in `fastapi-cloud-cli` and its dependencies (`sentry-sdk`, `rich-toolkit`, etc.),
  which exist to support deploying to FastAPI's cloud product — irrelevant for a project that
  never leaves localhost. The `-no-fastapi-cloud-cli` variant keeps `fastapi dev` and Swagger UI
  without the extra weight.
- **mypy `strict = true` from commit one, not "tightened later".** Retrofitting strict mode onto
  an existing codebase is far more painful than starting with it; the empty skeleton is the
  cheapest possible point to enable it.
- **A single CI job, not a matrix, until module 4.** The PostgreSQL/SQLite test matrix is
  introduced in module 4 once there's an actual second engine to test against; adding it now
  would be complexity with nothing behind it.
- **Branch protection on `main` with required Code Owner review, but `enforce_admins: false`.**
  GitHub never allows a PR author to approve their own PR, even as an admin. Enforcing the rule
  on admins too would permanently lock a solo maintainer out of merging. Leaving admins able to
  bypass keeps external contributions gated behind explicit review while not blocking normal
  solo-dev workflow.

## References

- [uv documentation](https://docs.astral.sh/uv/)
- [ruff documentation](https://docs.astral.sh/ruff/)
- [mypy — strict mode](https://mypy.readthedocs.io/en/stable/existing_code.html#introduce-stricter-options)
- [GitHub Docs — About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Docs — About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

## Self-check questions

1. Why does `authcore` forbid importing FastAPI or SQLAlchemy, and what would break that
   guarantee?
2. Why is enabling `mypy --strict` on an empty skeleton cheaper than enabling it after several
   modules of code exist?
3. In the branch protection rule configured for this repository, why does `enforce_admins: false`
   not weaken protection against unreviewed external contributions?
4. What is the difference between what pre-commit checks locally and what CI checks remotely, and
   why have both instead of relying on just one?

Answers: [`answers/00-project-setup.md`](answers/00-project-setup.md).
