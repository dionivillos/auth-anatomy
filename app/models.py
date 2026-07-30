from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    """Timezone-aware UTC timestamp (project convention: never naive datetimes)."""
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Stored lowercased and enforced at the application layer; UNIQUE also gives
    # us the lookup index for free, so no separate index=True is needed.
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # NULL until the user confirms their address via the email flow (module 3).
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # NULL for OAuth-only accounts (module 7). Otherwise an Argon2id PHC string.
    password_hash: Mapped[str | None] = mapped_column(String)

    display_name: Mapped[str] = mapped_column(String, nullable=False)

    # Timestamps are set in Python (default/onupdate) rather than via the
    # database clock, so we get identical timezone-aware UTC values on both
    # SQLite and PostgreSQL.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # NULL while the account is active; set when an account is disabled.
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, email={self.email!r})"
