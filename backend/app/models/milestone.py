from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Milestone(Base):
    """An unlocked milestone. unlocked_at is set once and never cleared.

    seen_at records when the user saw the unlock, so every client can show the
    celebration once.
    """

    __tablename__ = "milestones"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
