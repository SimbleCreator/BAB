from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Checkin(Base):
    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    waist_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    chest_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    arms_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    thighs_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    note: Mapped[str | None] = mapped_column(String(500))
    # Wins beyond the scale, each 1 (poor) to 5 (great).
    energy: Mapped[int | None] = mapped_column(SmallInteger)
    sleep: Mapped[int | None] = mapped_column(SmallInteger)
    stairs: Mapped[int | None] = mapped_column(SmallInteger)
