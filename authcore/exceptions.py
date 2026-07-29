"""Domain exceptions for authcore.

These carry a stable, machine-readable ``code`` alongside a human ``message`` so
the API layer can map them straight onto the uniform error shape
``{error: {code, message}}`` without translating strings.
"""


class AuthCoreError(Exception):
    """Base class for every authcore domain error."""


class PasswordPolicyError(AuthCoreError):
    """Raised when a password does not satisfy the password policy.

    Attributes:
        code: stable slug, e.g. ``"password_too_short"``.
        message: human-readable explanation.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
