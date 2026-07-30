"""Reference solution — Exercise 2 (identifier-aware policy).

One correct approach. Key design point: this lives *outside* the pure
`authcore.policy` because it needs request context (email, display name). It
composes the base policy rather than reimplementing it.
"""

from authcore import policy
from authcore._common_passwords import COMMON_PASSWORDS
from authcore.exceptions import PasswordPolicyError

IDENTIFIER_IN_PASSWORD = "password_contains_identifier"
_MIN_IDENTIFIER_LEN = 3


def check_password_with_context(
    password: str,
    *,
    email: str,
    display_name: str,
    denylist: frozenset[str] = COMMON_PASSWORDS,
) -> None:
    # 1. Base policy first (length, then common-password denylist).
    policy.check_password(password, denylist=denylist)

    # 2. Collect identifiers: email local-part + each word of the display name.
    local_part = email.split("@", 1)[0]
    identifiers = [local_part, *display_name.split()]

    # 3. Reject if any sufficiently long identifier appears in the password.
    folded_password = password.casefold()
    for identifier in identifiers:
        folded = identifier.casefold()
        if len(folded) >= _MIN_IDENTIFIER_LEN and folded in folded_password:
            raise PasswordPolicyError(
                IDENTIFIER_IN_PASSWORD,
                "Password must not contain your email or name.",
            )
