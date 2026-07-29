"""Password policy.

Deliberately minimal, following NIST SP 800-63B: enforce a length range and
reject well-known common passwords, but impose **no composition rules** (no
"must contain an uppercase letter / digit / symbol"). Composition rules push
users toward predictable patterns (``Password1!``) without adding real entropy;
a length floor plus a breached/common-password check defends the actual threat
(credential stuffing) far better.

`authcore` is pure: this module takes plain values and either returns ``None``
or raises a domain exception. The denylist is injected (defaulting to the
embedded one) so the logic never touches the filesystem.
"""

from authcore._common_passwords import COMMON_PASSWORDS
from authcore.exceptions import PasswordPolicyError

MIN_LENGTH = 8
# The maximum is not about password strength — it bounds the cost of hashing an
# arbitrarily large input (a denial-of-service vector) and stays within the
# algorithms' input limits.
MAX_LENGTH = 128


def check_password(password: str, *, denylist: frozenset[str] = COMMON_PASSWORDS) -> None:
    """Validate `password`. Return None if acceptable; raise on the first problem.

    Checks in order (length before the denylist, so the first failure is
    reported) and imposes no composition rules. The denylist is casefolded, so
    membership is tested case-insensitively.

    Raises:
        PasswordPolicyError: with a stable ``code`` of ``"password_too_short"``,
            ``"password_too_long"``, or ``"password_too_common"``.
    """
    if len(password) < MIN_LENGTH:
        raise PasswordPolicyError(
            "password_too_short", f"Password must be at least {MIN_LENGTH} characters long."
        )
    if len(password) > MAX_LENGTH:
        raise PasswordPolicyError(
            "password_too_long", f"Password must be at most {MAX_LENGTH} characters long."
        )
    if password.casefold() in denylist:
        raise PasswordPolicyError(
            "password_too_common", "This password is too common. Please choose a different one."
        )
