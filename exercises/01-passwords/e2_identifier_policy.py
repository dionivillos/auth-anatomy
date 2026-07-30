"""Exercise 2 — Reject passwords that contain the user's own identifiers.

Difficulty: ★★☆

`authcore.policy.check_password` is pure and context-free: it knows nothing about
who is registering. But "alice@example.com" choosing the password
"alice-2024-summer" is weak in a way length and the global denylist miss, because
it contains their own email local-part.

This check needs *request context* (the email and display name), so it does NOT
belong inside the pure `authcore.policy`. It belongs one layer out — here, a
context-aware wrapper that first applies the base policy and then adds the
identifier rule. (In the real app this logic would live in the registration
service, which already has both the password and the identifiers.)

Complete `check_password_with_context` so `test_e2_identifier_policy.py` passes.
Reference solution: `solutions/e2_identifier_policy.py`.
"""

from authcore import policy
from authcore._common_passwords import COMMON_PASSWORDS
from authcore.exceptions import PasswordPolicyError

IDENTIFIER_IN_PASSWORD = "password_contains_identifier"

# Ignore very short identifiers so a 2-letter display name does not reject
# half of all passwords.
_MIN_IDENTIFIER_LEN = 3


def check_password_with_context(
    password: str,
    *,
    email: str,
    display_name: str,
    denylist: frozenset[str] = COMMON_PASSWORDS,
) -> None:
    """Validate `password` with the base policy plus an identifier check.

    Returns None if acceptable; raises PasswordPolicyError otherwise.

    TODO(you):
      1. First run the base policy: `policy.check_password(password, denylist=denylist)`.
         Let its PasswordPolicyError propagate (short/long/common come first).
      2. Build the identifiers to forbid: the email local-part (text before '@')
         and each whitespace-separated word of the display name (so "Alice Cooper"
         yields "alice" and "cooper"). Casefold everything.
      3. If any identifier of length >= _MIN_IDENTIFIER_LEN appears as a substring
         of the casefolded password, raise
         PasswordPolicyError(IDENTIFIER_IN_PASSWORD, "<message>").
    """
    policy.check_password(password=password, denylist=denylist)

    identifiers = [word.casefold() for word in display_name.split()]
    email_local = email.split("@")[0].casefold()
    identifiers.append(email_local)
    valid_identifiers = [
       word for word in identifiers if len(word) >= _MIN_IDENTIFIER_LEN
    ]

    password_lower = password.casefold()
    if any(identifier in password_lower for identifier in valid_identifiers):
        raise PasswordPolicyError(
            IDENTIFIER_IN_PASSWORD, 
            "The password contains personal identifiers."
        )

    return None

