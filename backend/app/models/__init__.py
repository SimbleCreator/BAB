"""Import every model module here so Alembic autogenerate sees all tables."""

from app.models.base import Base
from app.models.profile import Profile
from app.models.user import RefreshToken, User

__all__ = ["Base", "Profile", "RefreshToken", "User"]
