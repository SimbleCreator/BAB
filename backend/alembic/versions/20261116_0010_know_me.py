"""know me: lifestyle profile fields, logging food by weight

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-16 10:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROFILE_COLUMNS = (
    ("city", sa.String(length=60)),
    ("state", sa.String(length=3)),
    ("work_type", sa.String(length=10)),
    ("food_source", sa.String(length=10)),
    ("wake_time", sa.String(length=5)),
    ("sleep_hours", sa.Numeric(3, 1)),
    ("sweet_drinks_per_day", sa.Integer()),
    ("fasting_note", sa.String(length=80)),
    ("food_budget_inr", sa.Integer()),
)


def upgrade() -> None:
    for name, type_ in PROFILE_COLUMNS:
        op.add_column("profiles", sa.Column(name, type_, nullable=True))
    op.add_column(
        "profiles",
        sa.Column("usual_foods", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column("custom_foods", sa.Column("serving_g", sa.Numeric(6, 1), nullable=True))
    op.add_column("meal_items", sa.Column("grams", sa.Numeric(6, 1), nullable=True))


def downgrade() -> None:
    op.drop_column("meal_items", "grams")
    op.drop_column("custom_foods", "serving_g")
    op.drop_column("profiles", "usual_foods")
    for name, _ in reversed(PROFILE_COLUMNS):
        op.drop_column("profiles", name)
