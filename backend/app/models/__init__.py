"""Import every model module here so Alembic autogenerate sees all tables."""

from app.models.activity import DailyActivity
from app.models.base import Base
from app.models.checkin import Checkin
from app.models.milestone import Milestone
from app.models.profile import Profile
from app.models.run import Run, RunPoint
from app.models.user import RefreshToken, User

__all__ = [
    "Base",
    "Checkin",
    "Milestone",
    "DailyActivity",
    "Profile",
    "RefreshToken",
    "Run",
    "RunPoint",
    "User",
]
